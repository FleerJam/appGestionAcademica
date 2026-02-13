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

import os
from PyQt6 import uic
from PyQt6.QtWidgets import QWidget, QMessageBox, QListWidgetItem, QApplication, QFileDialog
from PyQt6.QtCore import pyqtSignal, Qt
from sqlalchemy.exc import IntegrityError
from sqlalchemy import create_engine

from database.conexion import SessionLocal
from database.models import Persona
from models.tipos_cert_model import TipoCertificadoModel
from database import config


class ControladorConfiguraciones(QWidget):
    """
    Controlador para la gestión de configuraciones globales de la aplicación.

    Permite al usuario administrar:
    1. Conexión a base de datos (Local SQLite o Remota PostgreSQL).
    2. Rutas de carpetas compartidas para almacenamiento de archivos.
    3. Catálogo de tipos de certificados.
    4. Normalización y corrección de nombres de instituciones articuladas.
    """

    configuracion_guardada = pyqtSignal(dict)

    def __init__(self, parent=None):
        """Inicializa el controlador, carga la UI y los datos iniciales.

        Args:
            parent (QWidget, optional): Widget padre. Defaults to None.
        """
        super().__init__(parent)

        ruta_ui = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "views", "configuracion.ui"))
        if os.path.exists(ruta_ui):
            uic.loadUi(ruta_ui, self)
        else:
            QMessageBox.critical(self, "Error", f"No se encontró el archivo UI en: {ruta_ui}")
            return

        self.tipo_cert_model = TipoCertificadoModel()

        # Señales TAB BD
        self.radioBtn_Local.toggled.connect(self.al_cambiar_tipo_bd)
        self.btn_guardar_bd.clicked.connect(self.guardar_configuracion_bd)
        self.btn_probar_bd.clicked.connect(self.probar_conexion_bd)

        # --- NUEVO: Selector de carpeta compartida ---
        self.btn_buscar_carpeta.clicked.connect(self.seleccionar_carpeta_compartida)

        # Señales TAB CERTIFICADOS
        self.btn_AgregarCertificado.clicked.connect(self.agregar_certificado)
        self.btn_EliminarCertificado.clicked.connect(self.eliminar_certificado)

        # Señales TAB INSTITUCIONES
        self.listWidget_Instituciones.itemClicked.connect(self.al_seleccionar_institucion)
        self.btn_RenombrarInstitucion.clicked.connect(self.renombrar_institucion)

        # Cargas
        self.cargar_datos_bd()
        self.cargar_tipos_certificados()
        self.cargar_instituciones()

    def seleccionar_carpeta_compartida(self):
        """Abre un diálogo para seleccionar el directorio de almacenamiento de archivos.

        Actualiza el campo visual con la ruta seleccionada por el usuario.
        Se normaliza la ruta para compatibilidad con el sistema operativo.
        """
        carpeta = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta para Certificados Firmados")
        if carpeta:
            # Reemplazar slash por backslash para mejor lectura en Windows (opcional)
            carpeta = os.path.normpath(carpeta)
            self.lineEdit_CarpetaCompartida.setText(carpeta)

    def cargar_datos_bd(self):
        """Carga la configuración actual desde las variables de entorno a la UI.

        Lee los valores de conexión a base de datos (host, puerto, usuario, etc.)
        y la ruta de la carpeta compartida, rellenando los campos correspondientes.
        """
        if config.DB_TYPE == "sqlite":
            self.radioBtn_Local.setChecked(True)
        else:
            self.radioBtn_Online.setChecked(True)

        self.lineEdit_Url.setText(os.getenv("DB_HOST", ""))
        self.lineEdit_Puerto.setText(os.getenv("DB_PORT", "5432"))
        self.lineEdit_NombreBD.setText(os.getenv("DB_NAME_REMOTE", "academia_prod"))
        self.lineEdit_Usuario.setText(os.getenv("DB_USER", ""))
        self.lineEdit_Password.setText(os.getenv("DB_PASS", ""))

        # --- NUEVO: Cargar ruta compartida ---
        ruta_guardada = os.getenv("SHARED_FOLDER_PATH", config.DEFAULT_SHARED_DIR)
        self.lineEdit_CarpetaCompartida.setText(ruta_guardada)

    def al_cambiar_tipo_bd(self):
        """Ajusta valores por defecto al cambiar entre modo Local y Online.

        Si se selecciona 'Online' y los campos están vacíos, sugiere 'localhost'
        y el puerto '5432'.
        """
        if not self.radioBtn_Local.isChecked():
            if not self.lineEdit_Url.text(): self.lineEdit_Url.setText("localhost")
            if not self.lineEdit_Puerto.text(): self.lineEdit_Puerto.setText("5432")

    def probar_conexion_bd(self):
        """Realiza una prueba de conexión con los parámetros ingresados.

        - Para SQLite (Local): Verifica la existencia del archivo (simulado).
        - Para PostgreSQL (Online): Intenta crear un engine y conectar realmente.

        Muestra un mensaje modal con el resultado (Éxito o Error).
        """
        if self.radioBtn_Local.isChecked():
            QMessageBox.information(self, "Prueba", "Conexión local (SQLite) es un archivo, siempre funciona.")
            return

        host = self.lineEdit_Url.text().strip()
        port = self.lineEdit_Puerto.text().strip()
        db_name = self.lineEdit_NombreBD.text().strip()
        user = self.lineEdit_Usuario.text().strip()
        password = self.lineEdit_Password.text()

        if not all([host, port, db_name, user, password]):
            QMessageBox.warning(self, "Campos Vacíos", "Llena todos los campos.")
            return

        url_prueba = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            motor_prueba = create_engine(url_prueba, connect_args={'connect_timeout': 5})
            with motor_prueba.connect() as conexion:
                QApplication.restoreOverrideCursor()
                QMessageBox.information(self, "¡Éxito!", "Conexión exitosa a la base de datos PostgreSQL.")
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Fallo en conexión:\n{str(e)[:200]}...")

    def guardar_configuracion_bd(self):
        """Persiste la configuración actual en el archivo de entorno (.env).

        Guarda:
        - Tipo de base de datos (sqlite/postgresql).
        - Credenciales de conexión (si aplica).
        - Ruta de la carpeta compartida.

        Notifica al usuario que debe reiniciar para aplicar cambios.
        """
        tipo_bd = "sqlite" if self.radioBtn_Local.isChecked() else "postgresql"
        try:
            config.actualizar_env("DB_TYPE", tipo_bd)

            if tipo_bd == "postgresql":
                config.actualizar_env("DB_HOST", self.lineEdit_Url.text().strip())
                config.actualizar_env("DB_PORT", self.lineEdit_Puerto.text().strip())
                config.actualizar_env("DB_NAME_REMOTE", self.lineEdit_NombreBD.text().strip())
                config.actualizar_env("DB_USER", self.lineEdit_Usuario.text().strip())
                config.actualizar_env("DB_PASS", self.lineEdit_Password.text())

            # --- NUEVO: Guardar la ruta compartida ---
            ruta_compartida = self.lineEdit_CarpetaCompartida.text().strip()
            if ruta_compartida:
                config.actualizar_env("SHARED_FOLDER_PATH", ruta_compartida)

            QMessageBox.information(self, "Éxito",
                                    "Configuración guardada en .env.\nReinicie la aplicación para aplicar los cambios.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {e}")

    # --- (Los métodos de certificados e instituciones se mantienen idénticos a tu original) ---
    def cargar_tipos_certificados(self):
        """Carga y lista los tipos de certificados disponibles en la base de datos."""
        self.listWidget_Certificados.clear()
        try:
            certificados = self.tipo_cert_model.get_all()
            for cert in certificados:
                item = QListWidgetItem(cert.nombre)
                item.setData(Qt.ItemDataRole.UserRole, cert.id)
                self.listWidget_Certificados.addItem(item)
        except Exception as e:
            print(f"Error cargando certificados: {e}")

    def agregar_certificado(self):
        """Crea un nuevo tipo de certificado en la base de datos.

        Valida que el nombre no esté vacío y maneja duplicados.
        """
        nombre = self.lineEdit_NuevoCertificado.text().strip().upper()
        if not nombre:
            QMessageBox.warning(self, "Atención", "Ingrese un nombre para el certificado.")
            return
        try:
            self.tipo_cert_model.create({"nombre": nombre})
            self.lineEdit_NuevoCertificado.clear()
            self.cargar_tipos_certificados()
            QMessageBox.information(self, "Éxito", "Tipo de certificado agregado.")
        except IntegrityError:
            QMessageBox.warning(self, "Error", "Este tipo de certificado ya existe.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo agregar: {e}")

    def eliminar_certificado(self):
        """Elimina el tipo de certificado seleccionado tras confirmación."""
        item_seleccionado = self.listWidget_Certificados.currentItem()
        if not item_seleccionado: return

        cert_id = item_seleccionado.data(Qt.ItemDataRole.UserRole)
        cert_nombre = item_seleccionado.text()

        confirm = QMessageBox.question(self, "Confirmar", f"¿Eliminar '{cert_nombre}'?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirm == QMessageBox.StandardButton.Yes:
            try:
                if self.tipo_cert_model.delete(cert_id):
                    self.cargar_tipos_certificados()
                    QMessageBox.information(self, "Éxito", "Certificado eliminado.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar: {e}")

    def cargar_instituciones(self):
        """Carga la lista de instituciones articuladas únicas registradas.

        Filtra valores nulos o vacíos para mostrar solo instituciones válidas.
        """
        self.listWidget_Instituciones.clear()
        try:
            with SessionLocal() as session:
                instituciones = session.query(Persona.institucion_articulada).filter(
                    Persona.institucion_articulada.isnot(None)).filter(
                    Persona.institucion_articulada != "").distinct().all()
                for inst in instituciones:
                    if inst[0]: self.listWidget_Instituciones.addItem(inst[0].upper())
        except Exception as e:
            print(f"Error: {e}")

    def al_seleccionar_institucion(self, item):
        """Coloca el nombre de la institución seleccionada en el campo de edición.

        Args:
            item (QListWidgetItem): Ítem seleccionado en la lista.
        """
        self.lineEdit_RenombrarInstitucion.setText(item.text())

    def renombrar_institucion(self):
        """Renombra masivamente una institución en todos los registros de personas.

        Útil para corregir errores tipográficos. Solicita confirmación antes de
        ejecutar la actualización masiva (UPDATE) en la base de datos.
        """
        item_seleccionado = self.listWidget_Instituciones.currentItem()
        if not item_seleccionado: return

        nombre_antiguo = item_seleccionado.text()
        nombre_nuevo = self.lineEdit_RenombrarInstitucion.text().strip().upper()

        if not nombre_nuevo or nombre_nuevo == nombre_antiguo: return

        confirm = QMessageBox.question(self, "Confirmar Renombrado",
                                       f"¿Renombrar '{nombre_antiguo}' a '{nombre_nuevo}' en TODOS los estudiantes?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                with SessionLocal() as session:
                    session.query(Persona).filter(Persona.institucion_articulada == nombre_antiguo).update(
                        {"institucion_articulada": nombre_nuevo})
                    session.commit()
                self.lineEdit_RenombrarInstitucion.clear()
                self.cargar_instituciones()
                QMessageBox.information(self, "Éxito", "Instituciones actualizadas.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo actualizar: {e}")