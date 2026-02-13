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
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QComboBox, QHBoxLayout, QPushButton,
    QDialog, QLineEdit, QSpinBox, QDoubleSpinBox, QDateEdit,
    QGroupBox, QCheckBox, QMessageBox
)
from sqlalchemy.exc import IntegrityError

from .base import DialogoBase
from .evaluacion import DialogoEsquemaEvaluacion
from models.curso_model import CursoModel


class DialogoMatricula(DialogoBase):
    """
    Diálogo para registrar (matricular) manualmente a una persona existente en un curso existente.
    """

    def __init__(self, personas=None, cursos=None, parent=None):
        """
        Inicializa el formulario con listas desplegables para persona y curso.

        Args:
            personas (list): Lista de objetos persona o diccionarios.
            cursos (list): Lista de objetos curso o diccionarios.
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        if cursos is None: cursos = []
        if personas is None: personas = []
        self.setWindowTitle("Matricular Persona en Curso")
        self.setFixedSize(500, 300)
        self.matricula = None

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 35, 40, 35)
        layout.setSpacing(20)

        # Selección de Persona
        self.combo_persona = QComboBox()
        for p in personas:
            if isinstance(p, dict):
                self.combo_persona.addItem(f"{p['nombre']} ({p['cedula']})", p['id'])
            else:
                self.combo_persona.addItem(f"{p.nombre} ({p.cedula})", p.id)

        layout.addWidget(QLabel("Persona:"))
        layout.addWidget(self.combo_persona)

        # Selección de Curso
        self.combo_curso = QComboBox()
        for c in cursos:
            if isinstance(c, dict):
                self.combo_curso.addItem(c['nombre'], c['id'])
            else:
                self.combo_curso.addItem(c.nombre, c.id)

        layout.addWidget(QLabel("Curso:"))
        layout.addWidget(self.combo_curso)

        layout.addStretch()

        # Botones
        btn_layout = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_aceptar = QPushButton("Aceptar")
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_aceptar)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.btn_aceptar.clicked.connect(self.validar_y_aceptar)
        self.btn_cancelar.clicked.connect(self.reject)

    def validar_y_aceptar(self):
        """
        Valida que se hayan seleccionado ambas opciones y prepara el objeto matricula.
        """
        persona_id = self.combo_persona.currentData()
        curso_id = self.combo_curso.currentData()

        if not persona_id or not curso_id:
            self.mostrar_error("Debe seleccionar una persona y un curso.")
            return

        self.matricula = {"persona_id": persona_id, "curso_id": curso_id}
        self.accept()


class DialogoCurso(QDialog):
    """
    Formulario para la creación de un nuevo Curso, Taller o Conferencia.
    Incluye la configuración básica y la opción de configurar la evaluación inmediatamente.
    """

    def __init__(self, parent=None):
        """
        Inicializa los campos del formulario para el curso.

        Args:
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self.setWindowTitle("Nuevo Curso")
        self.setFixedSize(750, 650)
        self.curso = None
        self.model = CursoModel()

        # Layout principal
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(15)

        # --- Contenedor de columnas ---
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(30)

        # Columna izquierda
        left_layout = QVBoxLayout()

        self.nombre = QLineEdit()
        self.nombre.textChanged.connect(lambda: self.nombre.setText(self.nombre.text().upper()))
        left_layout.addWidget(QLabel("Nombre:"))
        left_layout.addWidget(self.nombre)

        self.responsable = QLineEdit()
        self.responsable.textChanged.connect(lambda: self.responsable.setText(self.responsable.text().upper()))
        left_layout.addWidget(QLabel("Responsable:"))
        left_layout.addWidget(self.responsable)

        self.duracion = QSpinBox()
        self.duracion.setRange(1, 1000)
        self.duracion.setSuffix(" hrs")
        left_layout.addWidget(QLabel("Duración:"))
        left_layout.addWidget(self.duracion)

        self.nota_aprobacion = QDoubleSpinBox()
        self.nota_aprobacion.setRange(0.0, 10.0)
        self.nota_aprobacion.setDecimals(2)
        self.nota_aprobacion.setSingleStep(0.1)
        self.nota_aprobacion.setValue(8.0)
        left_layout.addWidget(QLabel("Nota mínima para aprobar:"))
        left_layout.addWidget(self.nota_aprobacion)

        self.tipo = QComboBox()
        self.tipo.addItems(["CURSO", "TALLER", "CONFERENCIA/CHARLA"])
        left_layout.addWidget(QLabel("Tipo:"))
        left_layout.addWidget(self.tipo)

        self.modalidad = QComboBox()
        self.modalidad.addItems(["PRESENCIAL", "VIRTUAL", "SEMIPRESENCIAL"])
        left_layout.addWidget(QLabel("Modalidad:"))
        left_layout.addWidget(self.modalidad)

        left_layout.addStretch()

        # Columna derecha
        right_layout = QVBoxLayout()

        fechas_layout = QHBoxLayout()
        f_inicio_layout = QVBoxLayout()
        self.fecha_inicio = QDateEdit()
        self.fecha_inicio.setCalendarPopup(True)
        self.fecha_inicio.setDisplayFormat("yyyy-MM-dd")
        self.fecha_inicio.setDate(QDate.currentDate())
        f_inicio_layout.addWidget(QLabel("Fecha inicio:"))
        f_inicio_layout.addWidget(self.fecha_inicio)

        f_final_layout = QVBoxLayout()
        self.fecha_final = QDateEdit()
        self.fecha_final.setCalendarPopup(True)
        self.fecha_final.setDisplayFormat("yyyy-MM-dd")
        self.fecha_final.setDate(QDate.currentDate())
        f_final_layout.addWidget(QLabel("Fecha final:"))
        f_final_layout.addWidget(self.fecha_final)

        fechas_layout.addLayout(f_inicio_layout)
        fechas_layout.addLayout(f_final_layout)
        right_layout.addLayout(fechas_layout)

        self.part_objetivo_group = QGroupBox("Participantes objetivo:")
        self.part_objetivo_group.setMinimumHeight(200)
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(10, 20, 10, 20)
        group_layout.setSpacing(10)

        objetivos = ["Personal del SIS ECU 911", "Instituciones articuladas y/o vinculadas", "Ciudadanía en general"]
        self.checkboxes = []
        for obj in objetivos:
            cb = QCheckBox(obj)
            group_layout.addWidget(cb)
            self.checkboxes.append(cb)

        group_layout.addStretch()
        self.part_objetivo_group.setLayout(group_layout)
        right_layout.addWidget(self.part_objetivo_group)
        right_layout.addStretch()

        columns_layout.addLayout(left_layout, 50)
        columns_layout.addLayout(right_layout, 50)
        main_layout.addLayout(columns_layout)

        btn_layout = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_aceptar = QPushButton("Aceptar")
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_aceptar)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)
        self.btn_aceptar.clicked.connect(self.validar_y_guardar)
        self.btn_cancelar.clicked.connect(self.reject)

    def validar_y_guardar(self):
        """
        Recoge los datos del formulario, valida lógica de negocio (fechas, campos vacíos)
        y persiste el nuevo curso en la base de datos.
        """
        nombre = self.nombre.text().strip().upper()
        responsable = self.responsable.text().strip().upper()
        duracion = self.duracion.value()
        nota_aprobacion = self.nota_aprobacion.value()
        tipo = self.tipo.currentText().strip().upper()
        modalidad = self.modalidad.currentText().strip().upper()
        fecha_inicio = self.fecha_inicio.date().toPyDate()
        fecha_final = self.fecha_final.date().toPyDate()

        if fecha_final < fecha_inicio:
            self.mostrar_error("La fecha final no puede ser anterior a la fecha inicio.")
            return

        participantes = [cb.text().strip().upper() for cb in self.checkboxes if cb.isChecked()]
        if not participantes:
            self.mostrar_error("Debe seleccionar al menos un participante objetivo.")
            return

        if not nombre or not responsable:
            self.mostrar_error("Todos los campos de texto son obligatorios.")
            return

        campos = {
            "nombre": nombre, "tipo_curso": tipo, "fecha_inicio": fecha_inicio,
            "fecha_final": fecha_final, "responsable": responsable, "duracion_horas": duracion,
            "nota_aprobacion": nota_aprobacion, "modalidad": modalidad,
            "participantes_objetivo": participantes
        }

        try:
            self.curso = self.model.create(campos)

            # --- Configuración Inmediata de Esquema ---
            respuesta = QMessageBox.question(
                self, "Sistema de evaluación",
                "¿Desea configurar ahora el sistema de evaluación del curso?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if respuesta == QMessageBox.StandardButton.Yes:
                dlg = DialogoEsquemaEvaluacion(self.curso.id, self)
                dlg.exec()

            self.accept()
        except IntegrityError:
            self.mostrar_error("Ya existe un curso con este nombre.")
        except Exception as e:
            self.mostrar_error(f"Ocurrió un error: {str(e)}")

    def mostrar_error(self, mensaje):
        """
        Muestra un mensaje crítico de error.

        Args:
            mensaje (str): Texto del error.
        """
        QMessageBox.critical(self, "Error", mensaje)