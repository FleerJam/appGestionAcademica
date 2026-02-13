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
from PyQt6.QtWidgets import (
    QWidget, QMessageBox, QTableWidget, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QDateEdit, QCheckBox, QPushButton, QLabel
)
from PyQt6.QtCore import pyqtSignal, QDate, Qt
from sqlalchemy.exc import IntegrityError

# Importamos las utilidades
from utilities.delegado import BotonDetalleDelegate
from utilities.helper import PyQtHelper

# Importamos los modelos necesarios
from models.curso_model import CursoModel
from models.matricula_model import MatriculaModel
from models.centro_model import CentroModel


class ControladorDetalleCurso(QWidget):
    """Controlador para la vista de detalle y edición de un curso específico.

    Gestiona la visualización de la información del curso, el listado de estudiantes
    matriculados y permite la edición de los datos del curso así como la eliminación
    de matrículas.
    """

    # Señales para comunicar con la ventana principal
    signal_volver = pyqtSignal()
    signal_actualizado = pyqtSignal()

    # --- Declaraciones de tipo ---
    input_duracion: QSpinBox
    input_nota: QDoubleSpinBox
    input_nombre: QLineEdit
    input_responsable: QLineEdit
    input_tipo: QComboBox
    input_modalidad: QComboBox
    date_inicio: QDateEdit
    date_fin: QDateEdit
    checkBox_sis: QCheckBox
    checkBox_instituciones: QCheckBox
    checkBox_ciudadania: QCheckBox
    btn_cancelar: QPushButton
    btn_editar: QPushButton
    input_buscar: QLineEdit
    lbl_contador: QLabel
    tabla_matriculas: QTableWidget

    def __init__(self, curso, parent=None):
        """Inicializa el controlador del detalle del curso.

        Carga la interfaz gráfica, configura los modelos, establece valores iniciales
        y conecta las señales de los widgets.

        Args:
            curso (Curso): Objeto del curso a visualizar/editar.
            parent (QWidget, optional): Widget padre. Defaults to None.
        """
        super().__init__(parent)
        self.curso = curso
        self.columnas_headers = ["", "Cédula", "Nombre Completo", "Correo", "Centro", "Institución"]
        self.total_registros = 0

        # Instancias de modelos para base de datos
        self.curso_model = CursoModel()
        self.matricula_model = MatriculaModel()
        self.model_centro = CentroModel()

        # 1. Cargar UI (.ui file)
        try:
            uic.loadUi("views/adiestramiento_detalle.ui", self)
        except Exception as e:
            print(f"Error cargando el archivo UI: {e}")

        # 2. Resolución segura de la tabla
        self.tabla = getattr(self, 'tabla_matriculas', getattr(self, 'tableEstudiantes', None))
        if not self.tabla:
            self.tabla = self.findChild(QTableWidget, 'tabla_matriculas') or self.findChild(QTableWidget,
                                                                                            'tableEstudiantes')

        # 3. Resolución segura del input de búsqueda
        if not hasattr(self, 'input_buscar'):
            self.input_buscar = self.findChild(QLineEdit, 'input_buscar')

        # Configuración inicial de campos numéricos
        self.input_duracion.setRange(1, 1000)
        self.input_duracion.setSuffix(" hrs")
        self.input_duracion.setValue(self.curso.duracion_horas)

        self.input_nota.setRange(0.0, 10.0)
        self.input_nota.setDecimals(2)
        self.input_nota.setSingleStep(0.1)
        self.input_nota.setValue(float(self.curso.nota_aprobacion))

        # Conexión de botones
        self.btn_cancelar.clicked.connect(self.accion_volver)
        self.btn_editar.clicked.connect(self.activar_edicion)

        # 4. Conexión de búsqueda en tiempo real
        if self.input_buscar:
            self.input_buscar.setPlaceholderText("Buscar por cédula, nombre o institución...")
            self.input_buscar.textChanged.connect(self.filtrar_tabla)
        else:
            print("ADVERTENCIA: No se encontró 'input_buscar' en la interfaz.")

        # Configurar delegado
        self.delegado_eliminar = BotonDetalleDelegate(
            callback=self.eliminar_matricula,
            icon_path="assets/icons/delete_matricula.png",
            columna=0
        )

        # Configuración etiqueta "Sin Datos"
        if hasattr(self, 'lbl_sin_datos'):
            self.lbl_sin_datos.setStyleSheet(
                "padding-top: 100px; padding-bottom: 100px; font-size: 18px; color: #666;"
            )
            self.lbl_sin_datos.setVisible(False)

        # Inicialización final
        self.cargar_formato_tabla()
        self._bloquear_campos()
        self._cargar_combobox_opciones()
        self._cargar_datos_curso()
        self.cargar_datos_tabla()

    # ----------------- Lógica de UI -----------------

    def filtrar_tabla(self):
        """Filtra los resultados de la tabla de matriculados según el texto de búsqueda.

        Se conecta a la señal textChanged del input de búsqueda para actualizar
        la tabla en tiempo real.
        """
        """Método conectado a la señal textChanged del input de búsqueda."""
        self.cargar_datos_tabla()

    def _cargar_combobox_opciones(self):
        """Carga las opciones predefinidas en los combobox de tipo y modalidad."""
        self.input_tipo.clear()
        self.input_tipo.addItems(["Curso", "Taller", "Conferencia o charla"])
        self.input_modalidad.clear()
        self.input_modalidad.addItems(["Presencial", "Virtual", "Semipresencial"])

    def _bloquear_campos(self):
        """Deshabilita la edición de los campos del formulario (modo visualización)."""
        campos_texto = [self.input_nombre, self.input_responsable, self.input_duracion, self.input_nota]
        campos_seleccion = [self.input_tipo, self.input_modalidad, self.date_inicio, self.date_fin]
        checkboxes = [self.checkBox_sis, self.checkBox_instituciones, self.checkBox_ciudadania]

        for w in campos_texto:
            w.setReadOnly(True)
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        for w in campos_seleccion + checkboxes:
            w.setEnabled(False)
            w.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _desbloquear_campos(self):
        """Habilita la edición de los campos del formulario (modo edición)."""
        campos_texto = [self.input_nombre, self.input_responsable, self.input_duracion, self.input_nota]
        campos_seleccion = [self.input_tipo, self.input_modalidad, self.date_inicio, self.date_fin]
        checkboxes = [self.checkBox_sis, self.checkBox_instituciones, self.checkBox_ciudadania]

        for w in campos_texto:
            w.setReadOnly(False)
            w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        for w in campos_seleccion + checkboxes:
            w.setEnabled(True)
            w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def cargar_formato_tabla(self):
        """Configura las columnas, anchos y delegados de la tabla de matrículas."""
        if not self.tabla:
            return

        anchos = [40, 80, 80, 80, 80, 80]

        PyQtHelper.configurar_tabla(
            self.tabla,
            self.columnas_headers,
            anchos,
            delegado=self.delegado_eliminar
        )

    # ----------------- Lógica de Datos -----------------

    def cargar_datos_tabla(self):
        """Recupera las matrículas de la base de datos y las muestra en la tabla.

        Aplica filtros de búsqueda por cédula, nombre o institución si se ha ingresado
        texto en el campo de búsqueda. Maneja el estado de "Sin Datos" si no hay registros.
        """
        if not self.curso or not self.tabla:
            return

        # Obtener texto de búsqueda de forma segura
        texto_busqueda = ""
        if hasattr(self, 'input_buscar') and self.input_buscar:
            texto_busqueda = self.input_buscar.text().strip()

        filtros = {'curso_id': self.curso.id}
        or_fields = []

        if texto_busqueda:
            or_fields = [
                ('persona_cedula', texto_busqueda),
                ('persona_nombre', texto_busqueda),
                ('persona_institucion_articulada', texto_busqueda)
            ]

        try:
            self.total_registros = self.matricula_model.count(
                filters=filtros,
                or_fields=or_fields if or_fields else None
            )

            if hasattr(self, 'lbl_contador'):
                self.lbl_contador.setText(f"Total matrículas: {self.total_registros}")

            # --- CASO SIN DATOS ---
            if self.total_registros == 0:
                self.tabla.clearContents()
                self.tabla.setRowCount(0)

                # Ocultar headers si no hay datos
                self.tabla.horizontalHeader().setVisible(False)

                if hasattr(self, 'lbl_sin_datos'):
                    self.lbl_sin_datos.setVisible(True)
                return

            # --- CASO CON DATOS ---
            if hasattr(self, 'lbl_sin_datos'):
                self.lbl_sin_datos.setVisible(False)

            # Restaurar visibilidad de headers
            self.tabla.horizontalHeader().setVisible(True)

            matriculas = self.matricula_model.search(
                filters=filtros,
                order_by="persona_nombre",
                or_fields=or_fields if or_fields else None
            )

        except Exception as e:
            print(f"Error cargando matrículas: {e}")
            return

        filas = []
        for matricula in matriculas:
            persona = matricula.persona

            txt_centro = "Sin Asignar"
            if matricula.centro_id:
                try:
                    txt_centro = self.model_centro.texto_desde_id(matricula.centro_id)
                except Exception:
                    pass

            filas.append([
                matricula.id,
                persona.cedula if persona else "-",
                persona.nombre if persona else "-",
                persona.correo if persona else "-",
                txt_centro,
                persona.institucion_articulada if persona else "-"
            ])

        # Recargamos configuración (incluye textos de headers)
        self.cargar_formato_tabla()

        PyQtHelper.cargar_datos_en_tabla(
            self.tabla,
            filas,
            id_column=0,
            alineacion=Qt.AlignmentFlag.AlignCenter
        )

    def _cargar_datos_curso(self):
        """Rellena los campos del formulario con la información actual del curso."""
        if not self.curso: return
        try:
            self.input_nombre.setText(self.curso.nombre.lower().title())
            self.input_responsable.setText(self.curso.responsable.lower().title())
            self.input_duracion.setValue(self.curso.duracion_horas)
            self.input_nota.setValue(float(self.curso.nota_aprobacion))
            self.input_tipo.setCurrentText(self.curso.tipo_curso.lower().title())
            self.input_modalidad.setCurrentText(self.curso.modalidad.lower().title())

            fi = self.curso.fecha_inicio
            ff = self.curso.fecha_final
            self.date_inicio.setDate(QDate(fi.year, fi.month, fi.day))
            self.date_fin.setDate(QDate(ff.year, ff.month, ff.day))

            participantes = self.curso.participantes_objetivo or []
            if isinstance(participantes, str):
                limpio = participantes.replace('[', '').replace(']', '').replace('"', '').replace("'", "")
                participantes = [p.strip() for p in limpio.split(',') if p.strip()]

            participantes_norm = {str(p).strip().upper() for p in participantes}

            self.checkBox_sis.setChecked("PERSONAL DEL SIS ECU 911" in participantes_norm)
            self.checkBox_instituciones.setChecked("INSTITUCIONES ARTICULADAS Y/O VINCULADAS" in participantes_norm)
            self.checkBox_ciudadania.setChecked("CIUDADANIA EN GENERAL" in participantes_norm)
        except Exception as e:
            print(f"Error cargando datos de BD al formulario: {e}")

    # ----------------- Lógica de Acciones -----------------

    def activar_edicion(self):
        """Habilita el modo de edición del formulario y cambia la función del botón."""
        self._desbloquear_campos()
        self.btn_editar.setText("Guardar")
        self.btn_editar.clicked.disconnect()
        self.btn_editar.clicked.connect(self.guardar_cambios)

    def mostrar_mensaje(self, tipo, titulo, texto):
        """Muestra un cuadro de diálogo con un mensaje al usuario.

        Args:
            tipo (str): Tipo de mensaje ('error' o 'info').
            titulo (str): Título de la ventana.
            texto (str): Contenido del mensaje.
        """
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical if tipo == "error" else QMessageBox.Icon.Information)
        msg.setWindowTitle(titulo)
        msg.setText(texto)
        msg.exec()

    def _actualizar_master(self):
        """Notifica a la ventana principal para que actualice sus datos globales."""
        """Busca la ventana principal (MasterController) y actualiza su caché."""
        main_window = self.window()
        if hasattr(main_window, 'actualizar_cache_global'):
            main_window.actualizar_cache_global()

    def guardar_cambios(self):
        """Valida los datos ingresados y actualiza el curso en la base de datos.

        Realiza validaciones de fechas, tipos de datos y selección de participantes.
        Si la actualización es exitosa, recalcula estados de matrículas y refresca la UI.
        """
        try:
            duracion = self.input_duracion.value()
            nota_aprobacion = self.input_nota.value()
        except (TypeError, ValueError):
            self.mostrar_mensaje("error", "Error", "Valores numéricos inválidos.")
            return

        fecha_inicio_py = self.date_inicio.date().toPyDate()
        fecha_final_py = self.date_fin.date().toPyDate()

        if fecha_final_py < fecha_inicio_py:
            self.mostrar_mensaje("error", "Error", "La fecha final no puede ser anterior a la inicial.")
            return

        participantes_seleccionados = []
        if self.checkBox_sis.isChecked():
            participantes_seleccionados.append("PERSONAL DEL SIS ECU 911")
        if self.checkBox_instituciones.isChecked():
            participantes_seleccionados.append("INSTITUCIONES ARTICULADAS Y/O VINCULADAS")
        if self.checkBox_ciudadania.isChecked():
            participantes_seleccionados.append("CIUDADANIA EN GENERAL")

        if not participantes_seleccionados:
            self.mostrar_mensaje("error", "Error", "Debe seleccionar al menos un tipo de participante.")
            return

        datos_actualizados = {
            "nombre": self.input_nombre.text().strip().upper(),
            "responsable": self.input_responsable.text().strip().upper(),
            "duracion_horas": duracion,
            "tipo_curso": self.input_tipo.currentText().strip().upper(),
            "modalidad": self.input_modalidad.currentText().strip().upper(),
            "fecha_inicio": fecha_inicio_py,
            "fecha_final": fecha_final_py,
            "nota_aprobacion": nota_aprobacion,
            "participantes_objetivo": participantes_seleccionados
        }

        try:
            exito = self.curso_model.update(self.curso.id, datos_actualizados)

            if exito:
                self.curso = self.curso_model.get_by_id(self.curso.id)

                # --- NUEVA LÓGICA DE ACTUALIZACIÓN DE ESTADOS ---
                # Si cambian las reglas (nota mínima o fechas), recalcular estados.
                self.matricula_model.actualizar_estados_por_curso(curso=self.curso)

                # --- ACTUALIZAR MASTER (DASHBOARD) ---
                self._actualizar_master()

                self.mostrar_mensaje("info", "Éxito", "El curso ha sido actualizado correctamente.")
                self.signal_actualizado.emit()

                self._bloquear_campos()
                self.btn_editar.setText("Editar")
                self.btn_editar.clicked.disconnect()
                self.btn_editar.clicked.connect(self.activar_edicion)
            else:
                self.mostrar_mensaje("error", "Error", "No se encontró el registro para actualizar.")

        except IntegrityError:
            self.mostrar_mensaje("error", "Error", "Ya existe un curso con datos duplicados.")
        except Exception as e:
            self.mostrar_mensaje("error", "Error inesperado", str(e))

    def accion_volver(self):
        """Emite la señal para cerrar la vista actual y volver al listado anterior."""
        self.signal_volver.emit()
        self.close()

    def eliminar_matricula(self, id_matricula):
        """Elimina una matrícula específica tras confirmación del usuario.

        Args:
            id_matricula (int): Identificador único de la matrícula a eliminar.
        """
        confirm = QMessageBox.question(
            self,
            "Confirmar eliminación",
            "¿Está seguro de que desea eliminar esta matrícula?\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.matricula_model.delete(id_matricula)

            # Actualizamos también el Master porque cambia la cantidad de estudiantes
            self._actualizar_master()

            self.mostrar_mensaje("info", "Éxito", "Matrícula eliminada correctamente.")
            self.cargar_datos_tabla()
            self.signal_actualizado.emit()

        except Exception as e:
            self.mostrar_mensaje("error", "Error eliminando", str(e))