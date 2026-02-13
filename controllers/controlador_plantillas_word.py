import os
import shutil
import uuid
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QLineEdit, QMessageBox, QListWidget, QHBoxLayout, QGroupBox, QListWidgetItem,
    QApplication
)
from PyQt6.QtCore import Qt
from models.plantilla_certificado_model import PlantillaCertificadoModel


class GestorPlantillasWord(QDialog):
    """Gestor para la carga y administración de plantillas de certificado en formato Word (.docx).

    Permite subir archivos .docx que se almacenan como binarios en la base de datos,
    listar las plantillas existentes y eliminarlas. Proporciona ayuda visual sobre
    las etiquetas disponibles para el reemplazo de datos.
    """

    def __init__(self, parent=None):
        """Inicializa el diálogo de gestión de plantillas.

        Args:
            parent (QWidget, optional): Widget padre. Defaults to None.
        """
        super().__init__(parent)
        self.setWindowTitle("Gestor de Plantillas Word (.docx)")
        self.setFixedSize(700, 600)
        self.model = PlantillaCertificadoModel()
        self.ruta_docx_seleccionado = None

        self.init_ui()
        self.cargar_existentes()

    def init_ui(self):
        """Configura la interfaz gráfica del diálogo.

        Divide la ventana en dos columnas:
        - Izquierda: Instrucciones, lista de tags copiables y formulario de carga.
        - Derecha: Lista de plantillas registradas y botón de eliminar.
        """
        # Layout principal de toda la ventana
        main_layout = QHBoxLayout(self)

        # ---------------------------------------------------------
        # COLUMNA IZQUIERDA (Instrucciones, Códigos, Formulario)
        # ---------------------------------------------------------
        left_layout = QVBoxLayout()

        # 1. Instrucciones
        lbl_info = QLabel(
            "<h3>¿Cómo crear una plantilla?</h3>"
            "<ol>"
            "<li>Abra <b>Microsoft Word</b> y diseñe su certificado.</li>"
            "<li>Use los códigos de abajo (Ej: <b>{{ nombre_estudiante }}</b>).</li>"
            "<li>Guarde como <b>.docx</b> y cárguelo aquí.</li>"
            "</ol>"
        )
        lbl_info.setStyleSheet(
            "background-color: #e8f8f5; padding: 10px; border-radius: 5px; border: 1px solid #1abc9c;")
        lbl_info.setWordWrap(True)
        lbl_info.setMaximumHeight(150)
        left_layout.addWidget(lbl_info)

        # 2. Etiquetas Copiables
        group_tags = QGroupBox("Códigos de Datos (Doble Clic para Copiar)")
        layout_tags = QVBoxLayout(group_tags)

        self.lista_tags = QListWidget()
        self.lista_tags.setAlternatingRowColors(True)

        self.etiquetas_info = [
            ("Nombre del Estudiante", "{{ nombre_estudiante }}"),
            ("Cédula del Estudiante", "{{ cedula_estudiante }}"),
            ("Nombre del Curso", "{{ curso_nombre }}"),
            ("Horas de Duración", "{{ horas_curso }}"),
            ("Fecha de Inicio", "{{ fecha_inicio }}"),
            ("Fecha de Finalización", "{{ fecha_final }}"),
            ("Nota Final", "{{ nota_final }}"),
            ("Código de Validación", "{{ codigo_validacion }}"),
            ("Fecha de Emisión", "{{ fecha_emision }}")
        ]

        for desc, tag in self.etiquetas_info:
            item = QListWidgetItem(f"{tag}   ---   ({desc})")
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.lista_tags.addItem(item)

        self.lista_tags.itemDoubleClicked.connect(self.copiar_etiqueta)
        layout_tags.addWidget(self.lista_tags)
        left_layout.addWidget(group_tags)

        # 3. Formulario de Carga
        group_new = QGroupBox("Registrar Nueva Plantilla")
        layout_new = QVBoxLayout(group_new)

        row_nombre = QHBoxLayout()
        row_nombre.addWidget(QLabel("Nombre:"))
        self.input_nombre = QLineEdit()
        self.input_nombre.setPlaceholderText("Ej: Diploma Honorífico 2026")
        row_nombre.addWidget(self.input_nombre)
        layout_new.addLayout(row_nombre)

        layout_file = QHBoxLayout()
        self.lbl_archivo = QLabel("Ningún archivo seleccionado")
        self.lbl_archivo.setStyleSheet("color: #7f8c8d; font-style: italic;")
        btn_cargar = QPushButton("📂 Seleccionar Word")
        btn_cargar.clicked.connect(self.seleccionar_archivo)
        layout_file.addWidget(btn_cargar)
        layout_file.addWidget(self.lbl_archivo)
        layout_new.addLayout(layout_file)

        btn_guardar = QPushButton("Guardar Plantilla")
        btn_guardar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; height: 30px;")
        btn_guardar.clicked.connect(self.guardar_plantilla)
        layout_new.addWidget(btn_guardar)

        left_layout.addWidget(group_new)
        main_layout.addLayout(left_layout, 6)

        # ---------------------------------------------------------
        # COLUMNA DERECHA (Lista de Existentes)
        # ---------------------------------------------------------
        right_layout = QVBoxLayout()

        group_list = QGroupBox("Plantillas Registradas")
        layout_list = QVBoxLayout(group_list)

        self.lista_existentes = QListWidget()
        layout_list.addWidget(self.lista_existentes)

        btn_eliminar = QPushButton("Eliminar Seleccionada")
        btn_eliminar.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
        btn_eliminar.clicked.connect(self.eliminar_plantilla)
        layout_list.addWidget(btn_eliminar)

        right_layout.addWidget(group_list)
        main_layout.addLayout(right_layout, 4)

    def copiar_etiqueta(self, item):
        """Copia el texto de la etiqueta seleccionada al portapapeles del sistema."""
        texto = item.data(Qt.ItemDataRole.UserRole)
        QApplication.clipboard().setText(texto)
        QMessageBox.information(self, "Copiado", f"Código '{texto}' copiado al portapapeles.")

    def seleccionar_archivo(self):
        """Abre un diálogo para seleccionar un archivo .docx local."""
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar Word", "", "Word (*.docx)")
        if ruta:
            self.ruta_docx_seleccionado = ruta
            self.lbl_archivo.setText(os.path.basename(ruta))
            self.lbl_archivo.setStyleSheet("color: #27ae60; font-weight: bold;")

    def guardar_plantilla(self):
        """Lee el archivo seleccionado y lo guarda como binario en la base de datos."""
        nombre = self.input_nombre.text().strip().upper()
        if not nombre or not self.ruta_docx_seleccionado:
            QMessageBox.warning(self, "Error", "Faltan datos.")
            return

        try:
            # 1. LEER EL ARCHIVO EN BYTES
            with open(self.ruta_docx_seleccionado, 'rb') as f:
                contenido_bytes = f.read()

            # Extraemos el nombre original del archivo para guardarlo como referencia
            nombre_original_archivo = os.path.basename(self.ruta_docx_seleccionado)

            # 2. GUARDAR EN BD (Columna archivo_binario)
            self.model.create({
                "nombre": nombre,
                "archivo_binario": contenido_bytes,     # <-- Aquí viaja el archivo real
                "configuracion_json": "TYPE_WORD",
                "ancho_px": 0, "alto_px": 0, "numero_paginas": 1
            })

            QMessageBox.information(self, "Éxito", "Plantilla guardada en la Base de Datos correctamente.")

            # Limpieza UI
            self.ruta_docx_seleccionado = None
            self.input_nombre.clear()
            self.lbl_archivo.setText("Ningún archivo seleccionado")
            self.cargar_existentes()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar la plantilla: {str(e)}")

    def cargar_existentes(self):
        """Actualiza la lista visual con las plantillas Word almacenadas en BD."""
        self.lista_existentes.clear()
        for p in self.model.get_all():
            if p.configuracion_json == "TYPE_WORD":
                item = QListWidgetItem(f"{p.nombre}")
                item.setData(Qt.ItemDataRole.UserRole, p.id)
                self.lista_existentes.addItem(item)

    def eliminar_plantilla(self):
        """Elimina la plantilla seleccionada de la base de datos."""
        item = self.lista_existentes.currentItem()

        if not item:
            QMessageBox.warning(self, "Atención", "Seleccione una plantilla de la lista.")
            return

        respuesta = QMessageBox.question(
            self,
            "Eliminar",
            "¿Estás seguro de que deseas borrar esta plantilla de la base de datos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if respuesta == QMessageBox.StandardButton.Yes:
            id_plantilla = item.data(Qt.ItemDataRole.UserRole)

            try:
                # Ya no necesitamos buscar rutas locales físicas ni usar os.remove()
                # porque el archivo está embebido en la base de datos.
                # Al borrar el registro de la BD, se libera ese espacio.
                self.model.delete(id_plantilla)

                # Actualizar la lista visual
                self.cargar_existentes()
                QMessageBox.information(self, "Eliminado", "Plantilla eliminada correctamente de la Base de Datos.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo eliminar la plantilla: {str(e)}")