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
from PyQt6.QtCore import (
    QSize, Qt, QPropertyAnimation, QEasingCurve,
    QParallelAnimationGroup, QTimer
)
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QPushButton, QLabel, QWidget,
    QVBoxLayout, QFrame, QScrollArea, QLineEdit, QCheckBox,
    QHBoxLayout, QSpacerItem, QSizePolicy, QMessageBox
)

# --- IMPORTACIÓN DE PYQT CHARTS ---
from PyQt6.QtCharts import (
    QChart, QChartView, QHorizontalStackedBarSeries,
    QBarSet, QBarCategoryAxis, QValueAxis
)

# --- IMPORTACIONES DE CONTROLADORES Y MODELOS ---
from controllers.controlador_configuraciones import ControladorConfiguraciones
from controllers.controlador_certificados import ControladorCertificados as ControladorCertificados
from controllers.controlador_estudiantes import ControladorEstudiantes
from controllers.controlador_cursos import ControladorCursos
from controllers.controlador_estudiante_detalle import ControladorDetalleEstudiante
from controllers.controlador_curso_detalle import ControladorDetalleCurso
from controllers.controlador_plantillas_word import GestorPlantillasWord

# Diálogos
from utilities.dialogos import DialogoCurso as inputAdiestramiento
from utilities.dialogos import DialogoNotas as inputNotas
from utilities.dialogos import DialogoPersona as inputNewEstudiante
from utilities.dialogos import DialogoGenerarCertificados as inputGenCert

from utilities.importer_window import GestorImportacion
from models.matricula_model import MatriculaModel
from models.curso_model import CursoModel
from models.persona_model import PersonaModel
from models.certificado_model import CertificadoModel  # NUEVO: Importación necesaria para el conteo
from utilities.dialogos import DialogoReportes


