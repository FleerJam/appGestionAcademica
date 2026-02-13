#  Copyright (c) 2026 Fleer

import csv
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit,
    QHBoxLayout, QPushButton, QListWidget, QListWidgetItem,
    QGroupBox, QRadioButton, QFileDialog, QMessageBox,
    QProgressBar, QApplication
)
from sqlalchemy import text

# --- IMPORTACIÓN DE MODELOS (DAO) ---
from models.curso_model import CursoModel
from models.matricula_model import MatriculaModel
from models.evaluacion_curso_model import EvaluacionCursoModel


class DialogoReportes(QDialog):
    """
    Diálogo para la generación y exportación de reportes CSV (Generales y Detallados).
    Permite filtrar cursos y elegir el tipo de salida.
    """

    def __init__(self, parent=None):
        """
        Inicializa la interfaz del generador de reportes.

        Args:
            parent (QWidget, optional): Widget padre.
        """
        super().__init__(parent)
        self.setWindowTitle("Generador de Reportes")
        self.setFixedSize(700, 600)

        # 1. Instanciar los Modelos para acceso a datos
        self.model_curso = CursoModel()
        self.model_matricula = MatriculaModel()
        self.model_evaluacion = EvaluacionCursoModel()

        # Layout Principal
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # --- SECCIÓN 1: TIPO DE REPORTE ---
        gb_tipo = QGroupBox("1. Seleccione el Tipo de Reporte")
        gb_layout = QVBoxLayout()

        self.rb_general = QRadioButton("Reporte General (Estadísticas por Institución)")
        self.rb_general.setChecked(True)
        self.rb_detallado = QRadioButton("Reporte Detallado (Calificaciones por Estudiante)")

        gb_layout.addWidget(self.rb_general)
        gb_layout.addWidget(self.rb_detallado)
        gb_tipo.setLayout(gb_layout)
        layout.addWidget(gb_tipo)

        # --- SECCIÓN 2: SELECCIÓN DE CURSOS ---
        gb_cursos = QGroupBox("2. Seleccione los Cursos")
        cursos_layout = QVBoxLayout()

        # Buscador
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("Buscar curso por nombre...")
        self.input_buscar.textChanged.connect(self.filtrar_cursos)
        cursos_layout.addWidget(self.input_buscar)

        # Lista con Checkboxes
        self.lista_cursos = QListWidget()
        cursos_layout.addWidget(self.lista_cursos)

        # Botones de selección
        btn_sel_layout = QHBoxLayout()
        self.btn_todas = QPushButton("Seleccionar Todos")
        self.btn_todas.clicked.connect(self.seleccionar_todos)
        self.btn_ninguna = QPushButton("Deseleccionar Todos")
        self.btn_ninguna.clicked.connect(self.deseleccionar_todos)

        btn_sel_layout.addWidget(self.btn_todas)
        btn_sel_layout.addWidget(self.btn_ninguna)
        btn_sel_layout.addStretch()
        cursos_layout.addLayout(btn_sel_layout)

        gb_cursos.setLayout(cursos_layout)
        layout.addWidget(gb_cursos)

        # --- SECCIÓN 3: ACCIONES ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        btn_layout = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cerrar")
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_exportar = QPushButton("Exportar a CSV")
        self.btn_exportar.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 8px;")
        self.btn_exportar.clicked.connect(self.generar_reporte)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancelar)
        btn_layout.addWidget(self.btn_exportar)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Cargar datos iniciales
        self.cargar_cursos()

    def cargar_cursos(self):
        """Carga los cursos usando el modelo."""
        self.lista_cursos.clear()
        # Usamos search del modelo. Text() es necesario para el order_by complejo.
        cursos = self.model_curso.search(order_by=text("fecha_inicio desc"), limit=None) or []

        for curso in cursos:
            item = QListWidgetItem(f"{curso.nombre} (Fin: {curso.fecha_final})")
            item.setData(Qt.ItemDataRole.UserRole, curso.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.lista_cursos.addItem(item)

    def filtrar_cursos(self, texto):
        """Filtra visualmente la lista de cursos."""
        texto = texto.lower()
        for i in range(self.lista_cursos.count()):
            item = self.lista_cursos.item(i)
            item.setHidden(texto not in item.text().lower())

    def seleccionar_todos(self):
        """Marca todos los cursos visibles."""
        for i in range(self.lista_cursos.count()):
            item = self.lista_cursos.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked)

    def deseleccionar_todos(self):
        """Desmarca todos los cursos."""
        for i in range(self.lista_cursos.count()):
            self.lista_cursos.item(i).setCheckState(Qt.CheckState.Unchecked)

    def get_cursos_seleccionados(self):
        """Retorna los IDs de los cursos seleccionados."""
        ids = []
        for i in range(self.lista_cursos.count()):
            item = self.lista_cursos.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    def generar_reporte(self):
        """
        Orquesta la generación del reporte. Solicita ruta de archivo y llama
        al método específico según el tipo seleccionado.
        """
        ids_cursos = self.get_cursos_seleccionados()
        if not ids_cursos:
            QMessageBox.warning(self, "Aviso", "Seleccione al menos un curso.")
            return

        nombre_default = "Reporte_Instituciones.csv" if self.rb_general.isChecked() else "Reporte_Notas_Detallado.csv"
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar Reporte", nombre_default, "CSV Files (*.csv)")

        if not ruta:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        QApplication.processEvents()

        try:
            if self.rb_general.isChecked():
                self._generar_reporte_general(ids_cursos, ruta)
            else:
                self._generar_reporte_detallado(ids_cursos, ruta)

            self.progress_bar.setVisible(False)
            QMessageBox.information(self, "Éxito", f"Reporte guardado exitosamente en:\n{ruta}")
            self.accept()

        except Exception as e:
            self.progress_bar.setVisible(False)
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Error al generar reporte:\n{str(e)}")

    def _generar_reporte_general(self, ids_cursos, ruta):
        """
        Genera el reporte general agrupado por Institución Articulada.

        Reporte General: Desglosado por Institución Articulada para cada curso.
        Formato:
        CURSO | FECHA | INSTITUCIÓN | TOTAL | APROBADOS | REPROBADOS | NO REALIZÓ
        """
        try:
            with open(ruta, mode='w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file, delimiter=';')

                # Cabeceras
                writer.writerow([
                    "CURSO", "FECHA FIN", "INSTITUCIÓN",
                    "TOTAL INSCRITOS", "APROBADOS", "REPROBADOS", "NO REALIZÓ", "EN CURSO"
                ])

                for curso_id in ids_cursos:
                    # 1. Obtener curso
                    curso = self.model_curso.get_by_id(curso_id)
                    if not curso: continue

                    # 2. Obtener matriculas (Model ya carga relaciones)
                    matriculas = self.model_matricula.search(filters={'curso_id': curso_id}) or []

                    # 3. Agrupar datos por institución
                    # Estructura: { "POLICIA": {"total": 10, "aprobados": 8...}, "BOMBEROS": {...} }
                    stats_por_inst = {}

                    # Acumulador para el total del curso
                    total_curso = {
                        "total": 0, "aprobados": 0, "reprobados": 0, "no_realizo": 0, "en_curso": 0
                    }

                    for mat in matriculas:
                        # Determinar Institución (Limpieza de datos)
                        inst = "PARTICULAR"
                        if mat.persona and mat.persona.institucion_articulada:
                            inst_limpia = mat.persona.institucion_articulada.strip().upper()
                            if inst_limpia:
                                inst = inst_limpia

                        # Inicializar contadores para esta institución si es nueva
                        if inst not in stats_por_inst:
                            stats_por_inst[inst] = {
                                "total": 0, "aprobados": 0, "reprobados": 0, "no_realizo": 0, "en_curso": 0
                            }

                        # Determinar estado
                        estado = mat.estado.upper() if mat.estado else "EN CURSO"

                        # Actualizar contadores de la INSTITUCIÓN
                        stats_por_inst[inst]["total"] += 1
                        if estado == "APROBADO":
                            stats_por_inst[inst]["aprobados"] += 1
                        elif estado == "REPROBADO":
                            stats_por_inst[inst]["reprobados"] += 1
                        elif estado == "NO REALIZO":
                            stats_por_inst[inst]["no_realizo"] += 1
                        else:
                            stats_por_inst[inst]["en_curso"] += 1

                        # Actualizar contadores del TOTAL CURSO
                        total_curso["total"] += 1
                        if estado == "APROBADO":
                            total_curso["aprobados"] += 1
                        elif estado == "REPROBADO":
                            total_curso["reprobados"] += 1
                        elif estado == "NO REALIZO":
                            total_curso["no_realizo"] += 1
                        else:
                            total_curso["en_curso"] += 1

                    # 4. Escribir filas al CSV

                    # A. Filas por Institución (Orden Alfabético)
                    for nombre_inst in sorted(stats_por_inst.keys()):
                        datos = stats_por_inst[nombre_inst]
                        writer.writerow([
                            curso.nombre,
                            str(curso.fecha_final),
                            nombre_inst,
                            datos["total"],
                            datos["aprobados"],
                            datos["reprobados"],
                            datos["no_realizo"],
                            datos["en_curso"]
                        ])

                    # B. Fila de Resumen del Curso
                    writer.writerow([
                        curso.nombre,
                        str(curso.fecha_final),
                        "--- TOTAL DEL CURSO ---",
                        total_curso["total"],
                        total_curso["aprobados"],
                        total_curso["reprobados"],
                        total_curso["no_realizo"],
                        total_curso["en_curso"]
                    ])

                    # Fila vacía para separar cursos visualmente
                    writer.writerow([])

        except Exception as e:
            raise e

    def _generar_reporte_detallado(self, ids_cursos, ruta):
        """
        Genera el reporte detallado con notas por cada actividad.

        Reporte Detallado: Lista de estudiantes con sus notas desglosadas.
        """
        try:
            with open(ruta, mode='w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file, delimiter=';')

                headers = ["CURSO", "CÉDULA", "ESTUDIANTE", "INSTITUCIÓN", "ESTADO", "NOTA FINAL"]

                columnas_dinamicas = []
                es_curso_unico = len(ids_cursos) == 1

                # Configurar cabeceras dinámicas si es un solo curso
                if es_curso_unico:
                    evals = self.model_evaluacion.get_by_curso(ids_cursos[0]) or []
                    for ev in evals:
                        headers.append(f"{ev.nombre} ({ev.porcentaje}%)")
                        columnas_dinamicas.append(ev.id)
                else:
                    headers.append("DETALLE CALIFICACIONES")

                writer.writerow(headers)

                for curso_id in ids_cursos:
                    curso = self.model_curso.get_by_id(curso_id)
                    if not curso: continue

                    evaluaciones_curso = self.model_evaluacion.get_by_curso(curso_id) or []
                    matriculas = self.model_matricula.search(filters={'curso_id': curso_id}) or []

                    for mat in matriculas:
                        persona = mat.persona
                        institucion = "PARTICULAR"
                        if persona and persona.institucion_articulada:
                            institucion = persona.institucion_articulada

                        nombre_est = persona.nombre if persona else "DESCONOCIDO"
                        cedula_est = persona.cedula if persona else "SN"

                        row = [
                            curso.nombre,
                            cedula_est,
                            nombre_est,
                            institucion,
                            mat.estado,
                            str(mat.nota_final or 0.0).replace('.', ',')
                        ]

                        califs_est = {c.evaluacion_curso_id: c.puntaje for c in mat.calificaciones}

                        if es_curso_unico:
                            for ev_id in columnas_dinamicas:
                                puntaje = califs_est.get(ev_id, 0.0)
                                row.append(str(puntaje).replace('.', ','))
                        else:
                            detalles = []
                            for ev in evaluaciones_curso:
                                puntaje = califs_est.get(ev.id, 0.0)
                                detalles.append(f"{ev.nombre}: {puntaje}")
                            row.append(" | ".join(detalles))

                        writer.writerow(row)
        except Exception as e:
            raise e