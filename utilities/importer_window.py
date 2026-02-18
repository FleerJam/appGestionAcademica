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
from typing import List, Dict, Set

from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QProgressDialog, QApplication
from datetime import datetime

# Componentes Propios
from utilities.dialogos import DialogoEntrada, DialogoSeleccion
from models.curso_model import CursoModel

# Componentes de UI
from utilities.mapping_dialog import DialogoMapeoNotas
from utilities.dialogos import DialogoEsquemaEvaluacion

from controllers.import_processor import ExcelEngine, Validator
from services.persistence import PersistenceService
from database.schemas import RegistroImportado, ResultadoProceso
from utilities.sanitizer import Sanitizer


class WorkerProcesamiento(QObject):
    """
    Hilo de trabajo (Worker) encargado del procesamiento pesado de lectura
    y validación del archivo Excel.
    """
    finished = pyqtSignal(list, list)
    error = pyqtSignal(str)

    def __init__(self, excel_path, curso_obj, mapa_cols_manual, mapa_actividades, esquema_ponderacion):
        """
        Inicializa el worker con los parámetros necesarios para la validación.

        Args:
            excel_path (str): Ruta del archivo Excel.
            curso_obj: Objeto del curso seleccionado.
            mapa_cols_manual (dict): Mapeo manual de columnas de datos personales.
            mapa_actividades (dict): Mapeo de columnas de Excel a evaluaciones del curso.
            esquema_ponderacion (dict): Configuración de pesos de las evaluaciones.
        """
        super().__init__()
        self.path = excel_path
        self.curso = curso_obj
        self.mapa_manual = mapa_cols_manual
        self.mapa_actividades = mapa_actividades
        self.esquema_ponderacion = esquema_ponderacion
        self.persistence = PersistenceService()

    def run(self):
        """
        Ejecuta la lógica de carga, mapeo y validación de datos.
        Emite señal 'finished' con los resultados o 'error' si falla.
        """
        try:
            self.persistence.cargar_caches(self.curso.id)
            dict_aliases = self.persistence.obtener_diccionario_aliases()

            engine = ExcelEngine(self.path)
            if not engine.cargar():
                self.error.emit("No se pudo leer el archivo Excel.")
                return

            if self.mapa_manual:
                engine.mapa_cols = self.mapa_manual

            validator = Validator(
                engine.df, engine.mapa_cols, self.curso, dict_aliases,
                self.mapa_actividades, self.esquema_ponderacion
            )
            validos, revision = validator.procesar()

            self.finished.emit(validos, revision)
        except Exception as e:
            self.error.emit(f"Error interno en Worker: {str(e)}")


class WorkerGuardado(QObject):
    """
    Hilo de trabajo dedicado exclusivamente a la persistencia de datos en la base de datos
    para evitar congelar la interfaz gráfica.
    """
    finished = pyqtSignal(ResultadoProceso)
    error = pyqtSignal(str)

    def __init__(self, persistence_service, lista_datos: List[RegistroImportado], curso_id):
        """
        Inicializa el worker de guardado.

        Args:
            persistence_service (PersistenceService): Instancia del servicio de persistencia.
            lista_datos (List[RegistroImportado]): Lista de registros validados y listos para guardar.
            curso_id (str): ID del curso destino.
        """
        super().__init__()
        self.service = persistence_service
        self.lista = lista_datos
        self.curso_id = curso_id

    def run(self):
        """
        Ejecuta el guardado por lotes llamando al servicio de persistencia.
        """
        try:
            res = self.service.guardar_lote(self.lista, self.curso_id)
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


