import pandas as pd
from typing import List, Tuple, Dict, Any

from config.mappings import COLUMNA_ALIAS, CORRECCIONES_CENTROS
from database.schemas import RegistroImportado, DetalleCalificacion
from utilities.sanitizer import Sanitizer
from models.matricula_model import MatriculaModel  # Importamos el modelo central


class ExcelEngine:
    """Motor de carga y procesamiento de archivos de hoja de cálculo (Excel/ODS).

    Se encarga de leer el archivo físico, limpiar los nombres de columnas y realizar
    el mapeo inteligente entre las columnas del archivo y los campos esperados por
    el sistema.
    """

    def __init__(self, filepath: str):
        """Inicializa el motor con la ruta del archivo.

        Args:
            filepath (str): Ruta al archivo .xlsx, .xls o .ods.
        """
        self.filepath = filepath
        self.df = None
        self.mapa_cols = {}

    def cargar(self) -> bool:
        """Carga el archivo en un DataFrame de pandas y normaliza encabezados.

        Returns:
            bool: True si la carga fue exitosa, False en caso de error.
        """
        try:
            engine = "odf" if self.filepath.endswith(".ods") else "openpyxl"
            self.df = pd.read_excel(self.filepath, engine=engine, dtype=object)
            self.df.columns = [Sanitizer.limpiar_texto(col) for col in self.df.columns]
            return True
        except Exception:
            return False

    def mapear_columnas(self, manual_resolver_callback=None) -> bool:
        """Identifica automáticamente las columnas basándose en alias conocidos.

        Intenta hacer coincidir las columnas del Excel con las requeridas (cédula,
        nombre, etc.) usando `COLUMNA_ALIAS`. Permite intervención manual si
        alguna columna no se detecta automáticamente.

        Args:
            manual_resolver_callback (func, optional): Callback para resolución manual.

        Returns:
            bool: True si al menos la columna 'cedula' fue identificada.
        """
        cols_df = self.df.columns.tolist()
        used_cols = []

        for key, alias_list in COLUMNA_ALIAS.items():
            found = False
            for col in cols_df:
                if col not in used_cols:
                    if col == Sanitizer.limpiar_texto(key).upper() or col in alias_list:
                        self.mapa_cols[key] = col
                        used_cols.append(col)
                        found = True
                        break

            if not found:
                for col in cols_df:
                    if col not in used_cols:
                        for alias in alias_list:
                            if alias in col:
                                self.mapa_cols[key] = col
                                used_cols.append(col)
                                found = True
                                break
                        if found: break

            if not found and manual_resolver_callback:
                chosen = manual_resolver_callback(key, cols_df)
                if chosen:
                    self.mapa_cols[key] = chosen
                    used_cols.append(chosen)

        return 'cedula' in self.mapa_cols

    def obtener_columnas_restantes(self) -> List[str]:
        """Devuelve las columnas que no fueron mapeadas como datos del estudiante.

        Estas columnas restantes suelen corresponder a las actividades de evaluación.

        Returns:
            List[str]: Nombres de columnas disponibles para ser asignadas como notas.
        """
        columnas_sistema = list(self.mapa_cols.values())
        posibles_notas = []
        for col in self.df.columns:
            if col not in columnas_sistema:
                posibles_notas.append(col)
        return posibles_notas


