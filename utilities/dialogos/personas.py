#  Copyright (c) 2026 Fleer
import re
import traceback  # <--- Agregado para depurar cierres inesperados
from PyQt6.QtWidgets import (
    QVBoxLayout, QLabel, QLineEdit, QComboBox, QHBoxLayout, QPushButton, QMessageBox
)
from sqlalchemy.exc import IntegrityError

# Asumo que estos imports funcionan en tu entorno
from .base import DialogoBase
from models.persona_model import PersonaModel
from models.centro_model import CentroModel

# Importar Base de Datos
from database.conexion import SessionLocal
from database.models import Persona
from utilities.sanitizer import Sanitizer

class DialogoPersona(DialogoBase):
    """Formulario para crear una Persona (Estudiante, Instructor, etc.)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.centro_model = CentroModel()
        self.model = PersonaModel()

        self.sanitizer = Sanitizer()
        self.setWindowTitle("Nuevo Estudiante / Persona")
        self.setFixedSize(500, 650)
        self.persona = None

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)

        # --- Campos ---

        self.cedula = QLineEdit()
        # Se conecta la señal para forzar mayúsculas sin romper el cursor
        self.cedula.textChanged.connect(lambda: self.force_uppercase(self.cedula))
        layout.addWidget(QLabel("Cédula:"))
        layout.addWidget(self.cedula)

        self.nombre = QLineEdit()
        self.nombre.textChanged.connect(lambda: self.force_uppercase(self.nombre))
        layout.addWidget(QLabel("Nombre:"))
        layout.addWidget(self.nombre)

        self.correo = QLineEdit()
        self.correo.textChanged.connect(lambda: self.force_uppercase(self.correo))
        layout.addWidget(QLabel("Correo:"))
        layout.addWidget(self.correo)

        # Rol
        self.rol = QComboBox()
        roles = ["ESTUDIANTE", "COORDINADOR", "INSTRUCTOR", "OTRO"]
        self.rol.addItems(roles)
        layout.addWidget(QLabel("Rol:"))
        layout.addWidget(self.rol)

        # Centro
        self.centro = QComboBox()
        centros = self.centro_model.get_all()
        for centro in centros:
            # Aseguramos que el texto se muestre bien, pero el ID se mantenga integro
            texto = CentroModel.texto_desde_id(centro.id).title()
            self.centro.addItem(texto.upper(), centro.id)
        layout.addWidget(QLabel("Centro:"))
        layout.addWidget(self.centro)

        # --- Institución articulada (DINÁMICA) ---
        self.institucion = QComboBox()
        self.institucion.setEditable(True)
        # Forzar mayúsculas también en el campo editable del ComboBox
        self.institucion.lineEdit().textChanged.connect(
            lambda: self.force_uppercase(self.institucion.lineEdit())
        )

        # Cargar instituciones (Lógica movida a método para limpieza)
        self.cargar_instituciones()

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

        # Conexiones
        self.btn_aceptar.clicked.connect(self.validar_y_guardar)
        self.btn_cancelar.clicked.connect(self.reject)

    def force_uppercase(self, widget):
        """
        Convierte el texto a mayúsculas preservando la posición del cursor.
        Evita la recursividad y saltos de cursor molestos.
        """
        if not widget or not widget.text():
            return

        text = widget.text()
        # Solo actuar si hay caracteres en minúscula para evitar bucles innecesarios
        if text != text.upper():
            cursor_pos = widget.cursorPosition()
            widget.blockSignals(True)  # Prevenir recursividad
            widget.setText(text.upper())
            widget.blockSignals(False)
            widget.setCursorPosition(cursor_pos)  # Restaurar cursor

    def cargar_instituciones(self):
        """Carga la lista combinada de instituciones base y de la BD."""
        instituciones_base = [
            "SIS ECU 911", "TRANSITO Y MOVILIDAD", "SERVICIOS MUNICIPALES",
            "SERVICIOS MILITARES", "SEGURIDAD CIUDADANA", "MINISTERIO DE SALUD PUBLICA",
            "INSTITUTO ECUATORIANO DE SEGURIDAD SOCIAL", "CRUZ ROJA ECUATORIANA",
            "GESTION DE SINIESTROS", "GESTION DE RIESGOS, CIUDADANO"
        ]

        try:
            # CORRECCIÓN 3: Manejo seguro de la sesión
            with SessionLocal() as session:
                res = session.query(Persona.institucion_articulada).filter(
                    Persona.institucion_articulada.isnot(None)
                ).distinct().all()

                instituciones_db = [r[0].upper() for r in res if r[0]]
                # Set elimina duplicados, sorted ordena
                instituciones_finales = sorted(list(set(instituciones_base + instituciones_db)))
        except Exception as e:
            print(f"Advertencia: No se pudieron cargar instituciones de la BD: {e}")
            instituciones_finales = sorted(instituciones_base)

        self.institucion.addItems(instituciones_finales)

    def validar_correo(self, correo):
        # CORRECCIÓN 4: Regex mejorado para aceptar dominios modernos
        patron = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        return re.match(patron, correo) is not None

    def validar_y_guardar(self):
        """
        Recopila los datos, valida y guarda con manejo de errores robusto.
        """
        try:
            # Recopilación de datos (Dentro del Try por seguridad)
            cedula = self.cedula.text().strip()
            nombre = self.nombre.text().strip().upper()
            correo = self.correo.text().strip().upper()
            rol = self.rol.currentText().strip().upper()

            # Nota: currentData puede ser None si no hay selección
            centro_id = self.centro.currentData()

            institucion = self.institucion.currentText().strip().upper()

            # --- Validaciones ---
            if not cedula or not nombre or not correo:
                self.mostrar_error("Todos los campos son obligatorios.")
                return

            if not self.sanitizer.validar_cedula_ecuador(cedula):
                self.mostrar_error("Cédula inválida.")
                return

            if not self.validar_correo(correo):
                self.mostrar_error("El correo ingresado no tiene un formato válido.")
                return

            # --- Guardado ---
            datos_persona = {
                "cedula": cedula,
                "nombre": nombre,
                "correo": correo,
                "rol": rol,
                "centro_id": centro_id,
                "institucion_articulada": institucion
            }

            self.persona = self.model.create(datos_persona)
            self.accept()

        except IntegrityError:
            self.mostrar_error("Ya existe una persona con esta cédula o correo.")
        except Exception as e:
            # Imprimir el stack trace completo en la consola para saber exactamente dónde falla
            print("\n--- ERROR CRÍTICO AL GUARDAR PERSONA ---")
            traceback.print_exc()
            print("----------------------------------------\n")

            # Intentar mostrar el error en la UI
            self.mostrar_error(f"Error inesperado al guardar (revisa consola): {str(e)}")

    def mostrar_error(self, mensaje):
        """Helper por si DialogoBase no lo tiene"""
        if hasattr(super(), 'mostrar_error'):
            super().mostrar_error(mensaje)
        else:
            QMessageBox.critical(self, "Error", mensaje)