class GestorImportacion:
    """
    Controlador principal que orquesta todo el flujo de importación de datos desde Excel.
    Maneja la UI de selección, mapeo de columnas, validación interactiva y guardado.
    """
    def __init__(self, parent_widget):
        """
        Inicializa el gestor.

        Args:
            parent_widget (QWidget): Widget padre para mostrar diálogos modales.
        """
        self.parent = parent_widget
        self.persistence_service = PersistenceService()
        self.curso_model = CursoModel()

        self.thread_proc = None
        self.worker_proc = None
        self.thread_save = None
        self.worker_save = None

        self.pd_save = None
        self.reporte_errores = []
        self.lista_omitidos = []  # NUEVO: Lista separada para los omitidos manualmente

    def ejecutar(self):
        """
        Inicia el asistente de importación paso a paso.
        """
        self.reporte_errores = []
        self.lista_omitidos = []  # Reiniciar omitidos

        # 1. Selección Archivo
        archivo, _ = QFileDialog.getOpenFileName(self.parent, "Seleccionar Excel", "", "Excel Files (*.xlsx *.ods)")
        if not archivo: return

        # 2. Selección Curso
        cursos = self.curso_model.cursos_activos()
        if not cursos:
            QMessageBox.warning(self.parent, "Atención", "No existen cursos activos.")
            return

        nombres = [c.nombre for c in cursos]
        sel_dialog = DialogoSeleccion("Seleccionar Curso", "Destino:", nombres, self.parent)
        if not sel_dialog.exec(): return

        nombre_curso = sel_dialog.obtener_seleccion()
        curso_seleccionado = next(c for c in cursos if c.nombre == nombre_curso)

        # 3. Pre-validación Columnas
        engine_pre = ExcelEngine(archivo)
        if not engine_pre.cargar():
            QMessageBox.critical(self.parent, "Error", "Archivo corrupto.")
            return

        def resolver_ui(nombre, opciones):
            item, ok = QInputDialog.getItem(self.parent, "Asignación Manual", f"Falta '{nombre}':", opciones, 0, False)
            return item if ok else None

        if not engine_pre.mapear_columnas(manual_resolver_callback=resolver_ui):
            return

        # --- VERIFICACIÓN Y GESTIÓN DE ESQUEMA ---
        esquema = self.persistence_service.obtener_esquema_curso(curso_seleccionado.id)

        # Si NO hay esquema, ofrecemos crearlo
        if not esquema:
            resp_crear = QMessageBox.question(
                self.parent, "Sistema de Evaluación Faltante",
                f"El curso '{curso_seleccionado.nombre}' no tiene configurado un sistema de evaluación.\n\n"
                "¿Desea configurarlo AHORA para poder importar las notas del Excel?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if resp_crear == QMessageBox.StandardButton.Yes:
                dlg_esquema = DialogoEsquemaEvaluacion(curso_seleccionado.id, self.parent)
                dlg_esquema.exec()
                esquema = self.persistence_service.obtener_esquema_curso(curso_seleccionado.id)

        # Preparamos variables
        mapa_actividades = {}
        esquema_ponderacion = {}

        if esquema:
            esquema_ponderacion = {e['id']: e['porcentaje'] for e in esquema}
            columnas_disponibles = engine_pre.obtener_columnas_restantes()

            dialogo_mapeo = DialogoMapeoNotas(columnas_disponibles, esquema, self.parent)
            if not dialogo_mapeo.exec():
                return  # Cancelado en mapeo

            mapa_actividades = dialogo_mapeo.obtener_mapeo()
            if not mapa_actividades:
                QMessageBox.warning(self.parent, "Info", "No vinculó columnas. Se importarán solo datos personales.")
        else:
            resp_final = QMessageBox.warning(
                self.parent, "Importación Parcial",
                "⚠️ No hay esquema de evaluación.\n\n"
                "Se importarán SOLO los estudiantes y matrículas (Sin Calificaciones).\n"
                "¿Desea continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resp_final == QMessageBox.StandardButton.No:
                return

        # 4. Iniciar Worker
        self.thread_proc = QThread()
        self.worker_proc = WorkerProcesamiento(
            archivo, curso_seleccionado, engine_pre.mapa_cols,
            mapa_actividades, esquema_ponderacion
        )
        self.worker_proc.moveToThread(self.thread_proc)

        self.thread_proc.started.connect(self.worker_proc.run)
        self.worker_proc.finished.connect(lambda v, r: self._al_terminar_analisis(v, r, curso_seleccionado))
        self.worker_proc.error.connect(lambda e: QMessageBox.critical(self.parent, "Error", e))

        self.worker_proc.finished.connect(self.thread_proc.quit)
        self.worker_proc.finished.connect(self.worker_proc.deleteLater)
        self.thread_proc.finished.connect(self.thread_proc.deleteLater)

        self.thread_proc.start()

    def _al_terminar_analisis(self, validos: List[RegistroImportado], revision: List[RegistroImportado], curso):
        """
        Callback ejecutado cuando termina el análisis del Excel.
        Maneja la deduplicación, revisión interactiva y lanza el proceso de guardado.
        """
        if not validos and not revision:
            QMessageBox.information(self.parent, "Finalizado", "No se encontraron registros válidos.")
            return

        self.persistence_service.cargar_caches(curso.id)

        # --- FASE 1: DEDUPLICACIÓN ---
        mapa_maestro: Dict[str, RegistroImportado] = {}
        for reg in validos:
            if reg.cedula_limpia in mapa_maestro:
                anterior = mapa_maestro[reg.cedula_limpia]
                self.reporte_errores.append(f"Duplicado interno: {reg.cedula_limpia} (Se usa fila {reg.fila_excel}).")
            mapa_maestro[reg.cedula_limpia] = reg

        # --- FASE 2: RESOLUCIÓN ---
        corregidos = []
        if revision:
            corregidos = self._resolver_revisiones_interactivas(revision, mapa_maestro)

        for reg in corregidos:
            mapa_maestro[reg.cedula_limpia] = reg

        lista_final_unica = list(mapa_maestro.values())

        if not lista_final_unica:
            QMessageBox.warning(self.parent, "Cancelado", "No hay registros para guardar.")
            return

        # Guardado
        self.pd_save = QProgressDialog("Guardando en Base de Datos...", None, 0, 0, self.parent)
        self.pd_save.setWindowTitle("Finalizando")
        self.pd_save.setWindowModality(Qt.WindowModality.WindowModal)
        self.pd_save.setCancelButton(None)
        self.pd_save.show()

        self.thread_save = QThread()
        self.worker_save = WorkerGuardado(self.persistence_service, lista_final_unica, curso.id)
        self.worker_save.moveToThread(self.thread_save)

        self.thread_save.started.connect(self.worker_save.run)
        self.worker_save.finished.connect(self._on_guardado_finished)
        self.worker_save.error.connect(lambda e: self._on_guardado_error(e))

        self.worker_save.finished.connect(self.thread_save.quit)
        self.worker_save.finished.connect(self.worker_save.deleteLater)
        self.thread_save.finished.connect(self.thread_save.deleteLater)

        self.thread_save.start()

    def _on_guardado_finished(self, resultado: ResultadoProceso):
        """Callback al finalizar el guardado en BD."""
        if self.pd_save: self.pd_save.close()

        # Le sumamos los omitidos manualmente durante la fase de revisión
        resultado.registros_omitidos += len(self.lista_omitidos)

        # --- CORRECCIÓN CLAVE ---
        # Fusionar la lista de reporte local (omisiones/duplicados) con la lista de errores del resultado (BD)
        if self.reporte_errores:
            # Ponemos los errores de validación primero, luego los de base de datos
            resultado.errores = self.reporte_errores + resultado.errores

        self._mostrar_resumen(resultado)

    def _on_guardado_error(self, error_msg):
        """Callback si ocurre un error crítico durante el guardado."""
        if self.pd_save: self.pd_save.close()
        QMessageBox.critical(self.parent, "Error de Guardado", f"Ocurrió un error al guardar:\n{error_msg}")

    # --- Lógica de Revisión Interactiva ---
    def _resolver_revisiones_interactivas(self, lista_revision, mapa_validos):
        """
        Itera sobre registros problemáticos y solicita intervención del usuario
        para corregir cédulas o resolver conflictos de duplicados.
        """
        aceptados = []
        mapa_aceptados = {}
        total = len(lista_revision)

        for i, reg in enumerate(lista_revision):
            while True:
                dialog = self._crear_dialogo_revision(reg, i, total)
                if not dialog.exec():
                    if self._confirmar_omision(reg):
                        self._registrar_omision(reg)
                        break
                    continue

                nueva_ced = dialog.obtener_dato().strip()
                if not Sanitizer.validar_cedula_ecuador(nueva_ced):
                    QMessageBox.warning(self.parent, "Error", "Cédula inválida.")
                    continue

                if nueva_ced in mapa_aceptados:
                    dup = mapa_aceptados[nueva_ced]
                    QMessageBox.warning(self.parent, "Duplicado", f"Ya asignada a {dup.nombre_limpio}.")
                    continue

                if nueva_ced in mapa_validos:
                    dup = mapa_validos[nueva_ced]
                    msg = (f"CONFLICTO INTERNO: La cédula {nueva_ced} ya existe en el archivo.\n\n"
                           f"🟦 REGISTRO EXISTENTE (Fila {dup.fila_excel}):\n"
                           f"   Nombre: {dup.nombre_limpio}\n"
                           f"   Nota Final: {dup.nota_final} ({dup.estado_sugerido})\n\n"
                           f"🟧 REGISTRO ACTUAL (Manual):\n"
                           f"   Nombre: {reg.nombre_limpio}\n"
                           f"   Nota Final: {reg.nota_final} ({reg.estado_sugerido})\n\n"
                           f"¿Qué registro desea conservar?")

                    box = QMessageBox(self.parent)
                    box.setWindowTitle("Conflicto de Datos")
                    box.setText(msg)
                    box.addButton("Mantener Existente", QMessageBox.ButtonRole.ActionRole)
                    btn_act = box.addButton("Sobrescribir con Actual", QMessageBox.ButtonRole.ActionRole)
                    box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)

                    box.exec()
                    clicked = box.clickedButton()

                    if clicked == btn_act:
                        pass
                    elif clicked == box.buttons()[0]:
                        self.reporte_errores.append(
                            f"Fusión: Se descartó {reg.nombre_limpio} en favor de existente {dup.nombre_limpio}.")
                        # Esto podría contarse como omisión técnica o fusión
                        break
                    else:
                        continue

                if not self._validar_existencia_bd(nueva_ced, reg):
                    continue

                reg.cedula_limpia = nueva_ced
                aceptados.append(reg)
                mapa_aceptados[nueva_ced] = reg
                break
        return aceptados

    def _crear_dialogo_revision(self, reg, i, total):
        """Crea y configura el diálogo de corrección de cédula."""
        msg = (f"Estudiante: {reg.nombre_limpio}\nCentro: {reg.centro_nombre}\n"
               f"Problema: Cédula '{reg.cedula_original}' inválida.\nIngrese la correcta:")
        val = reg.cedula_limpia or reg.cedula_original
        return DialogoEntrada(f"Revisión ({i + 1}/{total})", msg, val, self.parent)

    def _confirmar_omision(self, reg) -> bool:
        """Pregunta al usuario si desea descartar definitivamente un registro."""
        return QMessageBox.question(self.parent, "Omitir", f"¿Omitir a {reg.nombre_limpio}?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def _registrar_omision(self, reg):
        """Registra un registro omitido en las listas de control y reportes."""
        # Ahora registramos en lista específica Y en errores para el log
        self.lista_omitidos.append(reg)
        self.reporte_errores.append(f"Omitido por usuario: {reg.nombre_limpio} (Cédula: {reg.cedula_original})")

    def _validar_existencia_bd(self, cedula, reg):
        """
        Verifica si la cédula ya existe en la base de datos y pregunta al usuario
        si desea fusionar los datos.
        """
        est_bd = self.persistence_service.cache_estudiantes.get(cedula)
        if est_bd:
            msg = (f"La cédula {cedula} existe en BD:\n{est_bd.nombre}\n\n"
                   f"¿FUSIONAR con el registro actual ({reg.nombre_limpio})?\n\n"
                   f"ℹ️ IMPLICACIÓN: Se asignarán la matrícula y notas de este Excel al estudiante existente ({est_bd.nombre}), "
                   f"ignorando el nombre mal escrito que aparece en el archivo.")
            return QMessageBox.question(self.parent, "Existente en BD", msg,
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes
        return True

    def _mostrar_resumen(self, resultado):
        """Muestra el diálogo final con las estadísticas del proceso."""
        # Mensaje con formato detallado y viñetas
        msg = (
            "<b>Proceso de Importación Finalizado</b>"
            f"""<b>Proceso de Importación Finalizado</b><br><br>
                <b>Nuevos Estudiantes:</b> {resultado.nuevos_estudiantes}<br>
                <b>Matrículas Nuevas (Inscripciones):</b> {resultado.matriculas_nuevas}<br>
                <b>Matrículas Actualizadas (Notas):</b> {resultado.matriculas_actualizadas}<br>
                <b>Registros Omitidos:</b> <span style="color:red">{resultado.registros_omitidos}</span><br><br>
                <i>Errores técnicos: {len(resultado.errores)}</i>"""
        )

        box = QMessageBox(self.parent)
        box.setWindowTitle("Resumen de Importación")
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(msg)

        btn_ok = box.addButton("Aceptar", QMessageBox.ButtonRole.AcceptRole)

        btn_log = None
        if resultado.errores or resultado.registros_omitidos > 0:
            box.setText(msg + "<br><br>¿Desea guardar el log de errores/omisiones?")
            btn_log = box.addButton("Guardar Log", QMessageBox.ButtonRole.ActionRole)

        box.exec()

        if box.clickedButton() == btn_log:
            self._guardar_log(resultado.errores)
        if hasattr(self.parent, 'actualizar_cache_global'):
            self.parent.actualizar_cache_global()
        if hasattr(self.parent, 'cargar_datos_tabla'): self.parent.cargar_datos_tabla()
        if hasattr(self.parent, 'cargar_datos_tabla_cursos'): self.parent.cargar_datos_tabla_cursos()

    def _guardar_log(self, errores):
        """Guarda el archivo de texto con el log de errores."""
        ruta, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Guardar Log",
            f"log_{datetime.now().strftime('%H%M')}.txt"
        )

        if ruta:
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write("=== LOG DE ERRORES Y OMISIONES ===\n")
                f.write('\n'.join(errores))