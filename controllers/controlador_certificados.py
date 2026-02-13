#  Copyright (c) 2026 Fleer
import os
import shutil
import uuid
import traceback
import tempfile
import re
from PyQt6 import uic
from PyQt6.QtWidgets import (
    QWidget, QMessageBox, QTableWidget, QLineEdit,
    QLabel, QPushButton, QComboBox, QFileDialog,
    QTableWidgetItem, QApplication, QDialog, QVBoxLayout,
    QListWidget, QListWidgetItem, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QUrl, QTimer, QDate
from PyQt6.QtGui import QDesktopServices, QIcon
from sqlalchemy import text
from sqlalchemy.orm import joinedload

# --- IMPORTACIONES DEL PROYECTO ---
from database import config
from database.conexion import SessionLocal
from database.models import Certificado, Matricula, Persona, Curso, Centro

from models.matricula_model import MatriculaModel
from models.persona_model import PersonaModel
from models.curso_model import CursoModel
from models.certificado_model import CertificadoModel
from models.plantilla_certificado_model import PlantillaCertificadoModel
from services.word_generator import GeneradorCertificadosWord

from utilities.delegado import BotonDetalleDelegate
from utilities.helper import PyQtHelper, actualizar_paginacion_ui
from utilities.dialogos import DialogoGenerarCertificados


class DialogoBuscador(QDialog):
    """ Diálogo auxiliar para buscar cursos en listas largas """

    def __init__(self, parent=None, titulo="Seleccionar", items=None):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.seleccionado_id = None
        self.seleccionado_texto = None

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Escriba para buscar:"))

        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("Buscar...")
        self.input_buscar.textChanged.connect(self.filtrar_lista)
        layout.addWidget(self.input_buscar)

        self.lista_widget = QListWidget()
        self.lista_widget.itemDoubleClicked.connect(self.validar_seleccion)
        layout.addWidget(self.lista_widget)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.validar_seleccion)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.setLayout(layout)
        self.items_originales = items or []
        self._cargar_items(self.items_originales)

    def _cargar_items(self, lista):
        self.lista_widget.clear()
        for t, i in lista:
            it = QListWidgetItem(t)
            it.setData(Qt.ItemDataRole.UserRole, i)
            self.lista_widget.addItem(it)

    def filtrar_lista(self, txt):
        for i in range(self.lista_widget.count()):
            it = self.lista_widget.item(i)
            it.setHidden(txt.lower() not in it.text().lower())

    def validar_seleccion(self):
        if self.lista_widget.currentItem():
            self.seleccionado_id = self.lista_widget.currentItem().data(Qt.ItemDataRole.UserRole)
            self.seleccionado_texto = self.lista_widget.currentItem().text()
            self.accept()
        else:
            QMessageBox.warning(self, "Aviso", "Seleccione un ítem.")