class Validator:
    """Validador y procesador de registros importados.

    Itera sobre las filas del DataFrame, limpia los datos, valida cédulas y utiliza
    el `MatriculaModel` para calcular notas finales y determinar estados. Separa
    los registros en 'válidos' y 'para revisión'.
    """

    def __init__(self, df: pd.DataFrame, mapa_cols: Dict, curso_config: Any, cache_alias: Dict,
                 mapa_actividades: Dict[str, str], esquema_ponderacion: Dict[str, float]):
        """Inicializa el validador con los datos y reglas de negocio.

        Args:
            df (pd.DataFrame): Datos cargados del Excel.
            mapa_cols (Dict): Mapeo de columnas (Excel -> Sistema).
            curso_config (Any): Objeto Curso con reglas de aprobación.
            cache_alias (Dict): Caché de alias de cédulas conocidas.
            mapa_actividades (Dict): Mapeo {ColumnaExcel: UUID_Evaluacion}.
            esquema_ponderacion (Dict): Mapeo {UUID_Evaluacion: Peso_Porcentual}.
        """
        self.df = df
        self.mapa_cols = mapa_cols
        self.curso = curso_config
        self.cache_alias = cache_alias
        self.mapa_actividades = mapa_actividades  # {ColumnaExcel: UUID_Evaluacion}
        self.esquema_ponderacion = esquema_ponderacion  # {UUID_Evaluacion: Porcentaje (e.g 40.0)}

        # Instancia del modelo para usar la lógica centralizada
        self.matricula_model = MatriculaModel()

    def procesar(self) -> Tuple[List[RegistroImportado], List[RegistroImportado]]:
        """Ejecuta el procesamiento fila por fila.

        Returns:
            Tuple[List, List]: (lista_registros_validos, lista_registros_revision)
        """
        validos = []
        revision = []
        col_cedula = self.mapa_cols.get('cedula')

        for idx, row in self.df.iterrows():
            fila = idx + 2
            raw_ced = row.get(col_cedula)
            cedula_limpia = Sanitizer.limpiar_cedula(raw_ced)

            if not cedula_limpia or cedula_limpia.lower() == 'nan': continue

            es_alias = cedula_limpia in self.cache_alias
            cedula_final = self.cache_alias[cedula_limpia] if es_alias else cedula_limpia
            es_valida = Sanitizer.validar_cedula_ecuador(cedula_final)

            nombre = Sanitizer.limpiar_texto(row.get(self.mapa_cols.get('nombre'), ''))
            apellido = Sanitizer.limpiar_texto(row.get(self.mapa_cols.get('apellido'), ''))
            centro_raw = Sanitizer.limpiar_texto(row.get(self.mapa_cols.get('centro'), ''))

            # --- USO DE LA LÓGICA CENTRALIZADA ---
            nota, estado, detalles, flag_no_realizo = self._procesar_notas_fila(row)

            registro = RegistroImportado(
                fila_excel=fila,
                cedula_limpia=cedula_final,
                cedula_original=cedula_limpia,
                nombre_limpio=f"{apellido} {nombre}".strip() or "SIN NOMBRE",
                centro_nombre=CORRECCIONES_CENTROS.get(centro_raw, centro_raw),
                correo=str(row.get(self.mapa_cols.get('correo'), '')).strip(),
                institucion=Sanitizer.limpiar_texto(row.get(self.mapa_cols.get('institucion_articulada'), '')),
                nota_final=nota,
                estado_sugerido=estado,
                detalles_notas=detalles,
                es_alias_conocido=es_alias,
                es_valida_algoritmo=es_valida,
                es_no_realizo=flag_no_realizo,
                raw_row=row
            )

            if es_alias or es_valida:
                validos.append(registro)
            else:
                revision.append(registro)

        return validos, revision

    def _procesar_notas_fila(self, row):
        """Calcula la nota final y el estado de una fila específica.

        Extrae los valores de las columnas mapeadas como notas, aplica ponderaciones
        y utiliza `MatriculaModel` para determinar si el estudiante aprobó, reprobó,
        o no realizó el curso.

        Args:
            row (pd.Series): Fila actual del DataFrame.

        Returns:
            tuple: (promedio_final, estado, lista_detalles, flag_no_realizo)
        """
        """
        Extrae las notas del Excel y delega el cálculo al MatriculaModel.
        """
        lista_para_calculo = []
        detalles = []
        todo_vacio = True

        # 1. Extraer datos crudos del Excel y preparar estructura
        for col_excel, uuid_eval in self.mapa_actividades.items():
            raw = row.get(col_excel)

            # Verificación básica de "No Realizó" si todas las celdas están vacías
            if not pd.isna(raw) and str(raw).strip() not in ["-", "", "nan"]:
                todo_vacio = False

            val_nota = Sanitizer.limpiar_nota(raw)
            porcentaje = self.esquema_ponderacion.get(uuid_eval, 0.0)

            # Estructura para el cálculo matemático
            lista_para_calculo.append({
                'puntaje': val_nota,
                'peso': porcentaje
            })

            # Estructura para guardar detalle en BD
            detalles.append(DetalleCalificacion(evaluacion_id=uuid_eval, puntaje=val_nota))

        # 2. Delegar Matemática a MatriculaModel
        promedio_final = self.matricula_model.calcular_nota_ponderada(lista_para_calculo)

        # 3. Delegar Estado a MatriculaModel
        estado = self.matricula_model.determinar_estado(
            nota_final=promedio_final,
            curso_obj=self.curso,
            es_abandono=todo_vacio  # Si todo está vacío, asumimos abandono en importación
        )

        return promedio_final, estado, detalles, todo_vacio