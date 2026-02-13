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
    QWidget, QMessageBox, QTableWidget, QLineEdit, QLabel, QPushButton, QComboBox
)
from PyQt6.QtCore import pyqtSignal, Qt
from sqlalchemy.exc import IntegrityError
import re

from utilities.helper import PyQtHelper
from utilities.delegado import BotonDetalleDelegate

from models.matricula_model import MatriculaModel
from models.curso_model import CursoModel
from models.centro_model import CentroModel
from models.persona_model import PersonaModel
from utilities.sanitizer import Sanitizer


class ControladorDetalleEstudiante(QWidget):
    """Controlador para la gestión del perfil detallado de un estudiante.

    Permite editar la información personal del estudiante, asignar roles, centros
    e instituciones, y visualizar/gestionar su historial de matrículas en cursos.
    """

    signal_volver = pyqtSignal()
    signal_actualizado = pyqtSignal()

    # --- Declaraciones de tipo ---
    tabla_matriculas: QTableWidget
    input_buscar: QLineEdit
    lbl_contador: QLabel
    btn_editar: QPushButton
    btn_regresar: QPushButton
    lbl_sin_datos: QLabel

    # Campos del formulario
    input_nombre: QLineEdit
    input_cedula: QLineEdit
    input_correo: QLineEdit

    # Todos estos son ComboBox ahora
    input_rol: QComboBox
    input_centro: QComboBox
    input_institucion: QComboBox

    def __init__(self, estudiante, parent=None):
        """Inicializa el controlador con los datos del estudiante seleccionado.

        Args:
            estudiante (Persona): Objeto del estudiante a editar.
            parent (QWidget, optional): Widget padre. Defaults to None.
        """
        super().__init__(parent)
        self.sanitizier = Sanitizer()
        self.estudiante = estudiante
        self.total_registros = 0
        self.centros_cache = []

        # Instancias de Modelos
        self.matricula_model = MatriculaModel()
        self.curso_model = CursoModel()
        self.centro_model = CentroModel()
        self.persona_model = PersonaModel()

        self.columnas_headers = [
            "", "Curso", "Tipo", "Modalidad", "Duración", "Centro"
        ]

        # 1. Cargar UI de forma segura
        try:
            uic.loadUi("views/estudiantes_detalle.ui", self)
        except Exception as e:
            print(f"Error cargando UI: {e}")

        # 2. Resolución segura de widgets
        self.tabla = getattr(self, 'tabla_matriculas', None)
        if not self.tabla:
            self.tabla = self.findChild(QTableWidget, 'tabla_matriculas')

        self.input_buscar = getattr(self, 'input_buscar', self.findChild(QLineEdit, 'input_buscar'))

        # Resolución de campos básicos (QLineEdit)
        self.input_nombre = getattr(self, 'input_nombre', self.findChild(QLineEdit, 'input_nombre'))
        self.input_cedula = getattr(self, 'input_cedula', self.findChild(QLineEdit, 'input_cedula'))
        self.input_correo = getattr(self, 'input_correo', self.findChild(QLineEdit, 'input_correo'))

        # Resolución de campos adicionales (QComboBox)
        self.input_rol = self.findChild(QComboBox, 'input_rol')
        self.input_centro = self.findChild(QComboBox, 'input_centro')
        self.input_institucion = self.findChild(QComboBox, 'input_institucion')

        # 3. Delegado eliminar
        self.delegado_eliminar = BotonDetalleDelegate(
            callback=self.eliminar_matricula,
            icon_path="assets/icons/delete_matricula.png",
            columna=0
        )

        # 4. Conexiones
        if hasattr(self, 'btn_regresar'):
            self.btn_regresar.clicked.connect(self.accion_volver)

        if hasattr(self, 'btn_editar'):
            self.btn_editar.clicked.connect(self.activar_edicion)

        if self.input_buscar:
            self.input_buscar.setPlaceholderText("Buscar curso o modalidad...")
            self.input_buscar.textChanged.connect(self.filtrar_tabla)

        if hasattr(self, 'lbl_sin_datos'):
            self.lbl_sin_datos.setStyleSheet(
                "padding-top: 100px; padding-bottom: 100px; font-size: 18px; color: #666;"
            )
            self.lbl_sin_datos.setVisible(False)

        # 5. Inicialización
        self._cargar_combos_opciones()
        self.cargar_formato_tabla()
        self._bloquear_campos()
        self._cargar_datos_estudiante()
        self.cargar_datos_tabla()

    # -------------------------------------------------
    # CONFIGURACIÓN COMBOS
    # -------------------------------------------------
    def _cargar_combos_opciones(self):
        """Carga las listas desplegables (roles, instituciones, centros).

        Obtiene los centros activos desde la base de datos y define listas estáticas
        para roles e instituciones comunes.
        """
        # 1. Cargar Roles (ACTUALIZADO: Igual que DialogoPersona)
        self.input_rol.clear()
        roles = [
            "Estudiante",
            "Coordinador",
            "Instructor",
            "Institución"
        ]
        self.input_rol.addItems(roles)

        # 2. Cargar Instituciones (Igual que DialogoPersona)
        self.input_institucion.clear()

        institutions = [
            "ADUANA",
            "AGENCIA CIVIL DE TRANSITO",
            "AGENCIA DE CONTROL MUNICIPAL DE SANTO DOMINGO",
            "AGENCIA DE TRANSITO MUNICIPAL BABAHOYO",
            "AGENCIA METROPOLITANA DE TRANSITO",
            "AGENCIA NACIONAL DE TRANSITO",
            "AUTORIDAD DE TRANSITO MUNICIPAL",
            "CEFORPRO",
            "CNEL",
            "COE - METROPOLITANO",
            "COMISION DE TRANSITO DEL ECUADOR",
            "CONSEJO DE REGIMEN ESPECIAL DE GALAPAGOS",
            "CRUZ ROJA ECUATORIANA",
            "CUERPO DE AGENTES DE CONTROL METROPOLITANOS",
            "CUERPO DE BOMBEROS",
            "DIRECCION DE TRANSITO TRANSPORTE",
            "DIRECCION MUNICIPAL DE GESTION DE RIESGOS",
            "EMOV",
            "EMPRESA ELECTRICA QUITO",
            "EMPRESA METROPOLITANA DE ASEO",
            "EMPRESA PUBLICA CUERPO DE BOMBEROS MILAGRO",
            "EMPRESA PUBLICA DE TRANSITO PORTOVIAL EP.",
            "EMPRESA PUBLICA METROPOLITANA DE AGUA POTABLE Y SANEAMIENTO",
            "EMPRESA PUBLICA MUNICIPAL DE TRANSPORTE",
            "FUERZAS ARMADAS DEL ECUADOR",
            "GOBIERNO AUTONOMO DESCENTRALIZADO",
            "GUARDIA CIUDADANA",
            "INSTITUTO ECUATORIANO DE SEGURIDAD SOCIAL IESS",
            "MEDICO CORPORACION PARA LA SEGURIDAD CIUDADANA DE GUAYAQUIL (CSCG)",
            "MINISTERIO DE SALUD PUBLICA",
            "MOVIDELNORT -EP",
            "MOVILIDAD GADMA",
            "MOVILIDAD MACHALA (TRANSITO)",
            "MUNICIPIO",
            "NINGUNA",
            "PARADA SEGURA",
            "POLICIA NACIONAL",
            "SEGURIDAD CIUDADANA (MUNICIPIO)",
            "SENAE",
            "SERVICIO NACIONAL DE ATENCION INTEGRAL A PERSONAS ADULTAS PRIVADAS DE LA LIBERTAD Y A ADOLESCENTES INFRACTORES (SNAI)",
            "SERVICIO NACIONAL DE GESTION DE RIESGOS Y EMERGENCIAS",
            "SERVICIOS MUNICIPALES",
            "SIS ECU 911",
            "UNIDAD DE CONTROL OPERATIVO DE TRANSITO"
        ]
        self.input_institucion.addItems(institutions)

        # 4. Cargar Centros desde BD
        self.input_centro.clear()
        self.input_centro.addItem("Sin Asignar", None)
        try:
            self.centros_cache = self.centro_model.get_all()
            for centro in self.centros_cache:
                # Guardamos el ID en el data del item para referencia segura
                self.input_centro.addItem(centro.nombre, centro.id)
        except Exception as e:
            print(f"Error cargando centros: {e}")

    # -------------------------------------------------
    # BLOQUEO / DESBLOQUEO
    # -------------------------------------------------
    def _bloquear_campos(self):
        """Deshabilita la edición de campos y combos (modo visualización)."""
        # Campos de texto (QLineEdit)
        widgets_texto = [
            self.input_nombre, self.input_cedula, self.input_correo
        ]
        # Campos de selección (QComboBox) - Se incluye ROL, INSTITUCION, CENTRO
        widgets_combo = [
            self.input_rol, self.input_centro,
            self.input_institucion
        ]

        for w in widgets_texto:
            if w:
                w.setReadOnly(True)
                w.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        for w in widgets_combo:
            if w:
                w.setEnabled(False)  # Deshabilita el combo
                w.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _desbloquear_campos(self):
        """Habilita la edición de campos y combos (modo edición)."""
        widgets_texto = [
            self.input_nombre, self.input_cedula, self.input_correo
        ]
        widgets_combo = [
            self.input_rol, self.input_centro,
            self.input_institucion
        ]

        for w in widgets_texto:
            if w:
                w.setReadOnly(False)
                w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        for w in widgets_combo:
            if w:
                w.setEnabled(True)  # Habilita el combo
                w.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # -------------------------------------------------
    # CARGAR DATOS
    # -------------------------------------------------
    def _cargar_datos_estudiante(self):
        """Rellena los campos del formulario con los datos del objeto estudiante."""
        if not self.estudiante:
            return

        # Cargar textos básicos
        if self.input_nombre:
            self.input_nombre.setText(getattr(self.estudiante, 'nombre', '') or '')
        if self.input_cedula:
            self.input_cedula.setText(getattr(self.estudiante, 'cedula', '') or '')
        if self.input_correo:
            self.input_correo.setText(getattr(self.estudiante, 'correo', '') or '')

        # Helper interno para seleccionar texto en combo insensible a mayúsculas
        # Esto es vital porque en DB se guardan UPPER (ej. "ESTUDIANTE")
        # pero el combo tiene Title Case (ej. "Estudiante")
        def set_combo_text_insensitive(combo, text_value):
            if not combo or not text_value: return
            text_value = str(text_value).upper()
            for i in range(combo.count()):
                if combo.itemText(i).upper() == text_value:
                    combo.setCurrentIndex(i)
                    return

        # Seleccionar ROL
        rol_actual = getattr(self.estudiante, 'rol', 'Estudiante')
        set_combo_text_insensitive(self.input_rol, rol_actual)

        # Seleccionar INSTITUCION
        inst_actual = getattr(self.estudiante, 'institucion_articulada', '')
        set_combo_text_insensitive(self.input_institucion, inst_actual)


        # Seleccionar CENTRO (por ID)
        if self.input_centro:
            centro_id_actual = getattr(self.estudiante, 'centro_id', None)
            if centro_id_actual:
                index = self.input_centro.findData(centro_id_actual)
                if index >= 0:
                    self.input_centro.setCurrentIndex(index)
            else:
                self.input_centro.setCurrentIndex(0)

    # -------------------------------------------------
    # EDITAR / GUARDAR
    # -------------------------------------------------
    def activar_edicion(self):
        """Activa el modo de edición y cambia la función del botón principal."""
        self._desbloquear_campos()
        self.btn_editar.setText("Guardar")
        self.btn_editar.clicked.disconnect()
        self.btn_editar.clicked.connect(self.guardar_cambios)

    def guardar_cambios(self):
        """Valida los datos y actualiza el registro del estudiante.

        Realiza validaciones de campos obligatorios, formato de cédula y correo.
        Maneja errores de integridad (duplicados).
        """
        # Recolección de datos
        nombre = self.input_nombre.text().strip().upper() if self.input_nombre else ""
        cedula = self.input_cedula.text().strip() if self.input_cedula else ""
        correo = self.input_correo.text().strip().lower() if self.input_correo else ""

        # OBTENCIÓN DE DATOS DE COMBOS (Con .upper() para consistencia en BD)
        rol = self.input_rol.currentText().strip().upper() if self.input_rol else "ESTUDIANTE"
        institucion = self.input_institucion.currentText().strip().upper() if self.input_institucion else None

        centro_id = self.input_centro.currentData() if self.input_centro else None

        # --- VALIDACIONES (Igual que en DialogoPersona) ---

        # 1. Campos obligatorios
        if not cedula or not nombre or not correo or not rol or not centro_id or not institucion:
            QMessageBox.warning(self, "Error", "Todos los campos son obligatorios.")
            return

        # 2. Validación de Cédula Ecuatoriana
        if not self.sanitizier.validar_cedula_ecuador(cedula):
            QMessageBox.warning(self, "Error", "Cédula inválida.")
            return

        # 3. Validación de formato de correo
        patron_correo = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(patron_correo, correo):
            QMessageBox.warning(self, "Error", "El formato del correo electrónico no es válido.")
            return

        datos_actualizados = {
            "nombre": nombre,
            "cedula": cedula,
            "correo": correo,
            "rol": rol,
            "centro_id": centro_id,
            "institucion_articulada": institucion
        }

        try:
            exito = self.persona_model.update(self.estudiante.id, datos_actualizados)

            if exito:
                self.estudiante = self.persona_model.get_by_id(self.estudiante.id)
                QMessageBox.information(self, "Éxito", "Datos actualizados correctamente.")
                self.signal_actualizado.emit()

                self._bloquear_campos()
                self.btn_editar.setText("Editar")
                self.btn_editar.clicked.disconnect()
                self.btn_editar.clicked.connect(self.activar_edicion)
            else:
                QMessageBox.warning(self, "Error", "No se encontró el registro para actualizar.")

        except IntegrityError:
            QMessageBox.critical(self, "Error", "La cédula o el correo ya existen en otro registro.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    # -------------------------------------------------
    # TABLA MATRÍCULAS
    # -------------------------------------------------
    def cargar_formato_tabla(self):
        """Configura las columnas y anchos de la tabla de matrículas."""
        if not self.tabla: return

        anchos = [40, 180, 90, 100, 90, 140]

        PyQtHelper.configurar_tabla(
            self.tabla,
            self.columnas_headers,
            anchos,
            delegado=self.delegado_eliminar)

    def filtrar_tabla(self):
        """Recarga la tabla aplicando el filtro de búsqueda actual."""
        self.cargar_datos_tabla()

    def cargar_datos_tabla(self):
        """Obtiene y visualiza el historial de matrículas del estudiante.

        Muestra los cursos en los que está inscrito, aplicando filtros si existen.
        Maneja la carga diferida de relaciones (curso, centro) para evitar errores de sesión.
        """
        if not self.tabla or not self.estudiante: return
        try:
            texto_busqueda = self.input_buscar.text().strip() if self.input_buscar else ""

            filtros = {'persona_id': self.estudiante.id}
            or_fields = []

            if texto_busqueda:
                or_fields = [
                    ('curso_nombre', texto_busqueda),
                    ('curso_modalidad', texto_busqueda)
                ]

            try:
                self.total_registros = self.matricula_model.count(
                    filters=filtros,
                    or_fields=or_fields if or_fields else None
                )

                if hasattr(self, 'lbl_contador'):
                    self.lbl_contador.setText(f"Cursos inscritos: {self.total_registros}")

                if self.total_registros == 0:
                    self.tabla.clearContents()
                    self.tabla.setRowCount(0)
                    self.tabla.horizontalHeader().setVisible(False)
                    if hasattr(self, 'lbl_sin_datos'):
                        self.lbl_sin_datos.setVisible(True)
                    return

                if hasattr(self, 'lbl_sin_datos'):
                    self.lbl_sin_datos.setVisible(False)

                self.tabla.horizontalHeader().setVisible(True)

                matriculas = self.matricula_model.search(
                    filters=filtros,
                    order_by="curso_nombre",
                    or_fields=or_fields if or_fields else None
                )

            except Exception as e:
                print(f"Error cargando tabla matrículas: {e}")
                return

            self.cargar_formato_tabla()

            filas = []
            for m in matriculas:
                # FIX: Detached Instance Error en 'm.curso'
                # La sesión se cerró al terminar .search(), por lo que la relación m.curso
                # no puede cargarse (Lazy Load). Usamos el curso_id para obtenerlo explícitamente.
                curso = None
                curso_id = getattr(m, 'curso_id', None)
                if curso_id:
                    try:
                        curso = self.curso_model.get_by_id(curso_id)
                    except Exception:
                        curso = None

                centro = "Sin Asignar"

                if m.centro_id:
                    try:
                        centro = self.centro_model.texto_desde_id(m.centro_id)
                    except:
                        pass

                filas.append([
                    m.id,
                    curso.nombre if curso else "-",
                    curso.tipo_curso if curso else "-",
                    curso.modalidad if curso else "-",
                    f"{curso.duracion_horas} hrs" if curso else "-",
                    centro
                ])

            PyQtHelper.cargar_datos_en_tabla(
                self.tabla,
                filas,
                id_column=0,
                alineacion=Qt.AlignmentFlag.AlignCenter
            )
        except Exception as e:
            print(e)

    def eliminar_matricula(self, id_matricula):
        """Elimina una matrícula del historial del estudiante tras confirmación.

        Args:
            id_matricula (int): ID de la matrícula a eliminar.
        """
        confirm = QMessageBox.question(
            self,
            "Confirmar eliminación",
            "¿Está seguro de eliminar esta matrícula?\nEl estudiante saldrá del curso.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self.matricula_model.delete(id_matricula)
            QMessageBox.information(self, "Éxito", "Matrícula eliminada.")
            self.cargar_datos_tabla()
            self.signal_actualizado.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def accion_volver(self):
        """Cierra la vista detallada y emite la señal de retorno."""
        self.signal_volver.emit()
        self.close()