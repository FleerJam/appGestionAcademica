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
import re
from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QLineEdit, QComboBox, QHBoxLayout, QPushButton
)
from sqlalchemy.exc import IntegrityError

from .base import DialogoBase
from models.persona_model import PersonaModel
from models.centro_model import CentroModel

# Importar Base de Datos para las instituciones dinámicas
from database.conexion import SessionLocal
from database.models import Persona


class DialogoPersona(DialogoBase):
    """Formulario para crear una Persona (Estudiante, Instructor, etc.)"""

    def __init__(self, parent=None):
        """
        Inicializa el formulario de creación de personas.
        Carga la lista dinámica de instituciones y centros.

        Args:
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self.centro_model = CentroModel()
        centros = self.centro_model.get_all()
        self.setWindowTitle("Nuevo Estudiante / Persona")
        self.setFixedSize(500, 650)
        self.persona = None
        self.model = PersonaModel()

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)

        # --- Campos ---
        self.cedula = QLineEdit()
        self.cedula.textChanged.connect(lambda: self.cedula.setText(self.cedula.text().upper()))
        layout.addWidget(QLabel("Cédula:"))
        layout.addWidget(self.cedula)

        self.nombre = QLineEdit()
        self.nombre.textChanged.connect(lambda: self.nombre.setText(self.nombre.text().upper()))
        layout.addWidget(QLabel("Nombre:"))
        layout.addWidget(self.nombre)

        self.correo = QLineEdit()
        self.correo.textChanged.connect(lambda: self.correo.setText(self.correo.text().upper()))
        layout.addWidget(QLabel("Correo:"))
        layout.addWidget(self.correo)

        self.rol = QComboBox()
        self.rol.addItems(["Estudiante", "Coordinador", "Instructor", "Otro"])
        layout.addWidget(QLabel("Rol:"))
        layout.addWidget(self.rol)

        self.centro = QComboBox()
        for centro in centros:
            texto = CentroModel.texto_desde_id(centro.id).title()
            self.centro.addItem(texto, centro.id)
        layout.addWidget(QLabel("Centro:"))
        layout.addWidget(self.centro)

        # --- Institución articulada (DINÁMICA) ---
        self.institucion = QComboBox()
        self.institucion.setEditable(True)  # <--- CRÍTICO: Permite escribir nuevas instituciones

        # Opciones por defecto
        instituciones_base = [
            "SIS ECU 911", "TRANSITO Y MOVILIDAD", "SERVICIOS MUNICIPALES",
            "SERVICIOS MILITARES", "SEGURIDAD CIUDADANA", "MINISTERIO DE SALUD PUBLICA",
            "INSTITUTO ECUATORIANO DE SEGURIDAD SOCIAL", "CRUZ ROJA ECUATORIANA",
            "GESTION DE SINIESTROS", "GESTION DE RIESGOS, CIUDADANO"
        ]

        # Extraer instituciones ya existentes en la BD
        try:
            with SessionLocal() as session:
                res = session.query(Persona.institucion_articulada).filter(
                    Persona.institucion_articulada.isnot(None)).distinct().all()
                instituciones_db = [r[0].upper() for r in res if r[0]]
                # Combinamos ambas listas y eliminamos duplicados usando Set
                instituciones_finales = sorted(list(set(instituciones_base + instituciones_db)))
        except Exception:
            instituciones_finales = sorted(instituciones_base)

        self.institucion.addItems(instituciones_finales)
        layout.addWidget(QLabel("Institución articulada:"))
        layout.addWidget(self.institucion)

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
        self.btn_aceptar.clicked.connect(self.validar_y_guardar)
        self.btn_cancelar.clicked.connect(self.reject)

    def validar_correo(self, correo):
        """
        Valida el formato del correo electrónico mediante expresión regular.

        Args:
            correo (str): Dirección de correo a validar.

        Returns:
            bool: True si el formato es válido.
        """
        patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        return re.match(patron, correo) is not None

    def validar_y_guardar(self):
        """
        Recopila los datos del formulario, realiza validaciones (vacío, cédula, correo)
        y guarda la nueva persona en la base de datos.
        """
        cedula = self.cedula.text().strip()
        nombre = self.nombre.text().strip().upper()
        correo = self.correo.text().strip().upper()
        rol = self.rol.currentText().strip().upper()
        centro_id = self.centro.currentData()
        if centro_id: centro_id = str(centro_id).upper()

        # Al ser editable, podemos usar currentText() para sacar lo que escribieron o seleccionaron
        institucion = self.institucion.currentText().strip().upper()

        if not cedula or not nombre or not correo or not rol or not centro_id or not institucion:
            self.mostrar_error("Todos los campos son obligatorios.")
            return

        if not self.model.validar_cedula_ecuador(cedula):
            self.mostrar_error("Cédula inválida.")
            return

        if not self.validar_correo(correo):
            self.mostrar_error("El correo ingresado no tiene un formato válido.")
            return

        try:
            self.persona = self.model.create({
                "cedula": cedula, "nombre": nombre, "correo": correo, "rol": rol,
                "centro_id": centro_id, "institucion_articulada": institucion
            })
            self.accept()
        except IntegrityError:
            self.mostrar_error("Ya existe una persona con esta cédula o correo.")
        except Exception as e:
            self.mostrar_error(f"Ocurrió un error: {str(e)}")