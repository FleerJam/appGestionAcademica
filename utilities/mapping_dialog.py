from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QComboBox, QMessageBox, QFrame, QCheckBox, QScrollArea, QSpacerItem, QSizePolicy, QWidget)
from PyQt6.QtCore import Qt


class FilaMapeo(QFrame):
    """
    Componente visual que representa una Evaluación del Curso (BD)
    y permite seleccionar qué columna del Excel la alimenta.
    """

    def __init__(self, evaluacion_data, columnas_disponibles, parent=None):
        """
        Inicializa la fila de mapeo.

        Args:
            evaluacion_data (dict): Diccionario con datos de la evaluación ('id', 'nombre', 'porcentaje').
            columnas_disponibles (list[str]): Lista de nombres de columnas del Excel.
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self.evaluacion_id = evaluacion_data['id']
        self.nombre_eval = evaluacion_data['nombre']
        self.porcentaje = evaluacion_data['porcentaje']

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)


        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 1. Etiqueta con el nombre de la Evaluación (Definida en el Curso)
        lbl_nombre = QLabel(f"{self.nombre_eval} ({self.porcentaje}%)")
        lbl_nombre.setFont(QFont("Arial", 10))
        layout.addWidget(lbl_nombre, 1)

        # 2. Flecha indicadora visual (Hacia la izquierda, indicando entrada de datos)
        lbl_arrow = QLabel("⬅")
        lbl_arrow.setStyleSheet("color: #666; font-weight: bold;")
        lbl_arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_arrow.setFixedWidth(30)
        layout.addWidget(lbl_arrow)

        # 3. ComboBox con las columnas del Excel
        self.combo_columnas = QComboBox()
        self.combo_columnas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)  # <-- Esto es clave
        self.combo_columnas.addItem("Seleccionar columna...", None)

        for col in columnas_disponibles:
            self.combo_columnas.addItem(col, col)  # Data es el nombre de la columna

        # Intentar auto-seleccionar si el nombre coincide
        self._intentar_autoseleccion(self.nombre_eval, columnas_disponibles)

        layout.addWidget(self.combo_columnas, 1)

    def _intentar_autoseleccion(self, nombre_eval, columnas_excel):
        """
        Busca similitud entre el nombre de la evaluación y las columnas del Excel
        para preseleccionar automáticamente.

        Args:
            nombre_eval (str): Nombre de la evaluación.
            columnas_excel (list[str]): Lista de columnas del Excel.
        """
        nombre_norm = nombre_eval.lower().replace("_", " ").replace(".", "")

        # 1. Búsqueda exacta o contenida fuerte
        for idx, col in enumerate(columnas_excel):
            col_norm = col.lower()
            # Mapeamos índice + 1 porque el 0 es "Seleccionar..."
            if nombre_norm == col_norm or nombre_norm in col_norm or col_norm in nombre_norm:
                self.combo_columnas.setCurrentIndex(idx + 1)
                return

    def obtener_datos(self):
        """
        Obtiene la configuración actual de la fila.

        Returns:
            tuple: (bool: usar, str: id_evaluacion, str: columna_excel_seleccionada)
        """
        # Sin checkbox, 'usar' siempre es True implícitamente, pero el mapeo final
        # dependerá de si columna_excel_seleccionada no es None.
        return True, self.evaluacion_id, self.combo_columnas.currentData()


class DialogoMapeoNotas(QDialog):
    """
    Diálogo modal para vincular las columnas de un archivo Excel con las
    evaluaciones configuradas en el curso.
    """

    def __init__(self, columnas_disponibles, esquema_evaluacion, parent=None):
        """
        Inicializa el diálogo.

        Args:
            columnas_disponibles (list[str]): Columnas encontradas en el Excel.
            esquema_evaluacion (list[dict]): Evaluaciones del curso.
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self.setWindowTitle("Asignación de Calificaciones")
        self.resize(750, 500)

        self.columnas = columnas_disponibles
        self.esquema = esquema_evaluacion
        self.filas_ui = []

        self._init_ui()

    def _init_ui(self):
        """Construye la interfaz gráfica del diálogo."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # --- Encabezado ---
        lbl_titulo = QLabel("Vincular Esquema de Evaluación")
        lbl_titulo.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(lbl_titulo)

        lbl_instrucciones = QLabel(
            "A continuación se muestran las evaluaciones configuradas para este curso.<br>"
            "Por favor, seleccione qué <b>Columna del Excel</b> contiene los datos para cada evaluación."
        )
        lbl_instrucciones.setStyleSheet("color: #555;")
        layout.addWidget(lbl_instrucciones)

        # --- ScrollArea ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)


        contenido_scroll = QWidget()

        self.layout_scroll = QVBoxLayout(contenido_scroll)
        self.layout_scroll.setSpacing(8)
        self.layout_scroll.setContentsMargins(0, 0, 10, 0)

        # --- Generación de filas basadas en ESQUEMA ---
        if not self.esquema:
            lbl_vacio = QLabel("Este curso no tiene evaluaciones configuradas.")
            lbl_vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.layout_scroll.addWidget(lbl_vacio)
        else:
            for eval_item in self.esquema:
                # FilaMapeo(datos_evaluacion, columnas_excel)
                fila = FilaMapeo(eval_item, self.columnas)
                self.layout_scroll.addWidget(fila)
                self.filas_ui.append(fila)

        self.layout_scroll.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        scroll.setWidget(contenido_scroll)
        layout.addWidget(scroll)

        # --- Botones ---
        linea = QFrame()
        linea.setFrameShape(QFrame.Shape.HLine)
        linea.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(linea)

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_ok = QPushButton("Confirmar Importación")

        btn_ok.clicked.connect(self._validar_y_aceptar)
        btn_cancel.clicked.connect(self.reject)

        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_ok)
        layout.addLayout(btn_box)

    def _validar_y_aceptar(self):
        """Valida que no haya columnas duplicadas y acepta el diálogo."""
        columnas_usadas = []
        mapeo_valido = False

        for fila in self.filas_ui:
            _, _, col_excel = fila.obtener_datos()

            # Solo validamos si se ha seleccionado una columna
            if col_excel:
                if col_excel in columnas_usadas:
                    QMessageBox.warning(self, "Conflicto",
                                        f"La columna '{col_excel}' está asignada a más de una evaluación.\nCada evaluación debe venir de una columna distinta.")
                    return

                columnas_usadas.append(col_excel)
                mapeo_valido = True

        if not mapeo_valido and self.esquema:
            # Si hay esquema pero no hay columnas mapeadas
            res = QMessageBox.question(self, "Sin Notas",
                                       "No ha vinculado ninguna columna de notas.\n¿Desea importar SOLO los datos personales?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if res == QMessageBox.StandardButton.No:
                return

        self.accept()

    def obtener_mapeo(self):
        """
        Retorna el diccionario de mapeo final.

        Returns:
            dict: {columna_excel: evaluacion_uuid}
        """
        mapeo = {}
        for fila in self.filas_ui:
            _, id_eval, col_excel = fila.obtener_datos()
            if col_excel:  # Si hay columna seleccionada, se incluye
                mapeo[col_excel] = id_eval
        return mapeo