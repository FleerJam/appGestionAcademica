#  Copyright (c) 2026 Fleer
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.

from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QMessageBox, QTableWidget, QLineEdit, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

# --- IMPORTACIONES DEL PROYECTO ---
from models.centro_model import CentroModel
from models.persona_model import PersonaModel
from models.curso_model import CursoModel
from models.matricula_model import MatriculaModel

from utilities.delegado import BotonDetalleDelegate
from utilities.helper import PyQtHelper, actualizar_paginacion_ui
from utilities.dialogos import DialogoMatricula


# ---------------- CONTROLADOR PRINCIPAL ----------------
class ControladorEstudiantes(QWidget):
    """Controlador principal para el catálogo de estudiantes.

    Gestiona la visualización del listado completo de estudiantes, permitiendo
    buscar, paginar, ver detalles, matricular en cursos y eliminar registros.
    """

    signal_abrir_detalle = pyqtSignal(object)  # Emite el objeto estudiante al MainController

    def __init__(self):
        """Inicializa el controlador, carga la UI y configura la tabla."""
        super().__init__()

        # 1. Cargar UI
        try:
            uic.loadUi("views/estudiantes.ui", self)
        except Exception as e:
            QMessageBox.critical(self, "Error UI", f"No se pudo cargar la interfaz de estudiantes: {e}")
            return

        # 2. Modelos
        self.model_estudiante = PersonaModel()
        self.model_centro = CentroModel()
        self.model_curso = CursoModel()
        self.model_matricula = MatriculaModel()

        # 3. Configuración Tabla (3 Botones + Datos)
        # Índices: 0=Detalle, 1=Matricular, 2=Borrar
        self.columnas_headers = ["", "", "", "Nombre Completo", "Cédula", "Correo", "Centro", "Institución"]

        # 4. Paginación
        self.registros_por_pagina = 50
        self.pagina_actual = 1
        self.total_registros = 0
        self.total_paginas = 1

        # 5. Delegados
        # A) Ver Detalle (Columna 0)
        self.delegado_detalle = BotonDetalleDelegate(
            callback=self.abrir_detalle_estudiante,
            icon_path="assets/icons/ver-detalles.png",
            columna=0
        )

        # B) Matricular (Columna 1)
        self.delegado_matricular = BotonDetalleDelegate(
            callback=self.abrir_dialogo_matricula,
            icon_path="assets/icons/matricular.png",
            columna=1
        )

        # C) Borrar (Columna 2)
        self.delegado_borrar = BotonDetalleDelegate(
            callback=self.borrar_estudiante,
            icon_path="assets/icons/delete.png",
            columna=2
        )

        # 6. Setup Inicial
        self.setup_ui_elements()
        self.cargar_formato_tabla()
        self.cargar_datos_tabla()

    # ---------------- CONFIGURACIÓN UI ----------------
    def setup_ui_elements(self):
        """Conecta los widgets de la interfaz con sus funciones correspondientes."""
        # Resolución segura de Widgets
        self.input_buscar = self.findChild(QLineEdit, 'input_buscar')
        self.btn_recargar = self.findChild(QPushButton, 'btn_recargar')
        self.btn_before = self.findChild(QPushButton, 'btn_before')
        self.btn_after = self.findChild(QPushButton, 'btn_after')

        # Conexiones
        if self.input_buscar:
            self.input_buscar.textChanged.connect(self.filtrar_tabla)

        if self.btn_recargar:
            self.btn_recargar.clicked.connect(self.recargar_datos)
            self.btn_recargar.setIcon(QIcon("assets/icons/refresh.png"))

        if self.btn_before: self.btn_before.clicked.connect(self.pagina_anterior)
        if self.btn_after: self.btn_after.clicked.connect(self.pagina_siguiente)

    # ---------------- ACCIONES ----------------
    def recargar_datos(self):
        """Resetea la búsqueda y recarga la tabla desde la primera página."""
        self.pagina_actual = 1
        if self.input_buscar:
            self.input_buscar.clear()
        self.cargar_datos_tabla()

    def filtrar_tabla(self):
        """Reinicia la paginación y actualiza la tabla al cambiar el texto de búsqueda."""
        self.pagina_actual = 1
        self.cargar_datos_tabla()

    # ---------------- FORMATO TABLA ----------------
    def cargar_formato_tabla(self):
        """Configura columnas, anchos y delegados para la tabla de estudiantes."""
        tabla = getattr(self, 'tabla_estudiantes', self.findChild(QTableWidget, 'tabla_estudiantes'))
        if not tabla:
            tabla = getattr(self, 'tableEstudiantes', self.findChild(QTableWidget, 'tableEstudiantes'))

        self.tabla = tabla

        if not self.tabla:
            print("Error: No se encontró el QTableWidget en estudiantes.ui")
            return

        # Ajuste de anchos: 3 botones de 40px + columnas de datos
        anchos = [40, 40, 40, 250, 120, 180, 150, 150]

        # Configurar usando helper actualizado (Fixed para botones 0, 1, 2)
        PyQtHelper.configurar_tabla(
            self.tabla,
            self.columnas_headers,
            anchos,
            columnas_boton=[0, 1, 2]
        )

        # Asignar delegados
        self.tabla.setItemDelegateForColumn(0, self.delegado_detalle)
        self.tabla.setItemDelegateForColumn(1, self.delegado_matricular)
        self.tabla.setItemDelegateForColumn(2, self.delegado_borrar)

    # ---------------- PAGINACIÓN ----------------
    def pagina_anterior(self):
        """Retrocede a la página anterior de resultados."""
        if self.pagina_actual > 1:
            self.pagina_actual -= 1
            self.cargar_datos_tabla()

    def pagina_siguiente(self):
        """Avanza a la página siguiente de resultados."""
        if self.pagina_actual < self.total_paginas:
            self.pagina_actual += 1
            self.cargar_datos_tabla()

    def actualizar_interfaz_paginacion(self):
        """Actualiza los botones y etiquetas de paginación."""
        actualizar_paginacion_ui(
            pagina_actual=self.pagina_actual,
            total_paginas=self.total_paginas,
            total_registros=self.total_registros,
            lbl_registros=self.findChild(QLabel, 'lbl_registros'),
            lbl_contador=self.findChild(QLabel, 'lbl_contador'),
            btn_before=self.btn_before,
            btn_after=self.btn_after
        )

    # ---------------- CARGA DE DATOS ----------------
    def cargar_datos_tabla(self):
        """Obtiene los datos paginados y filtrados para llenar la tabla.

        Realiza conteo total para la paginación y recupera el segmento de datos
        correspondiente.
        """
        if not getattr(self, 'tabla', None): return

        self.tabla.setUpdatesEnabled(False)
        self.tabla.setRowCount(0)

        texto_busqueda = self.input_buscar.text().strip() if self.input_buscar else ""

        try:
            filtros = {}
            or_fields = []

            if texto_busqueda:
                or_fields = [
                    ('nombre', texto_busqueda),
                    ('institucion_articulada', texto_busqueda),
                    ('cedula', texto_busqueda)
                ]

            # 1. Contar registros
            self.total_registros = self.model_estudiante.count(
                filters=filtros if filtros else None,
                or_fields=or_fields if or_fields else None
            )

            # 2. Calcular páginas
            self.total_paginas = max(1, (
                        self.total_registros + self.registros_por_pagina - 1) // self.registros_por_pagina)

            if self.pagina_actual > self.total_paginas:
                self.pagina_actual = self.total_paginas

            offset = (self.pagina_actual - 1) * self.registros_por_pagina

            # 3. Buscar registros
            estudiantes = self.model_estudiante.search(
                filters=filtros if filtros else None,
                order_by="nombre",
                limit=self.registros_por_pagina,
                offset=offset,
                or_fields=or_fields if or_fields else None
            )

        except Exception as e:
            print(f"Error cargando datos de estudiantes: {e}")
            self.tabla.setUpdatesEnabled(True)
            return

        filas = []
        for est in estudiantes:
            txt_centro = "Sin Asignar"
            if est.centro_id:
                try:
                    txt_centro = self.model_centro.texto_desde_id(est.centro_id)
                except Exception:
                    pass

            filas.append([
                est.id,  # Col 0: Detalle
                est.id,  # Col 1: Matricular
                est.id,  # Col 2: Borrar
                est.nombre,
                est.cedula,
                est.correo,
                txt_centro,
                est.institucion_articulada
            ])

        PyQtHelper.cargar_datos_en_tabla(
            self.tabla,
            filas,
            id_column=0,
            alineacion=Qt.AlignmentFlag.AlignCenter
        )

        self.actualizar_interfaz_paginacion()

    # ---------------- ACCIONES DELEGADOS ----------------

    def abrir_detalle_estudiante(self, persona_id):
        """Abre la vista detallada del estudiante seleccionado."""
        """Ver detalles completos."""
        persona = self.model_estudiante.get_by_id(persona_id)
        if not persona:
            QMessageBox.warning(self, "Error", "No se encontró el registro.")
            return
        self.signal_abrir_detalle.emit(persona)

    def abrir_dialogo_matricula(self, persona_id):
        """Abre el diálogo para inscribir a un estudiante en un curso.

        Valida que el estudiante tenga un centro asignado antes de permitir
        la matrícula.
        """
        """Abre el diálogo para inscribir a ESTE estudiante en un curso."""
        persona = self.model_estudiante.get_by_id(persona_id)
        if not persona: return

        # --- REGLA DE NEGOCIO: El estudiante debe tener centro para matricularse ---
        if not persona.centro_id:
            QMessageBox.warning(
                self,
                "Datos Incompletos",
                f"El estudiante '{persona.nombre}' NO tiene un centro asignado.\n\n"
                "Por favor, edite al estudiante y asigne un centro antes de matricular."
            )
            return

        # Obtener cursos activos para el combo
        cursos_activos = self.model_curso.cursos_activos()
        if not cursos_activos:
            QMessageBox.warning(self, "Sin Cursos", "No hay cursos activos disponibles para matricular.")
            return

        # Preparamos los datos para el diálogo
        dlg = DialogoMatricula(personas=[persona], cursos=cursos_activos, parent=self)

        # Pre-seleccionar la persona y bloquear el combo
        idx = dlg.combo_persona.findData(persona.id)
        if idx >= 0: dlg.combo_persona.setCurrentIndex(idx)
        dlg.combo_persona.setEnabled(False)

        if dlg.exec():
            datos = dlg.matricula

            # --- ASIGNACIÓN AUTOMÁTICA DE CENTRO ---
            # El centro de la matrícula es el mismo que el del estudiante
            datos['centro_id'] = persona.centro_id

            try:
                # Verificar duplicados
                existe = self.model_matricula.search(filters={
                    "persona_id": datos['persona_id'],
                    "curso_id": datos['curso_id']
                }, first=True)

                if existe:
                    QMessageBox.warning(self, "Duplicado", "Esta persona ya está matriculada en el curso seleccionado.")
                    return

                # Crear matrícula
                self.model_matricula.create(datos)
                QMessageBox.information(self, "Éxito", f"Matrícula creada correctamente para {persona.nombre}.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo crear la matrícula:\n{e}")

    def borrar_estudiante(self, persona_id):
        """Elimina un estudiante tras una doble confirmación de seguridad.

        Advierte sobre el borrado en cascada de matrículas y calificaciones.

        Args:
            persona_id (int): ID del estudiante a eliminar.
        """
        """Elimina al estudiante tras doble confirmación."""
        persona = self.model_estudiante.get_by_id(persona_id)
        if not persona: return

        # 1. Primera confirmación
        resp = QMessageBox.question(
            self, "Eliminar Estudiante",
            f"¿Desea eliminar a:\n'{persona.nombre}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if resp != QMessageBox.StandardButton.Yes: return

        # 2. Segunda confirmación (Advertencia Crítica)
        advertencia = QMessageBox.warning(
            self, "Confirmación Irreversible",
            f"¡ADVERTENCIA!\n\n"
            f"Al eliminar a {persona.nombre} se borrarán también:\n"
            f"- Su historial de matrículas.\n"
            f"- Sus calificaciones y certificados.\n\n"
            f"¿Está seguro de continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if advertencia == QMessageBox.StandardButton.Yes:
            try:
                if self.model_estudiante.delete(persona_id):
                    QMessageBox.information(self, "Eliminado", "Registro eliminado correctamente.")
                    self.recargar_datos()
                else:
                    QMessageBox.warning(self, "Error", "No se pudo eliminar el registro.")
            except Exception as e:
                QMessageBox.critical(self, "Error Crítico", f"Error al eliminar:\n{e}")