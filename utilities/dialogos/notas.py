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
#  Copyright (c) 2026 Fleer
from datetime import date
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QScrollArea, QWidget, QCheckBox, QDoubleSpinBox, QMessageBox
)

from database.conexion import SessionLocal
from database.models import EvaluacionCurso
from models.matricula_model import MatriculaModel
from models.calificacion_model import CalificacionModel
from models.curso_model import CursoModel
from .evaluacion import DialogoEsquemaEvaluacion


class DialogoNotas(QDialog):
    """
    Gestión de Calificaciones adaptada al nuevo modelo relacional y lógica centralizada.
    Permite visualizar, editar y guardar notas de estudiantes.
    """

    def __init__(self, parent=None):
        """
        Inicializa el diálogo y los modelos de datos.

        Args:
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self.setWindowTitle("Gestión de Calificaciones por Curso")
        self.setMinimumSize(850, 600)

        # Inicialización de modelos
        self.matricula_model = MatriculaModel()  # Lógica centralizada
        self.calificacion_model = CalificacionModel()
        self.curso_model = CursoModel()
        self.db = SessionLocal()

        self.widgets_puntaje = {}  # {evaluacion_id: QDoubleSpinBox}
        self.matricula_actual = None
        self.esquema_actual = []

        self.init_ui()
        self.cargar_cursos()

    def init_ui(self):
        """Configura los elementos de la interfaz: filtros, área de notas y botones."""
        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20, 20, 20, 20)

        # --- FILTROS ---
        filtros_frame = QGroupBox("Selección")
        filtros_layout = QHBoxLayout(filtros_frame)

        filtros_layout.addWidget(QLabel("<b>Curso:</b>"))
        self.cb_cursos = QComboBox()
        self.cb_cursos.setMinimumWidth(250)
        self.cb_cursos.activated.connect(self.al_seleccionar_curso)
        filtros_layout.addWidget(self.cb_cursos)

        filtros_layout.addWidget(QLabel("<b>Estudiante:</b>"))
        self.cb_estudiantes = QComboBox()
        self.cb_estudiantes.setMinimumWidth(250)
        self.cb_estudiantes.activated.connect(self.cargar_notas_estudiante)
        filtros_layout.addWidget(self.cb_estudiantes)

        self.btn_editar_esquema = QPushButton("⚙ Configurar Evaluaciones")
        self.btn_editar_esquema.clicked.connect(self.abrir_configuracion_esquema)
        self.btn_editar_esquema.setEnabled(False)
        filtros_layout.addWidget(self.btn_editar_esquema)

        layout_principal.addWidget(filtros_frame)

        # --- ÁREA DE NOTAS ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: 1px solid #ccc; border-radius: 4px; background: white; }")

        self.contenedor_notas = QWidget()
        self.layout_notas = QVBoxLayout(self.contenedor_notas)
        self.layout_notas.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.contenedor_notas)

        layout_principal.addWidget(self.scroll)

        # --- PANEL INFERIOR ---
        footer_layout = QHBoxLayout()

        self.chk_no_realizo = QCheckBox("El estudiante NO REALIZÓ el curso (Abandono/Retiro)")
        self.chk_no_realizo.toggled.connect(self.actualizar_promedio_en_tiempo_real)
        footer_layout.addWidget(self.chk_no_realizo)

        self.label_nota_final = QLabel('Nota final: -')
        self.label_nota_final.setStyleSheet("font-size: 18px; font-weight: bold; color: #2980b9; margin-left: 20px;")
        footer_layout.addWidget(self.label_nota_final)

        footer_layout.addStretch()

        self.btn_guardar = QPushButton("Guardar Calificaciones")
        self.btn_guardar.setMinimumSize(180, 45)
        self.btn_guardar.setEnabled(False)
        self.btn_guardar.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-weight: bold; font-size: 14px; border-radius: 5px; }
            QPushButton:disabled { background-color: #bdc3c7; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        self.btn_guardar.clicked.connect(self.guardar_cambios)

        footer_layout.addWidget(self.btn_guardar)
        layout_principal.addLayout(footer_layout)

    def cargar_cursos(self):
        """Obtiene y lista todos los cursos disponibles en el ComboBox."""
        try:
            cursos = self.curso_model.search(order_by=self.curso_model.model.nombre)
            self.cb_cursos.clear()
            self.cb_cursos.addItem("-- Seleccione un curso --", None)
            for c in cursos:
                self.cb_cursos.addItem(f"{c.nombre}", c.id)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudieron cargar los cursos: {e}")

    def al_seleccionar_curso(self):
        """Manejador de evento de selección de curso. Carga esquema y estudiantes."""
        curso_id = self.cb_cursos.currentData()
        self.cb_estudiantes.clear()
        self.limpiar_area_notas()

        if not curso_id:
            self.btn_editar_esquema.setEnabled(False)
            return

        self.btn_editar_esquema.setEnabled(True)
        self.cargar_esquema_curso(curso_id)
        self.cargar_estudiantes(curso_id)

    def cargar_esquema_curso(self, curso_id):
        """Carga la estructura de evaluación (parciales, examen) para el curso."""
        try:
            self.esquema_actual = self.db.query(EvaluacionCurso).filter_by(curso_id=curso_id).order_by(EvaluacionCurso.orden).all()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error cargando esquema: {e}")
            self.esquema_actual = []

    def cargar_estudiantes(self, curso_id):
        """Carga los estudiantes matriculados en el curso seleccionado."""
        matriculas = self.matricula_model.search(filters={"curso_id": curso_id}, order_by="persona_nombre")
        self.cb_estudiantes.addItem("-- Seleccione un estudiante --", None)
        for m in matriculas:
            try:
                nombre = m.persona.nombre if m.persona else "Desconocido"
                self.cb_estudiantes.addItem(nombre, m.id)
            except:
                pass

    def abrir_configuracion_esquema(self):
        """Abre el diálogo auxiliar para modificar las evaluaciones del curso."""
        curso_id = self.cb_cursos.currentData()
        if not curso_id: return

        dlg = DialogoEsquemaEvaluacion(curso_id, self)
        if dlg.exec():
            self.al_seleccionar_curso()

    def cargar_notas_estudiante(self):
        """
        Carga las calificaciones existentes del estudiante seleccionado y
        genera dinámicamente los campos de entrada (spinboxes).
        """
        matricula_id = self.cb_estudiantes.currentData()
        self.limpiar_area_notas()

        if not matricula_id:
            self.btn_guardar.setEnabled(False)
            return

        if not self.esquema_actual:
            lbl = QLabel("⚠️ Este curso no tiene configurado un sistema de evaluación.\n"
                         "Por favor, haga clic en 'Configurar Evaluaciones'.")
            lbl.setStyleSheet("color: red; font-size: 14px; padding: 20px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout_notas.addWidget(lbl)
            return

        self.btn_guardar.setEnabled(True)
        self.matricula_actual = self.matricula_model.get_by_id(matricula_id)

        if self.matricula_actual and self.matricula_actual.estado == "NO REALIZO":
            self.chk_no_realizo.setChecked(True)
        else:
            self.chk_no_realizo.setChecked(False)

        notas_existentes = {}
        calificaciones_bd = self.calificacion_model.get_by_matricula(matricula_id)
        for cal in calificaciones_bd:
            notas_existentes[cal.evaluacion_curso_id] = cal.puntaje

        for eval_item in self.esquema_actual:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)

            lbl_texto = f"{eval_item.nombre} <span style='color:#666; font-size:11px;'>({eval_item.porcentaje}%)</span>"
            lbl = QLabel(lbl_texto)
            lbl.setFont(self.font())

            spin = QDoubleSpinBox()
            spin.setRange(0, 10.0)
            spin.setDecimals(2)
            spin.setSingleStep(0.1)
            spin.setFixedWidth(120)

            valor_actual = notas_existentes.get(eval_item.id, 0.0)
            spin.setValue(float(valor_actual))

            spin.valueChanged.connect(self.actualizar_promedio_en_tiempo_real)

            row_layout.addWidget(lbl)
            row_layout.addStretch()
            row_layout.addWidget(spin)

            self.layout_notas.addWidget(row_widget)
            self.widgets_puntaje[eval_item.id] = spin

        self.actualizar_promedio_en_tiempo_real()

    def limpiar_area_notas(self):
        """Elimina todos los widgets del área de notas."""
        while self.layout_notas.count():
            child = self.layout_notas.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        self.widgets_puntaje = {}
        self.label_nota_final.setText("Nota final: -")

    def actualizar_promedio_en_tiempo_real(self):
        """Calcula el promedio visual usando MatriculaModel."""
        if self.chk_no_realizo.isChecked():
            self.label_nota_final.setText("Nota final: 0.00 (NO REALIZO)")
            for spin in self.widgets_puntaje.values(): spin.setEnabled(False)
            return

        for spin in self.widgets_puntaje.values(): spin.setEnabled(True)

        lista_notas = []
        for eval_item in self.esquema_actual:
            spin = self.widgets_puntaje.get(eval_item.id)
            if spin:
                lista_notas.append({
                    'puntaje': spin.value(),
                    'peso': eval_item.porcentaje
                })

        # --- USO DE LÓGICA CENTRALIZADA PARA VISUALIZACIÓN ---
        nota_final = self.matricula_model.calcular_nota_ponderada(lista_notas)
        self.label_nota_final.setText(f"Nota final: {nota_final} / 10.0")

    def guardar_cambios(self):
        """
        Persiste las calificaciones en la base de datos, calcula la nota final
        y actualiza el estado (Aprobado/Reprobado) usando el modelo central.
        """
        if not self.matricula_actual: return

        try:
            nuevo_promedio = 0.0
            es_abandono = self.chk_no_realizo.isChecked()

            if es_abandono:
                for eval_id, spin in self.widgets_puntaje.items():
                    self._guardar_calificacion_individual(eval_id, 0.0)
            else:
                lista_notas = []
                for eval_item in self.esquema_actual:
                    spin = self.widgets_puntaje.get(eval_item.id)
                    if spin:
                        valor = spin.value()
                        self._guardar_calificacion_individual(eval_item.id, valor)
                        lista_notas.append({'puntaje': valor, 'peso': eval_item.porcentaje})

                # --- USO DE LÓGICA CENTRALIZADA PARA GUARDADO ---
                nuevo_promedio = self.matricula_model.calcular_nota_ponderada(lista_notas)

            # Obtener objeto curso completo para evaluar fechas
            curso = self.curso_model.get_by_id(self.matricula_actual.curso_id)

            # --- USO DE LÓGICA CENTRALIZADA PARA ESTADO ---
            nuevo_estado = self.matricula_model.determinar_estado(
                nota_final=nuevo_promedio,
                curso_obj=curso,
                es_abandono=es_abandono
            )

            # Actualizar Matrícula
            self.matricula_model.update(self.matricula_actual.id, {
                "nota_final": nuevo_promedio,
                "estado": nuevo_estado
            })

            QMessageBox.information(self, "Guardado",
                                    f"Calificaciones actualizadas.\nNota Final: {nuevo_promedio}\nEstado: {nuevo_estado}")

            self.matricula_actual.nota_final = nuevo_promedio
            self.matricula_actual.estado = nuevo_estado
            self.actualizar_promedio_en_tiempo_real()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar: {e}")

    def _guardar_calificacion_individual(self, evaluacion_id, puntaje):
        """Guarda o actualiza una calificación individual en la BD."""
        filtros = {
            "matricula_id": self.matricula_actual.id,
            "evaluacion_curso_id": evaluacion_id
        }
        existe = self.calificacion_model.search(filters=filtros, first=True)

        if existe:
            self.calificacion_model.update(existe.id, {"puntaje": puntaje})
        else:
            self.calificacion_model.create({
                "matricula_id": self.matricula_actual.id,
                "evaluacion_curso_id": evaluacion_id,
                "puntaje": puntaje
            })

    def closeEvent(self, event):
        """Cierra sesión DB al cerrar diálogo."""
        self.db.close()
        super().closeEvent(event)