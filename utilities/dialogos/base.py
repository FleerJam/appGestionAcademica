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
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QMessageBox, QVBoxLayout, QLabel, QLineEdit,
    QHBoxLayout, QPushButton, QScrollArea, QWidget, QButtonGroup,
    QRadioButton
)

class DialogoBase(QDialog):
    """
    Clase base para todos los diálogos de la aplicación, proporcionando métodos comunes
    y configuración compartida.
    """

    def mostrar_error(self, mensaje, titulo="Error"):
        """
        Muestra un cuadro de diálogo modal de error crítico.

        Args:
            mensaje (str): El texto explicativo del error.
            titulo (str, optional): El título de la ventana del mensaje. Por defecto es "Error".
        """
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(titulo)
        msg.setText(mensaje)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()


class DialogoEntrada(DialogoBase):
    """
    Diálogo genérico para solicitar un dato de texto simple al usuario.
    Forza la entrada a mayúsculas.
    """

    def __init__(self, titulo="Entrada de datos", mensaje="Ingrese el dato:", placeholder="", parent=None):
        """
        Inicializa el diálogo de entrada.

        Args:
            titulo (str): Título de la ventana.
            mensaje (str): Etiqueta descriptiva para el campo de entrada.
            placeholder (str): Texto de ayuda visual dentro del campo de texto.
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setFixedSize(450, 220)
        self.valor_ingresado = None

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        self.label = QLabel(mensaje)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.input_dato = QLineEdit()
        self.input_dato.setPlaceholderText(placeholder)
        # Forzar mayúsculas
        self.input_dato.textChanged.connect(lambda: self.input_dato.setText(self.input_dato.text().upper()))
        self.input_dato.returnPressed.connect(self.validar_y_aceptar)
        layout.addWidget(self.input_dato)

        btn_layout = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_aceptar = QPushButton("Aceptar")
        self.btn_aceptar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_aceptar)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.btn_aceptar.clicked.connect(self.validar_y_aceptar)
        self.btn_cancelar.clicked.connect(self.reject)
        self.input_dato.setFocus()

    def validar_y_aceptar(self):
        """
        Valida que el campo no esté vacío y acepta el diálogo.
        Muestra un error si la validación falla.
        """
        texto = self.input_dato.text().strip()
        if not texto:
            self.mostrar_error("El campo no puede estar vacío.", "Faltan datos")
            return
        self.valor_ingresado = texto
        self.accept()

    def obtener_dato(self):
        """
        Recupera el valor ingresado por el usuario después de aceptar el diálogo.

        Returns:
            str: El texto ingresado o None si no se aceptó.
        """
        return self.valor_ingresado


class DialogoSeleccion(DialogoBase):
    """
    Diálogo genérico para seleccionar una opción única de una lista utilizando Radio Buttons.
    """

    def __init__(self, titulo="Seleccionar opción", mensaje="Seleccione un elemento:", opciones=None, parent=None):
        """
        Inicializa el diálogo de selección.

        Args:
            titulo (str): Título de la ventana.
            mensaje (str): Instrucción para el usuario.
            opciones (list, optional): Lista de opciones a mostrar.
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setFixedSize(500, 400)
        self.valor_seleccionado = None
        if opciones is None:
            opciones = []

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(15)

        self.label = QLabel(mensaje)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        # --- ÁREA DE SCROLL PARA RADIO BUTTONS ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        self.content_widget = QWidget()
        self.radio_layout = QVBoxLayout(self.content_widget)
        self.radio_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.radio_layout.setSpacing(10)

        self.grupo_radios = QButtonGroup(self)

        for i, opcion in enumerate(opciones):
            rb = QRadioButton(str(opcion))
            self.radio_layout.addWidget(rb)
            self.grupo_radios.addButton(rb)
            if i == 0:
                rb.setChecked(True)

        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)

        # --- BOTONES ---
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
        Verifica que se haya seleccionado una opción y cierra el diálogo.
        """
        boton_seleccionado = self.grupo_radios.checkedButton()
        if not boton_seleccionado:
            self.mostrar_error("Debe seleccionar una opción.", "Selección requerida")
            return
        self.valor_seleccionado = boton_seleccionado.text()
        self.accept()

    def obtener_seleccion(self):
        """
        Obtiene la opción seleccionada por el usuario.

        Returns:
            str: El texto de la opción seleccionada o None.
        """
        return self.valor_seleccionado