#  Copyright (c) 2026 Fleer
import os
import shutil
import tempfile
import traceback
import sys
from PyQt6.QtCore import QDate, Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QComboBox, QLabel, QLineEdit, QPushButton,
    QHBoxLayout, QListWidget, QListWidgetItem, QCheckBox, QProgressBar,
    QMessageBox, QApplication, QFileDialog, QAbstractItemView
)
from sqlalchemy.orm import joinedload

from .base import DialogoBase
from utilities.sanitizer import Sanitizer
from database import config

from database.conexion import SessionLocal
from database.models import Certificado, Persona, Centro, Matricula

from models.matricula_model import MatriculaModel
from models.curso_model import CursoModel
from models.certificado_model import CertificadoModel
from models.centro_model import CentroModel
from models.tipos_cert_model import TipoCertificadoModel
from models.plantilla_certificado_model import PlantillaCertificadoModel
from services.word_generator import GeneradorCertificadosWord


# --- CLASE AUXILIAR PARA CORREGIR ERROR EN PYINSTALLER ---
class NullWriter:
    def write(self, text): pass

    def flush(self): pass


class DialogoGenerarCertificados(DialogoBase):
    """
    Diálogo principal. Contiene la lógica centralizada de generación (_nucleo_generar_pdf_y_bd)
    y la interfaz para generación masiva.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.curso_id = None
        self.curso_obj = None
        self.setWindowTitle("Generar Certificados")
        self.setFixedSize(950, 600)
        self._cache_matriculas = []

        try:
            self.curso_model = CursoModel()
            self.matricula_model = MatriculaModel()
            self.tipo_cert_model = TipoCertificadoModel()
            self.certificado_model = CertificadoModel()
            self.centro_model = CentroModel()
            self.plantilla_model = PlantillaCertificadoModel()
            self.ruta_destino_usuario = ""

            self.init_ui()
            self.cargar_datos_iniciales()
        except Exception as e:
            self.mostrar_error(f"Error inicializando: {e}")

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        content_layout = QHBoxLayout()

        # --- PANEL IZQUIERDO ---
        left_layout = QVBoxLayout()

        group_curso = QGroupBox("1. Selección de Curso")
        l_curso = QVBoxLayout(group_curso)
        self.combo_curso = QComboBox()
        self.combo_curso.currentIndexChanged.connect(self.on_curso_changed)
        l_curso.addWidget(QLabel("Curso:"))
        l_curso.addWidget(self.combo_curso)
        left_layout.addWidget(group_curso)

        group_conf = QGroupBox("2. Configuración")
        l_conf = QVBoxLayout(group_conf)
        l_conf.addWidget(QLabel("Plantilla:"))
        self.combo_plantilla = QComboBox()
        l_conf.addWidget(self.combo_plantilla)
        l_conf.addWidget(QLabel("Tipo Certificado:"))
        self.combo_tipo = QComboBox()
        self.combo_tipo.currentIndexChanged.connect(self.on_tipo_changed)
        l_conf.addWidget(self.combo_tipo)

        l_ruta = QHBoxLayout()
        self.input_ruta = QLineEdit()
        self.input_ruta.setReadOnly(True)
        btn_ruta = QPushButton("Examinar...")
        btn_ruta.clicked.connect(self.seleccionar_ruta)
        l_ruta.addWidget(self.input_ruta)
        l_ruta.addWidget(btn_ruta)
        l_conf.addWidget(QLabel("Guardar en:"))
        l_conf.addLayout(l_ruta)
        left_layout.addWidget(group_conf)
        left_layout.addStretch()

        # --- PANEL DERECHO ---
        right_layout = QVBoxLayout()
        self.group_seleccion = QGroupBox("3. Destinatarios")
        self.group_seleccion.setStyleSheet("QGroupBox { font-weight: bold; }")
        l_sel = QVBoxLayout(self.group_seleccion)
        self.lbl_info = QLabel("Seleccione curso.")
        l_sel.addWidget(self.lbl_info)
        self.lista_estudiantes = QListWidget()
        self.lista_estudiantes.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.lista_estudiantes.setAlternatingRowColors(True)
        l_sel.addWidget(self.lista_estudiantes)
        self.chk_todos = QCheckBox("Seleccionar Todos")
        self.chk_todos.clicked.connect(self.toggle_todos)
        l_sel.addWidget(self.chk_todos)
        right_layout.addWidget(self.group_seleccion)

        content_layout.addLayout(left_layout, 4)
        content_layout.addLayout(right_layout, 6)
        main_layout.addLayout(content_layout)

        # BARRA PROGRESO
        self.lbl_advertencia = QLabel("")
        self.lbl_advertencia.setStyleSheet("font-weight: bold; color: #c0392b; font-size: 14px;")
        self.lbl_advertencia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.lbl_advertencia)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { border: 1px solid #bdc3c7; border-radius: 5px; text-align: center; }
            QProgressBar::chunk { background-color: #27ae60; width: 10px; }
        """)
        main_layout.addWidget(self.progress)

        # BOTONES
        btn_layout = QHBoxLayout()
        self.btn_preview = QPushButton("Vista Previa")
        self.btn_preview.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold;")
        self.btn_preview.clicked.connect(self.generar_vista_previa)

        self.btn_cerrar = QPushButton("Cerrar")
        self.btn_cerrar.clicked.connect(self.reject)

        self.btn_generar = QPushButton("Generar Certificados")
        self.btn_generar.setMinimumHeight(40)
        self.btn_generar.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; font-size: 14px;")
        self.btn_generar.clicked.connect(self.generar_certificados)

        btn_layout.addWidget(self.btn_preview)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cerrar)
        btn_layout.addWidget(self.btn_generar)
        main_layout.addLayout(btn_layout)

    def cargar_datos_iniciales(self):
        for t in self.tipo_cert_model.get_all():
            self.combo_tipo.addItem(t.nombre, t.id)

        self.combo_plantilla.clear()
        found = False
        for p in self.plantilla_model.get_all():
            if p.configuracion_json == "TYPE_WORD":
                self.combo_plantilla.addItem(f"[WORD] {p.nombre}", p.id)
                found = True

        if not found:
            self.combo_plantilla.addItem("⚠️ NO HAY PLANTILLAS", None)
            self.btn_generar.setEnabled(False)
            self.btn_preview.setEnabled(False)
        else:
            self.btn_generar.setEnabled(True)
            self.btn_preview.setEnabled(True)

        self.combo_curso.addItem("-- Seleccione --", None)
        for c in self.curso_model.search(order_by="nombre"):
            self.combo_curso.addItem(c.nombre, c.id)

    def on_curso_changed(self):
        cursor_set = False
        try:
            self.curso_id = self.combo_curso.currentData()
            self._cache_matriculas = []
            self.lista_estudiantes.clear()

            if not self.curso_id:
                self.curso_obj = None
                self.lbl_info.setText("Seleccione un curso.")
                return

            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            cursor_set = True

            self.curso_obj = self.curso_model.get_by_id(self.curso_id)
            self._cache_matriculas = self.matricula_model.search(filters={"curso_id": self.curso_id})
            self.on_tipo_changed()
        except Exception as e:
            self.mostrar_error(f"Error al cargar curso: {e}")
        finally:
            if cursor_set: QApplication.restoreOverrideCursor()

    def on_tipo_changed(self):
        if not self.curso_id:
            self.lbl_info.setText("Sin datos.")
            return

        tipo = self.combo_tipo.currentText().upper()
        self.lista_estudiantes.clear()

        filtrados = []
        auto_check = False

        if "APROBA" in tipo:
            filtrados = [m for m in self._cache_matriculas if m.estado == "APROBADO"]
        elif "PARTICIPA" in tipo or "ASISTEN" in tipo:
            filtrados = [m for m in self._cache_matriculas if m.estado != "NO REALIZO"]
        else:
            filtrados = self._cache_matriculas
            auto_check = True

        self.lista_estudiantes.blockSignals(True)
        for m in filtrados:
            if m.persona:
                txt = f"{m.persona.nombre} ({m.persona.cedula}) - {m.estado}"
                item = QListWidgetItem(txt)
                item.setData(Qt.ItemDataRole.UserRole, m)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked if auto_check else Qt.CheckState.Checked)
                self.lista_estudiantes.addItem(item)

        self.lista_estudiantes.blockSignals(False)
        self.lbl_info.setText(f"Mostrando: {len(filtrados)} estudiantes.")
        self.chk_todos.setVisible(True)
        self.chk_todos.setChecked(not auto_check)

    def toggle_todos(self):
        st = Qt.CheckState.Checked if self.chk_todos.isChecked() else Qt.CheckState.Unchecked
        for i in range(self.lista_estudiantes.count()):
            self.lista_estudiantes.item(i).setCheckState(st)

    def seleccionar_ruta(self):
        d = QFileDialog.getExistingDirectory(self, "Carpeta Destino")
        if d:
            self.ruta_destino_usuario = d
            self.input_ruta.setText(d)

    def _get_items_marcados(self):
        items = []
        for i in range(self.lista_estudiantes.count()):
            item = self.lista_estudiantes.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                items.append(item)
        return items

    # --- HELPERS FECHA/TEXTO ---
    @staticmethod
    def _formatear_fecha_larga(fecha):
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
                 "noviembre", "diciembre"]
        y, m, d = 0, 0, 0
        if isinstance(fecha, QDate):
            d, m, y = fecha.day(), fecha.month(), fecha.year()
        elif hasattr(fecha, 'year'):
            d, m, y = fecha.day, fecha.month, fecha.year
        else:
            return str(fecha)
        return f"{d:02d} de {meses[m - 1]} de {y}"

    @staticmethod
    def _formatear_fecha_mes_anio(fecha):
        meses = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE",
                 "NOVIEMBRE", "DICIEMBRE"]
        y, m = 0, 0
        if isinstance(fecha, QDate):
            y, m = fecha.year(), fecha.month()
        elif hasattr(fecha, 'year'):
            y, m = fecha.year, fecha.month
        else:
            return str(fecha)
        return f"{meses[m - 1]} DE {y}"

    def _generar_siglas_curso(self, nombre_curso):
        ignore = {'DE', 'DEL', 'LA', 'EL', 'EN', 'Y', 'PARA', 'CON', 'LOS', 'LAS', 'POR', 'TALLER', 'CURSO'}
        clean_name = Sanitizer.limpiar_texto(nombre_curso).upper()
        words = [w for w in clean_name.split() if w not in ignore]
        if not words: return "CUR"
        if len(words) >= 3:
            return "".join(w[0] for w in words[:3])
        elif len(words) == 2:
            return (words[0][:1] + words[1][:2])
        else:
            w = words[0]
            return w[:3] if len(w) >= 3 else w.ljust(3, 'X')

    def _obtener_sufijo_tipo(self, texto_tipo):
        txt = texto_tipo.upper()
        if "APROBA" in txt: return "A"
        if "PARTICIPA" in txt: return "P"
        if "RECONOCI" in txt: return "R"
        if "VINCULA" in txt: return "V"
        return "C"

    def _cargar_mapa_centros(self):
        session = SessionLocal()
        try:
            return {c.id: c.siglas for c in session.query(Centro).all()}
        finally:
            session.close()

    def _get_conteo_inicial_centro(self, centro_id):
        session = SessionLocal()
        try:
            return session.query(Certificado).join(Persona).filter(Persona.centro_id == centro_id).count()
        finally:
            session.close()

    # --- NÚCLEO CENTRALIZADO DE GENERACIÓN ---
    @staticmethod
    def _nucleo_generar_pdf_y_bd(session, matricula, plantilla_path, output_pdf_path,
                                 tipo_cert_id, datos_base, es_regeneracion=False, contadores_centros=None,
                                 mapa_centros=None):
        """
        Función ÚNICA que contiene la lógica de negocio para crear el PDF y actualizar la BD.
        Maneja la generación, actualización de fechas y limpieza de archivos firmados si aplica.
        """
        per = matricula.persona
        curso = matricula.curso
        centro_id = matricula.centro_id or per.centro_id

        # 1. Verificar existencia de certificado previo
        cert_existente = session.query(Certificado).filter(
            Certificado.persona_id == per.id,
            Certificado.curso_id == curso.id,
            Certificado.tipo_certificado_id == tipo_cert_id
        ).first()

        codigo = "GEN-MANUAL-0000"

        # 2. Generación o recuperación de código
        if cert_existente:
            codigo = cert_existente.codigo_validacion.strip()
        elif not es_regeneracion and centro_id and contadores_centros is not None and mapa_centros is not None:
            # Lógica secuencial para NUEVOS certificados masivos
            if centro_id not in contadores_centros:
                c = session.query(Certificado).join(Persona).filter(Persona.centro_id == centro_id).count()
                contadores_centros[centro_id] = c

            contadores_centros[centro_id] += 1
            seq = contadores_centros[centro_id]
            siglas_cen = str(mapa_centros.get(centro_id, "UNK")).strip().upper()

            # Generar siglas curso
            clean_cur = Sanitizer.limpiar_texto(curso.nombre).upper()
            ignore = {'DE', 'DEL', 'LA', 'EL', 'EN', 'Y', 'PARA', 'CON', 'LOS', 'LAS', 'POR', 'TALLER', 'CURSO'}
            words = [w for w in clean_cur.split() if w not in ignore]

            if not words:
                siglas_cur = "CUR"
            elif len(words) >= 3:
                siglas_cur = "".join(w[0] for w in words[:3])
            elif len(words) == 2:
                siglas_cur = (words[0][:1] + words[1][:2])
            else:
                w = words[0]; siglas_cur = w[:3] if len(w) >= 3 else w.ljust(3, 'X')

            sufijo = datos_base.get("sufijo_tipo", "C")

            codigo = f"{siglas_cen}-DNAE-{siglas_cur}-{seq:04d}-{sufijo}".strip()

        # 3. Preparar Datos para Word
        datos_merge = datos_base.copy()
        datos_merge.update({
            "nombre_estudiante": per.nombre,
            "cedula_estudiante": per.cedula,
            "nota_final": str(matricula.nota_final),
            "codigo_validacion": codigo
        })

        # 4. Generar PDF Físico
        if not GeneradorCertificadosWord.generar(plantilla_path, datos_merge, output_pdf_path):
            raise Exception("Fallo en librería docx2pdf")

        # 5. Actualizar Base de Datos y Limpiar
        if cert_existente:
            cert_existente.fecha_emision = QDate.currentDate().toPyDate()

            # CRÍTICO: Si estamos regenerando, debemos borrar cualquier firmado anterior
            if es_regeneracion and matricula.ruta_pdf_firmado:
                try:
                    p = os.path.abspath(
                        os.path.join(config.SHARED_FOLDER_PATH, os.path.basename(matricula.ruta_pdf_firmado)))
                    if os.path.exists(p):
                        os.remove(p)
                except:
                    pass  # Si falla el borrado físico, seguimos

                # Desvincular en BD
                matricula.ruta_pdf_firmado = None
        else:
            # Crear nuevo registro (masivo o primera vez)
            nuevo_cert = Certificado(
                persona_id=per.id,
                curso_id=curso.id,
                tipo_certificado_id=tipo_cert_id,
                fecha_emision=QDate.currentDate().toPyDate(),
                codigo_validacion=codigo
            )
            session.add(nuevo_cert)

        return True

    # --- MÉTODOS PÚBLICOS DE EJECUCIÓN ---

    def generar_certificados(self):
        """ Ejecuta el bucle masivo utilizando la configuración de la UI. """
        # Fix PyInstaller console
        if sys.stderr is None: sys.stderr = NullWriter()
        if sys.stdout is None: sys.stdout = NullWriter()

        if not self.curso_id or not self.ruta_destino_usuario:
            self.mostrar_error("Faltan datos obligatorios (Curso o Ruta).")
            return

        items = self._get_items_marcados()
        if not items:
            self.mostrar_error("Seleccione al menos un estudiante.")
            return

        plantilla = self.plantilla_model.get_by_id(self.combo_plantilla.currentData())
        if not plantilla or not plantilla.archivo_binario:
            self.mostrar_error("La plantilla no contiene el archivo de Word en la base de datos.")
            return

        # Preparar entorno
        temp_dir = tempfile.mkdtemp()
        plantilla_path = os.path.join(temp_dir, "plantilla.docx")
        temp_pdf_dir = tempfile.mkdtemp()

        # Log para errores
        log_path = os.path.join(self.ruta_destino_usuario, "log_errores_certificados.txt")
        if os.path.exists(log_path):
            try:
                os.remove(log_path)
            except:
                pass

        session = SessionLocal()  # Sesión para el lote

        try:
            with open(plantilla_path, "wb") as f:
                f.write(plantilla.archivo_binario)

            # Datos estáticos del curso
            f_ini = self._formatear_fecha_larga(self.curso_obj.fecha_inicio)
            f_fin = self._formatear_fecha_larga(self.curso_obj.fecha_final)
            f_emi = self._formatear_fecha_mes_anio(QDate.currentDate())
            sufijo_tipo = self._obtener_sufijo_tipo(self.combo_tipo.currentText())

            datos_base = {
                "curso_nombre": self.curso_obj.nombre,
                "horas_curso": str(self.curso_obj.duracion_horas),
                "fecha_inicio": f_ini,
                "fecha_final": f_fin,
                "fecha_emision": f_emi,
                "sufijo_tipo": sufijo_tipo
            }

            # Mapas para secuenciales
            mapa_centros = self._cargar_mapa_centros()
            contadores_centros = {}

            # Configuración UI
            total_items = len(items)
            self.progress.setVisible(True)
            self.progress.setMaximum(total_items)
            self.progress.setValue(0)
            self.btn_generar.setEnabled(False)
            self.btn_cerrar.setEnabled(False)
            self.lbl_advertencia.setText("Iniciando generación...")
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            gen = 0
            err = 0
            actualizados = 0
            ultimo_error_msg = ""

            for i, item in enumerate(items):
                try:
                    # Usamos la sesión local para traer el objeto matricula 'vivo'
                    mat_data = item.data(Qt.ItemDataRole.UserRole)
                    mat = session.query(Matricula).get(mat_data.id)

                    nombre_clean = Sanitizer.limpiar_texto(mat.persona.nombre)
                    # El nombre del archivo temporal se define aquí, el código final se calcula dentro del núcleo pero
                    # para el archivo temporal necesitamos un nombre preliminar o calculamos el código antes si quisiéramos.
                    # El núcleo calcula el código, pero necesitamos pasar el path.
                    # Truco: Usamos un nombre genérico con cédula y el núcleo genera el archivo.
                    # Para simplificar y no duplicar lógica de código, podemos generar el archivo con cédula y luego renombrarlo
                    # o aceptar que el archivo en disco no tenga el código en el nombre si es masivo.
                    # OJO: La lógica original construía el nombre del archivo CON el código.
                    # Para mantener compatibilidad exacta, moveremos la lógica de código FUERA del núcleo para masivo?
                    # No, mejor dejar que el nucleo lo maneje pero pasarle un path temporal y luego moverlo.

                    # Para masivo, el nombre de archivo es importante.
                    # Requerimos el código ANTES para el nombre del archivo.
                    # Ajuste: Haremos que el nucleo use un path temporal y nos devuelva el codigo generado,
                    # pero el método retorna bool.
                    # Simplificación: Usaremos nombre con Cédula y Nombre. El código va DENTRO del PDF.

                    filename = f"{mat.persona.cedula}_{nombre_clean}.pdf"
                    ruta_temp_pdf = os.path.join(temp_pdf_dir, filename)
                    ruta_usu = os.path.join(self.ruta_destino_usuario, filename)

                    # LLAMADA AL NÚCLEO
                    self._nucleo_generar_pdf_y_bd(
                        session=session, matricula=mat, plantilla_path=plantilla_path,
                        output_pdf_path=ruta_temp_pdf, tipo_cert_id=self.combo_tipo.currentData(),
                        datos_base=datos_base, es_regeneracion=False,
                        contadores_centros=contadores_centros, mapa_centros=mapa_centros
                    )

                    # Mover archivo
                    if os.path.exists(ruta_temp_pdf):
                        shutil.copyfile(ruta_temp_pdf, ruta_usu)
                        os.remove(ruta_temp_pdf)
                        gen += 1

                    # Commit parcial
                    if i % 10 == 0: session.commit()

                except Exception as e:
                    err += 1
                    ultimo_error_msg = str(e)
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"\n[ERROR] Fila {i}: {e}\n{traceback.format_exc()}\n")

                    # Rollback parcial de contadores si es necesario
                    centro_id = mat.centro_id or mat.persona.centro_id
                    if centro_id in contadores_centros:
                        contadores_centros[centro_id] -= 1

                avance = i + 1
                if avance % 5 == 0 or avance == total_items:
                    porcentaje = int((avance / total_items) * 100)
                    self.progress.setValue(avance)
                    self.lbl_advertencia.setText(f"Procesando {avance}/{total_items} ({porcentaje}%)...")
                    QApplication.processEvents()

            session.commit()

            QApplication.restoreOverrideCursor()
            self.lbl_advertencia.setText("Proceso completado.")
            self.progress.setVisible(False)
            self.btn_generar.setEnabled(True)
            self.btn_cerrar.setEnabled(True)

            msg = f"Proceso terminado.\n\nGenerados: {gen}\nErrores: {err}"
            if err > 0:
                msg += f"\n\nÚltimo error detectado:\n{ultimo_error_msg}\n\n(Revise 'log_errores_certificados.txt')"

            QMessageBox.information(self, "Fin", msg)
            self.accept()

        except Exception as e:
            session.rollback()
            QApplication.restoreOverrideCursor()
            self.mostrar_error(f"Error crítico: {e}")
        finally:
            session.close()
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
            if os.path.exists(temp_pdf_dir): shutil.rmtree(temp_pdf_dir)

    @staticmethod
    def regenerar_unitario_silencioso(parent, matricula_id):
        """
        Punto de entrada para regeneración individual desde el Controlador.
        Prepara los datos, pide ruta y llama a _nucleo_generar_pdf_y_bd.
        """
        if sys.stderr is None: sys.stderr = NullWriter()
        if sys.stdout is None: sys.stdout = NullWriter()

        ruta_usu = QFileDialog.getExistingDirectory(parent, "Seleccione carpeta para guardar el PDF")
        if not ruta_usu: return False

        session = SessionLocal()
        temp_dir = tempfile.mkdtemp()

        try:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

            # Carga Eager de la matrícula para asegurar relaciones
            mat = session.query(Matricula).options(
                joinedload(Matricula.persona),
                joinedload(Matricula.curso),
                joinedload(Matricula.centro)
            ).get(matricula_id)

            if not mat: raise Exception("Matrícula no encontrada")

            # Buscar plantilla Word válida
            pm = PlantillaCertificadoModel()
            plantilla = next((p for p in pm.get_all() if p.configuracion_json == "TYPE_WORD" and p.archivo_binario),
                             None)
            if not plantilla: raise Exception("No hay plantilla Word configurada en el sistema.")

            plantilla_path = os.path.join(temp_dir, "temp.docx")
            with open(plantilla_path, "wb") as f:
                f.write(plantilla.archivo_binario)

            # Buscar el tipo de certificado del registro existente para usar el mismo ID
            cert_previo = session.query(Certificado).filter(
                Certificado.persona_id == mat.persona_id, Certificado.curso_id == mat.curso_id
            ).first()

            tipo_id = cert_previo.tipo_certificado_id if cert_previo else 1  # Fallback

            # Datos base
            f_ini = DialogoGenerarCertificados._formatear_fecha_larga(mat.curso.fecha_inicio)
            f_fin = DialogoGenerarCertificados._formatear_fecha_larga(mat.curso.fecha_final)
            f_emi = DialogoGenerarCertificados._formatear_fecha_mes_anio(QDate.currentDate())

            datos_base = {
                "curso_nombre": mat.curso.nombre,
                "horas_curso": str(mat.curso.duracion_horas),
                "fecha_inicio": f_ini,
                "fecha_final": f_fin,
                "fecha_emision": f_emi,
                "sufijo_tipo": "R"  # Indicador interno, aunque el nucleo usa el código existente
            }

            # Nombre de archivo REGENERADO
            nombre_clean = Sanitizer.limpiar_texto(mat.persona.nombre)
            codigo_txt = cert_previo.codigo_validacion.strip() if cert_previo else "REGEN"
            nombre_file = f"{mat.persona.cedula}_{nombre_clean}_{codigo_txt}.pdf"
            ruta_salida = os.path.join(ruta_usu, nombre_file)

            # LLAMADA AL NÚCLEO con flag es_regeneracion=True
            DialogoGenerarCertificados._nucleo_generar_pdf_y_bd(
                session=session, matricula=mat, plantilla_path=plantilla_path,
                output_pdf_path=ruta_salida, tipo_cert_id=tipo_id,
                datos_base=datos_base, es_regeneracion=True
            )

            session.commit()
            QApplication.restoreOverrideCursor()
            QMessageBox.information(parent, "Éxito",
                                    f"Certificado regenerado en:\n{ruta_salida}\n\nNota: Se ha eliminado cualquier firma digital previa.")
            return True

        except Exception as e:
            session.rollback()
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(parent, "Error", str(e))
            return False
        finally:
            session.close()
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)

    def generar_vista_previa(self):
        """ Genera un certificado temporal sin afectar BD ni limpiar firmados. """
        if sys.stderr is None: sys.stderr = NullWriter()
        if sys.stdout is None: sys.stdout = NullWriter()

        if not self.curso_id:
            self.mostrar_error("Seleccione un curso primero.")
            return

        items = self._get_items_marcados()
        if not items:
            self.mostrar_error("Marque al menos un estudiante.")
            return

        item = items[0]
        plantilla_id = self.combo_plantilla.currentData()
        plantilla = self.plantilla_model.get_by_id(plantilla_id) if plantilla_id else None

        if not plantilla or not plantilla.archivo_binario:
            self.mostrar_error("Plantilla inválida.")
            return

        temp_dir = tempfile.mkdtemp()
        ruta_tpl_temp = os.path.join(temp_dir, "plantilla_temp.docx")

        try:
            with open(ruta_tpl_temp, "wb") as f:
                f.write(plantilla.archivo_binario)

            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            mat = item.data(Qt.ItemDataRole.UserRole)
            per = mat.persona

            f_ini = self._formatear_fecha_larga(self.curso_obj.fecha_inicio)
            f_fin = self._formatear_fecha_larga(self.curso_obj.fecha_final)
            f_emi = self._formatear_fecha_mes_anio(QDate.currentDate())

            datos = {
                "nombre_estudiante": per.nombre,
                "cedula_estudiante": per.cedula,
                "curso_nombre": self.curso_obj.nombre,
                "horas_curso": str(self.curso_obj.duracion_horas),
                "fecha_inicio": f_ini,
                "fecha_final": f_fin,
                "nota_final": str(mat.nota_final),
                "codigo_validacion": "VISTA-PREVIA-0000",
                "fecha_emision": f_emi
            }

            ruta_pdf = os.path.join(temp_dir, "preview.pdf")
            exito = GeneradorCertificadosWord.generar(ruta_tpl_temp, datos, ruta_pdf)

            QApplication.restoreOverrideCursor()

            if exito:
                QDesktopServices.openUrl(QUrl.fromLocalFile(ruta_pdf))
            else:
                self.mostrar_error("Falló la generación del documento.")

        except Exception as e:
            QApplication.restoreOverrideCursor()
            self.mostrar_error(f"Error en vista previa: {e}")
        finally:
            pass  # No borramos temp_dir inmediatamente para que el visor PDF pueda abrirlo