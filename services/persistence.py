from typing import List, Dict
from models.persona_model import PersonaModel
from models.matricula_model import MatriculaModel
from models.calificacion_model import CalificacionModel
from models.centro_model import CentroModel
from models.cedula_alias_model import CedulaAliasModel
from models.evaluacion_curso_model import EvaluacionCursoModel
from models.curso_model import CursoModel

from database.schemas import RegistroImportado, ResultadoProceso
from utilities.sanitizer import Sanitizer


class PersistenceService:
    """
    Servicio encargado de la lógica de persistencia y orquestación de datos
    entre los modelos de base de datos y los procesos de importación.
    """

    def __init__(self):
        """
        Inicializa el servicio instanciando los modelos necesarios y
        preparando los diccionarios para caché interno.
        """
        self.model_persona = PersonaModel()
        self.model_matricula = MatriculaModel()
        self.model_calificacion = CalificacionModel()
        self.model_centro = CentroModel()
        self.model_alias = CedulaAliasModel()
        self.model_evaluacion = EvaluacionCursoModel()
        self.model_curso = CursoModel()

        # Caches internos
        self.cache_centros = {}
        self.cache_estudiantes = {}
        self.cache_matriculas = {}

    # ... (cargar_caches, obtener_diccionario_aliases, obtener_esquema_curso se mantienen igual) ...
    def cargar_caches(self, curso_id):
        """
        Carga en memoria los datos de centros, estudiantes y matrículas
        existentes para optimizar las consultas durante el procesamiento por lotes.

        Args:
            curso_id (str): Identificador único del curso para filtrar matrículas.
        """
        # Cache Centros
        for c in self.model_centro.get_all():
            key = Sanitizer.limpiar_texto(c.nombre)
            self.cache_centros[key] = c

        # Cache Estudiantes
        estudiantes = self.model_persona.get_all()
        self.cache_estudiantes = {str(e.cedula).strip(): e for e in estudiantes}

        # Cache Matriculas
        mats = self.model_matricula.search(filters={'curso_id': curso_id})
        self.cache_matriculas = {m.persona_id: m for m in mats}

    def obtener_diccionario_aliases(self) -> Dict[str, str]:
        """
        Obtiene un mapa de alias de cédulas registrados en el sistema.

        Returns:
            Dict[str, str]: Un diccionario donde la clave es el alias (limpio)
            y el valor es la cédula real asociada.
        """
        mapa = {}
        try:
            if hasattr(self.model_alias, 'get_all'):
                aliases = self.model_alias.get_all()
                id_to_cedula = {p.id: p.cedula for p in self.model_persona.get_all()}
                for a in aliases:
                    if a.persona_id in id_to_cedula:
                        limpio = str(a.alias_valor).strip()
                        mapa[limpio] = id_to_cedula[a.persona_id]
        except Exception:
            pass
        return mapa

    def obtener_esquema_curso(self, curso_id: str) -> List[Dict]:
        """
        Recupera la estructura de evaluaciones configurada para un curso específico.

        Args:
            curso_id (str): Identificador del curso.

        Returns:
            List[Dict]: Lista de diccionarios con la configuración de evaluaciones.
        """
        return self.model_evaluacion.obtener_esquema_curso(curso_id)

    def guardar_lote(self, registros: List[RegistroImportado], curso_id: str) -> ResultadoProceso:
        """
        Procesa y persiste un lote de registros importados, manejando la creación o actualización
        de estudiantes, matrículas y calificaciones.

        Args:
            registros (List[RegistroImportado]): Lista de objetos con la información procesada del archivo fuente.
            curso_id (str): Identificador del curso al que pertenecen los registros.

        Returns:
            ResultadoProceso: Objeto que contiene contadores de operaciones (nuevos, actualizados)
            y lista de errores encontrados.
        """
        resultado = ResultadoProceso()

        # 1. Obtener Metadatos del Curso
        curso = self.model_curso.get_by_id(curso_id)
        if not curso:
            resultado.errores.append("Error Crítico: El curso no existe.")
            return resultado

        for reg in registros:
            try:
                # --- A. Validación de Centro ---
                centro = self.cache_centros.get(reg.centro_nombre)
                if not centro:
                    resultado.errores.append(f"Fila {reg.fila_excel}: Centro '{reg.centro_nombre}' no existe en BD.")
                    resultado.registros_omitidos += 1
                    continue

                # --- B. Gestión de Estudiante ---
                est = self.cache_estudiantes.get(reg.cedula_limpia)

                if not est:
                    nuevo = {
                        "cedula": reg.cedula_limpia,
                        "nombre": reg.nombre_limpio,
                        "centro_id": centro.id,
                        "correo": reg.correo,
                        "institucion_articulada": reg.institucion,
                        "rol": "ESTUDIANTE"
                    }
                    self.model_persona.create(nuevo)
                    est = self.model_persona.search(filters={"cedula": reg.cedula_limpia}, first=True)
                    self.cache_estudiantes[reg.cedula_limpia] = est
                    resultado.nuevos_estudiantes += 1
                else:
                    # >>> CAMBIO 1: Actualizar centro del Estudiante si es diferente <<<
                    if hasattr(est, 'centro_id') and est.centro_id != centro.id:
                        self.model_persona.update(est.id, {"centro_id": centro.id})
                        # Actualizamos la referencia local para que la matrícula use el ID correcto si fuera necesario
                        est.centro_id = centro.id

                # Registro de Alias
                if reg.cedula_original != reg.cedula_limpia:
                    self._registrar_alias(est.id, reg.cedula_original)

                # --- C. CÁLCULO DE ESTADO ---
                estado_final = self.model_matricula.determinar_estado(
                    nota_final=reg.nota_final,
                    curso_obj=curso,
                    es_abandono=reg.es_no_realizo or (reg.estado_sugerido == "NO REALIZO")
                )

                # Si es abandono, forzamos nota 0 visual
                nota_final_bd = 0.0 if estado_final == "NO REALIZO" else reg.nota_final

                # --- D. Gestión de Matrícula ---
                matricula = self.cache_matriculas.get(est.id)

                if not matricula:
                    data_creacion = {
                        "persona_id": est.id,
                        "curso_id": curso_id,
                        "centro_id": centro.id,
                        "nota_final": nota_final_bd,
                        "estado": estado_final
                    }
                    self.model_matricula.create(data_creacion)

                    # Recargar para caché
                    matricula = self.model_matricula.search(filters={"persona_id": est.id, "curso_id": curso_id},
                                                            first=True)
                    self.cache_matriculas[est.id] = matricula
                    resultado.matriculas_nuevas += 1
                else:
                    # >>> CAMBIO 2: Actualizar centro de la Matrícula <<<
                    updates = {
                        "nota_final": nota_final_bd,
                        "estado": estado_final,
                        "centro_id": centro.id  # <-- Forzamos actualización del centro en la matrícula
                    }
                    self.model_matricula.update(matricula.id, updates)
                    resultado.matriculas_actualizadas += 1

                # --- E. Guardado de Notas Detalladas ---
                notas_a_guardar = reg.detalles_notas
                if estado_final == "NO REALIZO":
                    for d in notas_a_guardar: d.puntaje = 0.0

                self._guardar_calificaciones(matricula.id, notas_a_guardar)

            except Exception as e:
                resultado.errores.append(f"Fila {reg.fila_excel} ({reg.nombre_limpio}): Error crítico BD: {str(e)}")
                resultado.registros_omitidos += 1

        return resultado

    def _registrar_alias(self, persona_id, alias_val):
        """
        Registra un alias para una cédula si este no existe previamente.

        Args:
            persona_id: ID de la persona en base de datos.
            alias_val: Valor del alias (cédula original del Excel).
        """
        try:
            existe = self.model_alias.search(filters={"alias_valor": alias_val}, first=True)
            if not existe:
                self.model_alias.create({"alias_valor": alias_val, "persona_id": persona_id})
        except Exception:
            pass

    def _guardar_calificaciones(self, matricula_id, detalles):
        """
        Guarda o actualiza las calificaciones detalladas para una matrícula específica.

        Args:
            matricula_id: ID de la matrícula asociada.
            detalles: Lista de objetos con detalle de notas y evaluación.
        """
        for det in detalles:
            try:
                filtros = {"matricula_id": matricula_id, "evaluacion_curso_id": det.evaluacion_id}
                existe = self.model_calificacion.search(filters=filtros, first=True)
                datos = {
                    "matricula_id": matricula_id,
                    "evaluacion_curso_id": det.evaluacion_id,
                    "puntaje": det.puntaje
                }
                if existe:
                    self.model_calificacion.update(existe.id, {"puntaje": det.puntaje})
                else:
                    self.model_calificacion.create(datos)
            except Exception as e:
                print(f"Error guardando nota {det.evaluacion_id}: {e}")