class ControladorCertificados(QWidget):
    """
    Controlador principal.
    Carga datos desde la tabla 'Certificado' y permite acciones de gestión.
    """

    def __init__(self):
        super().__init__()
        try:
            ruta_ui = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "views", "certificados.ui"))
            uic.loadUi(ruta_ui, self)
        except Exception as e:
            QMessageBox.critical(self, "Error UI", f"No se pudo cargar la interfaz: {e}")
            return

        self.model_matricula = MatriculaModel()
        self.model_curso = CursoModel()
        self.model_certificado = CertificadoModel()

        self.columnas_headers = [
            "", "", "", "",
            "Código", "Estudiante", "Curso / Asunto", "Fecha Emisión", "Estado"
        ]

        self.registros_por_pagina = 50
        self.pagina_actual = 1
        self.total_registros = 0
        self.total_paginas = 1

        self._init_delegados()
        self.setup_ui_elements()
        self.cargar_formato_tabla()
        self._cargar_cursos_en_combo()

        QTimer.singleShot(100, self.recargar_datos)

    def _init_delegados(self):
        self.delegado_descargar = BotonDetalleDelegate(self.accion_descargar_pdf, "assets/icons/pdf_download.png", 0,
                                                       self)
        self.delegado_regenerar = BotonDetalleDelegate(self.accion_regenerar, "assets/icons/refresh.png", 1, self)
        self.delegado_subir = BotonDetalleDelegate(self.accion_subir_firmado, "assets/icons/upload.png", 2, self)
        self.delegado_eliminar = BotonDetalleDelegate(self.accion_eliminar, "assets/icons/delete.png", 3, self)

    def setup_ui_elements(self):
        self.input_buscar = self.findChild(QLineEdit, 'input_buscar')
        self.combo_filtro = self.findChild(QComboBox, 'combo_filtro')
        if hasattr(self, 'btn_recargar'):
            self.btn_recargar.setIcon(QIcon("assets/icons/refresh.png"))

        if self.combo_filtro:
            self.combo_filtro.currentIndexChanged.connect(self.recargar_datos)

        if self.input_buscar: self.input_buscar.textChanged.connect(self.filtrar_tabla)

        btn_ids = ['btn_recargar', 'btn_subir_lote', 'btn_descargar_zip', 'btn_anterior', 'btn_siguiente']
        funcs = [self.recargar_datos, self.accion_subir_lote, self.accion_descargar_zip_curso, self.pagina_anterior,
                 self.pagina_siguiente]

        for bid, func in zip(btn_ids, funcs):
            btn = self.findChild(QPushButton, bid)
            if btn: btn.clicked.connect(func)

        self.lbl_paginacion = self.findChild(QLabel, 'lbl_paginacion')
        self.lbl_contador_sub = self.findChild(QLabel, 'lbl_contador_sub')
        self.lbl_num_firmar = self.findChild(QLabel, 'lbl_num_firmar')

    def cargar_formato_tabla(self):
        self.tabla = self.findChild(QTableWidget, 'tabla_certificados')
        if self.tabla:
            anchos = [35, 35, 35, 35, 100, 220, 220, 90, 100]
            PyQtHelper.configurar_tabla(self.tabla, self.columnas_headers, anchos, columnas_boton=[0, 1, 2, 3])
            self.tabla.setItemDelegateForColumn(0, self.delegado_descargar)
            self.tabla.setItemDelegateForColumn(1, self.delegado_regenerar)
            self.tabla.setItemDelegateForColumn(2, self.delegado_subir)
            self.tabla.setItemDelegateForColumn(3, self.delegado_eliminar)

    def _cargar_cursos_en_combo(self):
        try:
            if not self.combo_filtro: return
            self.combo_filtro.blockSignals(True)
            self.combo_filtro.clear()
            self.combo_filtro.addItem("Todos los Cursos", None)
            for c in self.model_curso.search(order_by=text("fecha_inicio desc")):
                self.combo_filtro.addItem(c.nombre, c.id)
            self.combo_filtro.blockSignals(False)
        except:
            pass

    # --- MÉTODO PRINCIPAL DE CARGA DE DATOS ---
    def cargar_datos_tabla(self):
        if not self.tabla: return
        self.tabla.setUpdatesEnabled(False)
        self.tabla.setRowCount(0)

        session = SessionLocal()
        try:
            texto = self.input_buscar.text().strip().lower() if self.input_buscar else ""
            curso_id = self.combo_filtro.currentData() if self.combo_filtro else None

            # 1. Consulta Base sobre CERTIFICADOS
            query = session.query(Certificado).options(
                joinedload(Certificado.persona),
                joinedload(Certificado.curso)
            )

            # 2. Filtros
            if curso_id:
                query = query.filter(Certificado.curso_id == curso_id)

            query = query.order_by(Certificado.fecha_emision.desc())
            todos = query.all()

            datos_procesados = []
            cont_faltan_firmar = 0

            # 3. Procesamiento en memoria para cruzar con matrícula
            for cert in todos:
                per = cert.persona
                cur = cert.curso

                # Buscar matrícula para ver si tiene archivo firmado subido
                mat = session.query(Matricula).filter(
                    Matricula.persona_id == per.id,
                    Matricula.curso_id == cur.id
                ).first()

                tiene_firma = False
                if mat and mat.ruta_pdf_firmado: tiene_firma = True

                if not tiene_firma: cont_faltan_firmar += 1

                # Filtro texto
                txts = [per.nombre, per.cedula, cert.codigo_validacion]
                if texto and not any(texto in (str(t).lower() if t else "") for t in txts):
                    continue

                f_emi = cert.fecha_emision.strftime("%d/%m/%Y") if cert.fecha_emision else "-"

                datos_procesados.append({
                    "mat_id": mat.id if mat else None,
                    "codigo": cert.codigo_validacion,
                    "estudiante": per.nombre,
                    "curso": cur.nombre,
                    "fecha": f_emi,
                    "estado": "FIRMADO" if tiene_firma else "GENERADO"
                })

            # 4. Paginación y Renderizado
            self.total_registros = len(datos_procesados)
            self.total_paginas = max(1, (
                        self.total_registros + self.registros_por_pagina - 1) // self.registros_por_pagina)
            if self.pagina_actual > self.total_paginas: self.pagina_actual = 1

            inicio = (self.pagina_actual - 1) * self.registros_por_pagina
            lote = datos_procesados[inicio: inicio + self.registros_por_pagina]

            filas = []
            ids_data = [item["mat_id"] for item in lote]

            for item in lote:
                filas.append(
                    ["", "", "", "", item["codigo"], item["estudiante"], item["curso"], item["fecha"], item["estado"]])

            PyQtHelper.cargar_datos_en_tabla(self.tabla, filas, alineacion=Qt.AlignmentFlag.AlignCenter)

            # Asignar ID Matricula a los botones
            for i, mat_id in enumerate(ids_data):
                for c in range(4):
                    it = self.tabla.item(i, c)
                    if not it:
                        it = QTableWidgetItem("")
                        self.tabla.setItem(i, c, it)
                    if mat_id: it.setData(Qt.ItemDataRole.UserRole, mat_id)

            if self.lbl_num_firmar:
                self.lbl_num_firmar.setText(f"{cont_faltan_firmar} pendientes")
                self.lbl_num_firmar.setStyleSheet("color: orange;" if cont_faltan_firmar > 0 else "color: green;")

            self.actualizar_interfaz_paginacion()

        except Exception as e:
            traceback.print_exc()
        finally:
            session.close()
            self.tabla.setUpdatesEnabled(True)

    # --- ACCIONES ---

    def recargar_datos(self):
        self.pagina_actual = 1
        self.cargar_datos_tabla()

    def filtrar_tabla(self):
        self.recargar_datos()

    def pagina_anterior(self):
        if self.pagina_actual > 1: self.pagina_actual -= 1; self.cargar_datos_tabla()

    def pagina_siguiente(self):
        if self.pagina_actual < self.total_paginas: self.pagina_actual += 1; self.cargar_datos_tabla()

    def accion_regenerar(self, matricula_id):
        if not matricula_id: return

        resp = QMessageBox.question(self, "Regenerar",
                                    "¿Regenerar certificado?\nSi ya existe un firmado, se ELIMINARÁ.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            if DialogoGenerarCertificados.regenerar_unitario_silencioso(self, matricula_id):
                self.recargar_datos()

    def accion_descargar_pdf(self, matricula_id):
        if not matricula_id: return
        try:
            session = SessionLocal()
            mat = session.query(Matricula).get(matricula_id)
            if not mat: return

            ruta = mat.ruta_pdf_firmado
            session.close()

            if not ruta:
                return QMessageBox.warning(self, "Aviso", "No hay PDF firmado asociado.")

            # MODIFICADO: No usar os.path.basename, respetar la estructura de carpetas guardada en DB
            # Esto permite que si la ruta es "Curso A/Centro B/file.pdf", se abra correctamente.
            path_abs = os.path.abspath(os.path.join(config.SHARED_FOLDER_PATH, ruta))

            if os.path.exists(path_abs):
                QDesktopServices.openUrl(QUrl.fromLocalFile(path_abs))
            else:
                QMessageBox.warning(self, "Error", f"Archivo no encontrado en:\n{path_abs}")
        except:
            traceback.print_exc()

    def accion_eliminar(self, matricula_id):
        if not matricula_id: return
        if QMessageBox.question(self, "Eliminar", "¿Borrar certificado?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.No:
            return

        try:
            session = SessionLocal()
            mat = session.query(Matricula).get(matricula_id)
            cert = session.query(Certificado).filter_by(persona_id=mat.persona_id, curso_id=mat.curso_id).first()

            if cert:
                # Borrar físico firmado si existe
                if mat.ruta_pdf_firmado:
                    # MODIFICADO: Respetar ruta relativa con carpetas
                    p = os.path.join(config.SHARED_FOLDER_PATH, mat.ruta_pdf_firmado)
                    if os.path.exists(p): os.remove(p)
                    mat.ruta_pdf_firmado = None

                session.delete(cert)
                session.commit()
                QMessageBox.information(self, "Éxito", "Eliminado.")
                self.recargar_datos()
            session.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def accion_subir_firmado(self, matricula_id):
        """ Sube un archivo individual, organizándolo en carpetas legibles. """
        if not matricula_id: return
        file, _ = QFileDialog.getOpenFileName(self, "PDF Firmado", "", "PDF (*.pdf)")
        if not file: return

        try:
            session = SessionLocal()
            # Cargar con relaciones para obtener nombres de carpetas
            mat = session.query(Matricula).options(
                joinedload(Matricula.curso),
                joinedload(Matricula.centro),
                joinedload(Matricula.persona)
            ).get(matricula_id)

            # 1. Preparar Nombres para Carpetas
            nombre_curso = self._limpiar_nombre(mat.curso.nombre) if mat.curso else "Curso_General"
            nombre_centro = self._limpiar_nombre(mat.centro.nombre) if mat.centro else "Sin_Centro"
            nombre_persona = self._limpiar_nombre(mat.persona.nombre)
            cedula = mat.persona.cedula

            # 2. Definir Estructura: SHARED / Curso / Centro / Cedula_Nombre.pdf
            carpeta_destino = os.path.join(config.SHARED_FOLDER_PATH, nombre_curso, nombre_centro)
            os.makedirs(carpeta_destino, exist_ok=True)

            nombre_archivo = f"{cedula}_{nombre_persona}.pdf"
            dest_path = os.path.join(carpeta_destino, nombre_archivo)

            # Ruta relativa para guardar en BD (compatible con Windows/Linux)
            ruta_relativa_db = os.path.join(nombre_curso, nombre_centro, nombre_archivo)

            # 3. Copiar
            shutil.copy2(file, dest_path)

            # 4. Borrar anterior si existía (maneja cambio de nombre de carpetas si es necesario)
            if mat.ruta_pdf_firmado:
                old = os.path.join(config.SHARED_FOLDER_PATH, mat.ruta_pdf_firmado)
                if os.path.exists(old) and os.path.abspath(old) != os.path.abspath(dest_path):
                    os.remove(old)

            mat.ruta_pdf_firmado = ruta_relativa_db
            session.commit()
            session.close()

            QMessageBox.information(self, "Éxito", "Firmado subido y organizado.")
            self.recargar_datos()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def accion_subir_lote(self):
        """
        Lógica actualizada para legibilidad web:
        1. Busca CERTIFICADOS.
        2. Crea estructura de carpetas REAL (Curso/Centro/).
        3. Guarda archivo como 'Cedula_Nombre.pdf'.
        4. Actualiza BD con ruta relativa.
        """
        try:
            # 1. Seleccionar Curso
            cursos = self.model_curso.search(order_by=text("fecha_final desc"), limit=None)
            if not cursos: return
            items = [(f"{c.nombre} (Fin: {c.fecha_final})", c.id) for c in cursos]

            dlg = DialogoBuscador(self, "Carga Lote (Organizada)", items)
            if not dlg.exec(): return
            curso_id = dlg.seleccionado_id

            # 2. Seleccionar Carpeta Origen
            dir_origen = QFileDialog.getExistingDirectory(self, "Carpeta con PDFs")
            if not dir_origen: return

            archivos = [f for f in os.listdir(dir_origen) if f.lower().endswith('.pdf')]
            if not archivos: return QMessageBox.warning(self, "Aviso", "No hay PDFs.")

            session = SessionLocal()
            os.makedirs(config.SHARED_FOLDER_PATH, exist_ok=True)

            try:
                # Cargar Certificados con relaciones necesarias para nombrar carpetas y archivos
                certificados = session.query(Certificado).join(Persona).filter(
                    Certificado.curso_id == curso_id
                ).all()

                count = 0

                for cert in certificados:
                    persona = cert.persona
                    cedula = persona.cedula

                    # Buscar archivo (Prioridad: mayor número de "signed")
                    candidatos = [f for f in archivos if cedula in f]

                    if candidatos:
                        candidatos.sort(key=lambda x: x.lower().count('signed'), reverse=True)
                        archivo_origen = candidatos[0]

                        # Buscar Matrícula para obtener el Centro y guardar ruta
                        # Necesitamos joinedload para el Centro
                        mat = session.query(Matricula).options(
                            joinedload(Matricula.curso),
                            joinedload(Matricula.centro)
                        ).filter(
                            Matricula.persona_id == persona.id,
                            Matricula.curso_id == curso_id
                        ).first()

                        if mat:
                            # --- NUEVA LÓGICA DE ORGANIZACIÓN ---
                            nombre_curso = self._limpiar_nombre(mat.curso.nombre)
                            nombre_centro = self._limpiar_nombre(mat.centro.nombre) if mat.centro else "Sin_Centro"
                            nombre_persona = self._limpiar_nombre(persona.nombre)

                            # Estructura: SHARED / Nombre Curso / Nombre Centro /
                            carpeta_relativa = os.path.join(nombre_curso, nombre_centro)
                            carpeta_absoluta = os.path.join(config.SHARED_FOLDER_PATH, carpeta_relativa)
                            os.makedirs(carpeta_absoluta, exist_ok=True)

                            # Nombre Archivo: Cedula_Nombre.pdf
                            nombre_nuevo = f"{cedula}_{nombre_persona}.pdf"
                            ruta_destino_abs = os.path.join(carpeta_absoluta, nombre_nuevo)
                            ruta_destino_rel = os.path.join(carpeta_relativa, nombre_nuevo)

                            # Copiar
                            shutil.copy2(os.path.join(dir_origen, archivo_origen), ruta_destino_abs)

                            # Limpiar anterior si era diferente
                            if mat.ruta_pdf_firmado:
                                old = os.path.join(config.SHARED_FOLDER_PATH, mat.ruta_pdf_firmado)
                                if os.path.exists(old) and os.path.abspath(old) != os.path.abspath(ruta_destino_abs):
                                    try:
                                        os.remove(old)
                                    except:
                                        pass  # Ignorar si no se puede borrar

                            mat.ruta_pdf_firmado = ruta_destino_rel
                            count += 1

                session.commit()
                QMessageBox.information(self, "Fin", f"Vinculados y organizados: {count}")
            finally:
                session.close()
                self.recargar_datos()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def accion_descargar_zip_curso(self):
        """
        Descarga ZIP. Como ahora los archivos YA están organizados en carpetas,
        simplemente los recolectamos manteniendo o recreando esa estructura.
        """
        try:
            cursos = self.model_curso.search(order_by=text("fecha_final desc"), limit=None)
            items = [(f"{c.nombre}", c.id) for c in cursos]
            dlg = DialogoBuscador(self, "Descargar ZIP", items)
            if not dlg.exec(): return

            session = SessionLocal()
            mats = session.query(Matricula).filter(Matricula.curso_id == dlg.seleccionado_id).all()

            temp_dir = tempfile.mkdtemp()
            cnt = 0

            for m in mats:
                if m.ruta_pdf_firmado:
                    # Ruta absoluta actual
                    src = os.path.join(config.SHARED_FOLDER_PATH, m.ruta_pdf_firmado)

                    if os.path.exists(src):
                        # Queremos que en el ZIP quede organizado por Centro/Institucion
                        # Podemos confiar en la ruta guardada O re-generar estructura si se desea agrupar distinto.
                        # Aquí usaremos la lógica de agrupación por Institución como pediste antes.

                        nombre_centro = self._limpiar_nombre(m.centro.nombre) if m.centro else "Sin Centro"
                        nombre_inst = self._limpiar_nombre(
                            m.persona.institucion_articulada) if m.persona and m.persona.institucion_articulada else "Particulares"
                        nombre_archivo = os.path.basename(src)  # Ya tiene formato Cedula_Nombre.pdf gracias al subidor

                        carpeta_zip = os.path.join(temp_dir, nombre_centro, nombre_inst)
                        os.makedirs(carpeta_zip, exist_ok=True)

                        shutil.copy2(src, os.path.join(carpeta_zip, nombre_archivo))
                        cnt += 1

            session.close()

            if cnt == 0:
                shutil.rmtree(temp_dir)
                return QMessageBox.warning(self, "Aviso", "No hay firmados para este curso.")

            dest, _ = QFileDialog.getSaveFileName(self, "Guardar ZIP", "Certificados_Curso.zip", "ZIP (*.zip)")
            if dest:
                shutil.make_archive(dest.replace('.zip', ''), 'zip', temp_dir)
                QMessageBox.information(self, "Éxito", f"ZIP guardado con {cnt} archivos.")

            shutil.rmtree(temp_dir)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _limpiar_nombre(self, t):
        if not t: return "Indefinido"
        # Permitimos letras, numeros, espacios, guiones y puntos. Eliminamos caracteres reservados de sistema.
        return re.sub(r'[<>:"/\\|?*]', '', str(t)).strip()[:60]

    def actualizar_interfaz_paginacion(self):
        actualizar_paginacion_ui(self.pagina_actual, self.total_paginas, self.total_registros, self.lbl_paginacion,
                                 None, self.btn_anterior, self.btn_siguiente)