class MasterController(QMainWindow):
    """Controlador Maestro (Ventana Principal) de la aplicación.

    Coordina la navegación entre las diferentes vistas (Cursos, Estudiantes, Certificados),
    administra el menú lateral (Sidebar), y gestiona el Dashboard principal con
    estadísticas y gráficos en tiempo real. Actúa como orquestador centralizando
    la actualización de caché y datos.
    """

    # ----------------------------
    # --- DECLARACIÓN DE WIDGETS ---
    # ----------------------------
    stackedWidget: QStackedWidget
    # Botones del Sidebar
    btn_inicio: QPushButton
    btn_estudiantes: QPushButton
    btn_adiestramientos: QPushButton
    btn_certificados: QPushButton
    btn_config: QPushButton
    btn_new_course: QPushButton
    btn_change_note: QPushButton
    btn_new_student: QPushButton
    btn_import: QPushButton
    btn_gen_cert: QPushButton
    btn_report: QPushButton
    btn_disenador: QPushButton

    # UI Elements
    lbl_card_1_value: QLabel
    lbl_card_2_value: QLabel
    lbl_card_3_value: QLabel
    card_1_icon: QLabel
    card_2_icon: QLabel
    card_3_icon: QLabel
    sidebar: QWidget
    chart_placeholder: QFrame
    btn_toggle_sidebar: QLabel

    # Header Sidebar
    lbl_logo: QLabel
    lbl_separator: QLabel
    lbl_titulo: QLabel
    frame_2: QWidget

    # ----------------------------
    # --- MÉTODO __INIT__ ---
    # ----------------------------
    def __init__(self):
        """Inicializa la ventana principal, carga componentes y datos iniciales."""
        super().__init__()
        # 1. Cargar UI
        uic.loadUi("views/mainWindow.ui", self)

        # 2. Configuración Inicial
        self._init_sidebar_animation()
        self._init_navigation()

        # 3. Timer Debounce (Para optimizar búsqueda en gráficos)
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self._renderizar_grafico_nativo)

        # 4. Inicialización de Variables de Caché
        self.cache_cursos = []
        self.cache_matriculas = {}  # Diccionario {curso_id: [lista_estados]}
        self.data_loaded = False

        # 5. Modelos
        self.curso_model = CursoModel()
        self.estudiante_model = PersonaModel()
        self.matricula_model = MatriculaModel()
        self.certificado_model = CertificadoModel()  # NUEVO: Inicializar modelo de certificados

        # 6. Setup Gráfico
        self._setup_native_chart_ui()

        # 7. Carga Inicial de Datos
        self.actualizar_cache_global()

        self._set_elementos_visibles(True)

    # ----------------------------
    # --- SETUP INTERFAZ & SIDEBAR ---
    # ----------------------------
    def _init_sidebar_animation(self):
        """Configura la animación del menú lateral (expandir/colapsar)."""
        """Configura la animación del menú lateral"""
        self.width_expandido = 260
        self.width_colapsado = 60

        self.sidebar.setMinimumWidth(self.width_expandido)
        self.sidebar.setMaximumWidth(self.width_expandido)

        self.animacion_min = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.animacion_max = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.grupo_animacion = QParallelAnimationGroup()
        self.grupo_animacion.addAnimation(self.animacion_min)
        self.grupo_animacion.addAnimation(self.animacion_max)

        self.btn_toggle_sidebar.setToolTip("Mostrar / Ocultar sidebar")
        self.btn_toggle_sidebar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_sidebar.mousePressEvent = self._on_toggle_sidebar_click

        if self.sidebar.layout() is None:
            layout_sidebar = QVBoxLayout(self.sidebar)
            self.sidebar.setLayout(layout_sidebar)

        layout = self.sidebar.layout()
        if layout:
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)

        self._configurar_botones_sidebar()
        self._configurar_icons_dashboard()

    def _init_navigation(self):
        """Inicializa los controladores de las vistas secundarias y los añade al Stack."""
        self.vista_estudiantes = ControladorEstudiantes()
        self.vista_cursos = ControladorCursos()
        self.vista_certificados = ControladorCertificados()
        self.vista_configuraciones = ControladorConfiguraciones()

        self.stackedWidget.insertWidget(1, self.vista_estudiantes)
        self.stackedWidget.insertWidget(2, self.vista_cursos)
        self.stackedWidget.insertWidget(3, self.vista_certificados)
        self.stackedWidget.insertWidget(4, self.vista_configuraciones)

        self.vista_estudiantes.signal_abrir_detalle.connect(self.mostrar_detalle_estudiante)
        self.vista_cursos.signal_abrir_detalle.connect(self.mostrar_detalle_curso)
        self.stackedWidget.currentChanged.connect(self._on_tab_changed)

        # Conectar la señal de configuraciones guardadas
        self.vista_configuraciones.configuracion_guardada.connect(self._on_config_guardada)

    def _configurar_botones_sidebar(self):
        """Asigna iconos, estilos y señales a los botones del menú lateral."""
        # Lista de botones para configuración masiva
        botones = [
            self.btn_inicio, self.btn_estudiantes, self.btn_adiestramientos,
            self.btn_certificados, self.btn_config, self.btn_new_course,
            self.btn_change_note, self.btn_new_student, self.btn_import,
            self.btn_gen_cert, self.btn_report,
            self.btn_disenador
        ]

        ALTURA_BOTON = 45

        # --- Conexiones e Iconos ---
        self.btn_inicio.clicked.connect(lambda: self.cambiar_pagina(0))
        self.btn_inicio.setIcon(QIcon("assets/icons/home.png"))

        self.btn_estudiantes.clicked.connect(lambda: self.cambiar_pagina(1))
        self.btn_estudiantes.setIcon(QIcon("assets/icons/button_estudiantes.png"))

        self.btn_adiestramientos.clicked.connect(lambda: self.cambiar_pagina(2))
        self.btn_adiestramientos.setIcon(QIcon("assets/icons/button_adiestramiento.png"))

        self.btn_certificados.clicked.connect(lambda: self.cambiar_pagina(3))
        self.btn_certificados.setIcon(QIcon("assets/icons/certificado.png"))

        # NUEVO: Conectar el botón de configuración a la página 4
        self.btn_config.clicked.connect(lambda: self.cambiar_pagina(4))
        self.btn_config.setIcon(QIcon("assets/icons/config.png"))

        self.btn_new_course.clicked.connect(self.nuevo_adiestramiento)
        self.btn_new_course.setIcon(QIcon("assets/icons/agregar.png"))

        self.btn_change_note.clicked.connect(self.cambiar_notas)
        self.btn_change_note.setIcon(QIcon("assets/icons/calificaciones.png"))

        self.btn_new_student.clicked.connect(self.nuevo_estudiante)
        self.btn_new_student.setIcon(QIcon("assets/icons/agregar_estudiante.png"))

        self.btn_import.clicked.connect(self.importar_archivo)
        self.btn_import.setIcon(QIcon("assets/icons/button_new_importation.png"))

        self.btn_gen_cert.clicked.connect(self.generar_certificados)
        self.btn_gen_cert.setIcon(QIcon("assets/icons/gen_cert.png"))

        self.btn_report.clicked.connect(self.abrir_reportes)
        self.btn_report.setIcon(QIcon("assets/icons/gen_report.png"))

        self.btn_disenador.clicked.connect(self.abrir_disenador)
        self.btn_disenador.setIcon(QIcon("assets/icons/design.png"))

        for btn in botones:
            if btn:
                btn.setFixedHeight(ALTURA_BOTON)
                btn.setIconSize(QSize(24, 24))
                btn.setStyleSheet("text-align: left; padding-left: 15px;")

        self.sidebar.setStyleSheet("padding-left: 15px; padding-right: 15px;")

    def _configurar_icons_dashboard(self):
        """Carga y escala los iconos de las tarjetas del dashboard principal."""
        try:
            self.card_1_icon.setPixmap(
                QPixmap("assets/icons/students_dashboard.png").scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                                                                      Qt.TransformationMode.SmoothTransformation))
            self.card_2_icon.setPixmap(
                QPixmap("assets/icons/dashboard_cursos.png").scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                                                                    Qt.TransformationMode.SmoothTransformation))
            self.card_3_icon.setPixmap(
                QPixmap("assets/icons/cert_dashboard.png").scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                                                                  Qt.TransformationMode.SmoothTransformation))
        except:
            pass

    # ----------------------------
    # --- LÓGICA DE ANIMACIÓN (TOGGLE) ---
    # ----------------------------
    def _on_toggle_sidebar_click(self, event):
        """Maneja el evento de clic en el botón de hamburguesa del sidebar."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_sidebar()

    def toggle_sidebar(self):
        """Ejecuta la animación de apertura o cierre del menú lateral."""
        ancho_actual = self.sidebar.width()
        duration = 500
        curve = QEasingCurve.Type.InOutQuart

        try:
            self.grupo_animacion.finished.disconnect()
        except TypeError:
            pass

        if ancho_actual == self.width_expandido:
            self._set_elementos_visibles(False)
            self.animacion_min.setDuration(duration)
            self.animacion_min.setStartValue(ancho_actual)
            self.animacion_min.setEndValue(self.width_colapsado)
            self.animacion_min.setEasingCurve(curve)

            self.animacion_max.setDuration(duration)
            self.animacion_max.setStartValue(ancho_actual)
            self.animacion_max.setEndValue(self.width_colapsado)
            self.animacion_max.setEasingCurve(curve)
            self.grupo_animacion.start()
        else:
            self.animacion_min.setDuration(duration)
            self.animacion_min.setStartValue(ancho_actual)
            self.animacion_min.setEndValue(self.width_expandido)
            self.animacion_min.setEasingCurve(curve)

            self.animacion_max.setDuration(duration)
            self.animacion_max.setStartValue(ancho_actual)
            self.animacion_max.setEndValue(self.width_expandido)
            self.animacion_max.setEasingCurve(curve)

            self.grupo_animacion.finished.connect(lambda: self._set_elementos_visibles(True))
            self.grupo_animacion.start()

    def _set_elementos_visibles(self, visible: bool):
        """Muestra u oculta textos e iconos del sidebar según su estado (expandido/colapsado)."""
        base_style = "margin-bottom: 2px;"

        if hasattr(self, 'lbl_logo'):
            if visible:
                self.lbl_logo.setPixmap(
                    QPixmap("assets/icons/ECU911.png").scaled(150, 125, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                              Qt.TransformationMode.SmoothTransformation))
                self.lbl_logo.setVisible(True)
                self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.lbl_logo.setStyleSheet("padding-top: 0px; padding-bottom: 0px;")
            else:
                self.lbl_logo.setVisible(False)

        if visible:
            self.sidebar.setStyleSheet("padding-left: 7px; padding-right: 7px;")
            self.btn_toggle_sidebar.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.btn_toggle_sidebar.setStyleSheet("padding: 0px; ")
            style_btn = f"{base_style} text-align: left; padding-left: 15px;"
            if hasattr(self, 'frame_2') and self.frame_2.layout():
                self.frame_2.layout().setContentsMargins(9, 9, 9, 9)
        else:
            self.sidebar.setStyleSheet("padding-left: 5px; padding-right: 7px;")
            self.btn_toggle_sidebar.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.btn_toggle_sidebar.setStyleSheet(
                "padding-top: 55px; padding-bottom: 55px; padding-left: 0px; padding-right: 0px;")
            style_btn = f"{base_style} text-align: center; padding-left: 7px;"
            if hasattr(self, 'frame_2') and self.frame_2.layout():
                self.frame_2.layout().setContentsMargins(9, 9, 9, 9)

        if hasattr(self, 'lbl_separator'):
            self.lbl_separator.setHidden(not visible)

        botones = [
            (self.btn_inicio, "   Inicio"),
            (self.btn_estudiantes, "   Estudiantes"),
            (self.btn_adiestramientos, "   Cursos"),
            (self.btn_certificados, "   Certificados"),
            (self.btn_config, "   Configuración"),
            (self.btn_new_student, "   Nuevo Estudiante"),
            (self.btn_new_course, "   Nuevo Curso"),
            (self.btn_change_note, "   Cambiar Notas"),
            (self.btn_import, "   Importar Excel/ODS"),
            (self.btn_gen_cert, "   Generar Certificados"),
            (self.btn_report, "   Reportes"),
            (self.btn_disenador, "   Diseñador de Plantillas")
        ]

        for btn, texto_original in botones:
            if not btn: continue
            if visible:
                btn.setText(texto_original)
                btn.setStyleSheet(style_btn)
                btn.setToolTip("")
            else:
                btn.setText("")
                btn.setStyleSheet(style_btn)
                btn.setToolTip(texto_original.strip())

    # ----------------------------
    # --- LÓGICA DE DATOS Y CACHÉ ---
    # ----------------------------
    def actualizar_cache_global(self):
        """Sincroniza el estado de la aplicación con la base de datos.

        Recarga los modelos, actualiza las estadísticas del Dashboard, regenera
        los gráficos y notifica a los controladores hijos para que refresquen
        sus tablas. Debe llamarse tras cualquier operación de escritura (CRUD).
        """
        """
        FUNCIÓN PRINCIPAL DE ACTUALIZACIÓN.
        Debe ser llamada cada vez que se realice un cambio en la Base de Datos
        (Insert, Update, Delete) para mantener la UI sincronizada.
        """
        try:
            # 1. Recargar datos crudos desde Modelos
            self.cache_cursos = self.curso_model.search() or []
            raw_matriculas = self.matricula_model.search() or []

            # 2. Reconstruir Caché de Matrículas (Optimizado para Gráficos)
            self.cache_matriculas = {}
            for m in raw_matriculas:
                if m.curso_id not in self.cache_matriculas:
                    self.cache_matriculas[m.curso_id] = []
                # Normalización de estado
                estado_str = str(m.estado).upper() if m.estado else "SIN ESTADO"
                self.cache_matriculas[m.curso_id].append(estado_str)

            self.data_loaded = True

            # 3. Actualizar Dashboard
            self._actualizar_dashboard_cards()

            # 4. Actualizar Gráfico Nativo
            self._renderizar_grafico_nativo()

            # 5. Notificar a las Vistas Hijas (Tablas)
            if hasattr(self.vista_cursos, 'recargar_datos'):
                self.vista_cursos.recargar_datos()

            if hasattr(self.vista_estudiantes, 'recargar_datos'):
                self.vista_estudiantes.recargar_datos()

        except Exception as e:
            print(f"Error crítico actualizando caché: {e}")
            # Aquí podrías poner un QMessageBox si deseas alertar al usuario

    def _actualizar_dashboard_cards(self):
        """Actualiza solo los números de las tarjetas"""
        try:
            total_estudiantes = self.estudiante_model.count()
            self.lbl_card_1_value.setText(str(total_estudiantes))
            self.lbl_card_2_value.setText(str(len(self.cache_cursos)))

            # --- ACTUALIZACIÓN DE TARJETA 3: CERTIFICADOS PENDIENTES DE FIRMA ---
            # Lógica sincronizada estrictamente con ControladorCertificados:
            # 1. Obtenemos TODOS los certificados generados (Tabla Certificado).
            # 2. Obtenemos TODAS las matrículas para verificar firma.
            # 3. Cruzamos: Si existe Certificado pero Matrícula NO tiene 'ruta_pdf_firmado' -> PENDIENTE.

            todos_certificados = self.certificado_model.search() or []
            todas_matriculas = self.matricula_model.search() or []

            # Mapa para búsqueda rápida: (persona_id, curso_id) -> Objeto Matricula
            mapa_matriculas = {
                (m.persona_id, m.curso_id): m
                for m in todas_matriculas
            }

            cont_faltan_firmar = 0

            for cert in todos_certificados:
                # Buscamos la matrícula correspondiente
                mat = mapa_matriculas.get((cert.persona_id, cert.curso_id))

                tiene_firma = False
                # La única fuente de verdad para "FIRMADO" es la ruta en la matrícula
                if mat and mat.ruta_pdf_firmado:
                    tiene_firma = True

                if not tiene_firma:
                    cont_faltan_firmar += 1

            # Actualizar el Label de la tarjeta
            self.lbl_card_3_value.setText(str(cont_faltan_firmar))

        except Exception as e:
            print(f"Error actualizando dashboard: {e}")
            self.lbl_card_3_value.setText("0")

    # ------------------------------------------------------
    # --- GRÁFICO NATIVO ---
    # ------------------------------------------------------
    def _setup_native_chart_ui(self):
        """Configura e inserta el widget QChart en el placeholder de la UI."""
        if self.chart_placeholder.layout() is None:
            main_layout = QVBoxLayout(self.chart_placeholder)
            main_layout.setContentsMargins(0, 0, 0, 0)
        else:
            main_layout = self.chart_placeholder.layout()

        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(5, 5, 5, 5)

        self.txt_chart_search = QLineEdit()
        self.txt_chart_search.setPlaceholderText("🔍 Buscar curso...")
        self.txt_chart_search.textChanged.connect(self.on_filter_interaction)

        self.chk_en_curso = QCheckBox("En curso")
        self.chk_en_curso.setChecked(True)
        self.chk_aprobo = QCheckBox("Aprobado")
        self.chk_aprobo.setChecked(True)
        self.chk_reprobo = QCheckBox("Reprobado")
        self.chk_reprobo.setChecked(True)
        self.chk_no_realizo = QCheckBox("No realizo")
        self.chk_no_realizo.setChecked(True)

        self.chk_en_curso.setStyleSheet("color: #3498db; font-weight: bold;")
        self.chk_aprobo.setStyleSheet("color: #2ecc71; font-weight: bold;")
        self.chk_reprobo.setStyleSheet("color: #e74c3c; font-weight: bold;")
        self.chk_no_realizo.setStyleSheet("color: #95a5a6; font-weight: bold;")

        for chk in [self.chk_en_curso, self.chk_aprobo, self.chk_reprobo, self.chk_no_realizo]:
            chk.toggled.connect(self.on_filter_interaction)

        filter_layout.addWidget(self.txt_chart_search)
        filter_layout.addWidget(self.chk_en_curso)
        filter_layout.addWidget(self.chk_aprobo)
        filter_layout.addWidget(self.chk_reprobo)
        filter_layout.addWidget(self.chk_no_realizo)
        filter_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.chart = QChart()
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.chart.setBackgroundRoundness(0)
        self.chart.setMargins(self.chart.margins())
        self.chart.legend().setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chart.legend().setFont(QFont("Arial", 9, QFont.Weight.Bold))

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.scroll_chart = QScrollArea()
        self.scroll_chart.setWidget(self.chart_view)
        self.scroll_chart.setWidgetResizable(True)
        self.scroll_chart.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_chart.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        main_layout.addWidget(filter_widget)
        main_layout.addWidget(self.scroll_chart)

    def on_filter_interaction(self):
        """Inicia el temporizador de debounce al modificar filtros del gráfico."""
        self.debounce_timer.start()

    def _renderizar_grafico_nativo(self):
        """Genera y muestra el gráfico de barras apiladas con los datos actuales.

        Filtra los cursos por nombre y cuenta los estados (Aprobado, Reprobado, etc.)
        según los CheckBox activados. Redimensiona dinámicamente la altura del gráfico.
        """
        if not self.data_loaded: return

        texto = self.txt_chart_search.text().lower().strip()
        cursos_filtrados = [c for c in self.cache_cursos if texto in c.nombre.lower()]

        if not cursos_filtrados:
            self.chart.removeAllSeries()
            for axis in self.chart.axes(): self.chart.removeAxis(axis)
            self.chart.setTitle("No se encontraron resultados")
            return

        def obtener_cantidad_total(curso):
            return len(self.cache_matriculas.get(curso.id, []))

        cursos_filtrados.sort(key=obtener_cantidad_total)
        # Limitamos a los últimos 100 para rendimiento si hay demasiados
        cursos_filtrados = cursos_filtrados[-100:]

        set_en_curso = QBarSet("En curso")
        set_aprobo = QBarSet("Aprobado")
        set_reprobo = QBarSet("Reprobado")
        set_no_realizo = QBarSet("No realizó")

        set_en_curso.setColor(QColor("#3498db"))
        set_aprobo.setColor(QColor("#2ecc71"))
        set_reprobo.setColor(QColor("#e74c3c"))
        set_no_realizo.setColor(QColor("#95a5a6"))

        nombres_cursos = []
        max_valor_x = 0

        for curso in cursos_filtrados:
            estados = self.cache_matriculas.get(curso.id, [])

            c_en = estados.count("EN CURSO")
            c_apr = estados.count("APROBADO")
            c_rep = estados.count("REPROBADO")
            c_no = estados.count("NO REALIZO")

            total_vis = 0
            if self.chk_en_curso.isChecked(): total_vis += c_en
            if self.chk_aprobo.isChecked(): total_vis += c_apr
            if self.chk_reprobo.isChecked(): total_vis += c_rep
            if self.chk_no_realizo.isChecked(): total_vis += c_no

            nombres_cursos.append(f"{curso.nombre} (Total: {total_vis})")

            set_en_curso.append(c_en if self.chk_en_curso.isChecked() else 0)
            set_aprobo.append(c_apr if self.chk_aprobo.isChecked() else 0)
            set_reprobo.append(c_rep if self.chk_reprobo.isChecked() else 0)
            set_no_realizo.append(c_no if self.chk_no_realizo.isChecked() else 0)

            if total_vis > max_valor_x: max_valor_x = total_vis

        series = QHorizontalStackedBarSeries()
        series.append(set_en_curso)
        series.append(set_aprobo)
        series.append(set_reprobo)
        series.append(set_no_realizo)
        series.setLabelsVisible(True)
        series.setLabelsFormat("@value")

        self.chart.removeAllSeries()
        for axis in self.chart.axes(): self.chart.removeAxis(axis)

        self.chart.addSeries(series)
        self.chart.setTitle(f"Resumen de Cursos ({len(cursos_filtrados)} mostrados)")

        axis_y = QBarCategoryAxis()
        axis_y.append(nombres_cursos)
        self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        series.attachAxis(axis_y)

        axis_x = QValueAxis()
        axis_x.setRange(0, max(5, max_valor_x + 1))
        axis_x.setLabelFormat("%d")
        self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        series.attachAxis(axis_x)

        altura_necesaria = max(400, (len(cursos_filtrados) * 40) + 100)
        self.chart_view.setMinimumHeight(altura_necesaria)

    # ----------------------------
    # --- PROXY EVENTS ---
    # ----------------------------
    def nuevo_adiestramiento(self):
        """Abre el diálogo para crear un nuevo curso."""
        inputAdiestramiento().exec()
        # Llamada centralizada post-edición
        self.actualizar_cache_global()
        # NUEVO: Refrescar la lista de cursos en el controlador de certificados
        if hasattr(self.vista_certificados, 'actualizar_listado_cursos'):
            self.vista_certificados.actualizar_listado_cursos()

    def cambiar_notas(self):
        """Abre el diálogo de gestión de calificaciones."""
        inputNotas().exec()
        self.actualizar_cache_global()

    def nuevo_estudiante(self):
        """Abre el diálogo para registrar un nuevo estudiante."""
        inputNewEstudiante().exec()
        self.actualizar_cache_global()

    def importar_archivo(self):
        """Inicia el asistente de importación desde Excel/ODS."""
        GestorImportacion(self).ejecutar()
        # La función actualizar_cache_global ya se encarga de refrescar las sub-vistas
        self.actualizar_cache_global()
        # Forzar cambio de tab si es necesario, o mantener
        self._on_tab_changed(self.stackedWidget.currentIndex())

    def generar_certificados(self):
        """Abre el diálogo de generación masiva de certificados."""
        inputGenCert().exec()
        self.actualizar_cache_global()

    def abrir_disenador(self):
        """Abre el gestor de plantillas Word."""
        dlg = GestorPlantillasWord(parent=self)
        dlg.exec()

    def cambiar_pagina(self, index):
        """Cambia la vista actual en el StackedWidget."""
        self.stackedWidget.setCurrentIndex(index)

    def _on_tab_changed(self, index):
        """Evento disparado al cambiar de pestaña; refresca datos específicos."""
        if index == 0:
            self._actualizar_dashboard_cards()
        elif index == 1 and hasattr(self.vista_estudiantes, 'cargar_datos_tabla'):
            self.vista_estudiantes.cargar_datos_tabla()
        elif index == 2 and hasattr(self.vista_cursos, 'cargar_datos_tabla'):
            self.vista_cursos.cargar_datos_tabla()
        elif index == 3 and hasattr(self.vista_certificados, 'actualizar_listado_cursos'):
            # NUEVO: Actualizamos el combo de cursos en Certificados
            self.vista_certificados.actualizar_listado_cursos()

    def mostrar_detalle_estudiante(self, estudiante):
        """Navega a la vista de detalle del estudiante."""
        self.vista_detalle_est = ControladorDetalleEstudiante(estudiante)

        # Función interna para manejar el retorno y actualización
        def on_volver_estudiante():
            self.cambiar_pagina(1)
            self.actualizar_cache_global()

        self.vista_detalle_est.signal_volver.connect(on_volver_estudiante)
        self.stackedWidget.addWidget(self.vista_detalle_est)
        self.stackedWidget.setCurrentIndex(self.stackedWidget.count() - 1)

    def mostrar_detalle_curso(self, curso):
        """Navega a la vista de detalle del curso."""
        self.vista_detalle_curso = ControladorDetalleCurso(curso)

        # Función interna para manejar el retorno y actualización
        def on_volver_curso():
            self.cambiar_pagina(2)
            self.actualizar_cache_global()

        self.vista_detalle_curso.signal_volver.connect(on_volver_curso)
        self.stackedWidget.addWidget(self.vista_detalle_curso)
        self.stackedWidget.setCurrentIndex(self.stackedWidget.count() - 1)

    def abrir_reportes(self):
        """Abre el diálogo de generación de reportes avanzados."""
        dlg = DialogoReportes(self)
        dlg.exec()

    def _on_config_guardada(self, nueva_config):
        """
        Callback que se ejecuta cuando el ControladorConfiguraciones emite
        la señal de guardado.
        """
        print("MasterController recibió la nueva configuración:", nueva_config)
        # Aquí puedes agregar la lógica para reiniciar la conexión a la base de datos,
        # recargar variables globales, etc., basándote en los nuevos datos.