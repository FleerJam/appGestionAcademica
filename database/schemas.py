from dataclasses import dataclass, field
from typing import List, Any, Optional


@dataclass
class DetalleCalificacion:
    """Estructura ligera para almacenar el puntaje de una evaluación específica."""
    evaluacion_id: str  # UUID de la tabla evaluaciones_curso
    puntaje: float


@dataclass
class RegistroImportado:
    """
    Representa una fila procesada del Excel durante la importación.
    Contiene tanto los datos crudos como los datos limpios y calculados (notas, estados).
    """
    fila_excel: int
    cedula_limpia: str
    cedula_original: str
    nombre_limpio: str
    centro_nombre: str
    correo: str
    institucion: str

    # Datos calculados
    nota_final: float
    estado_sugerido: str  # 'APROBADO', 'REPROBADO', 'EN CURSO', 'NO REALIZO'
    detalles_notas: List[DetalleCalificacion] = field(default_factory=list)

    # Metadatos de validación
    es_alias_conocido: bool = False
    es_valida_algoritmo: bool = False
    es_no_realizo: bool = False

    raw_row: Any = None


@dataclass
class ResultadoProceso:
    """Resumen final de la operación de guardado tras una importación masiva."""
    nuevos_estudiantes: int = 0      # Personas que no existían en BD
    matriculas_nuevas: int = 0       # Inscripciones nuevas en este curso
    matriculas_actualizadas: int = 0 # Inscripciones que ya existían y se actualizaron notas
    registros_omitidos: int = 0      # Registros saltados por decisión del usuario o error
    errores: List[str] = field(default_factory=list)