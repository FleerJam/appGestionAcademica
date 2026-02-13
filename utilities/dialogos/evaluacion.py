from datetime import date
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout, QTableWidget, QHeaderView, QGroupBox, QHBoxLayout,
    QLineEdit, QDoubleSpinBox, QPushButton, QLabel, QTableWidgetItem,
    QMessageBox
)

from .base import DialogoBase
# Asumiendo que el archivo se llama sanitizer.py y está en una ruta accesible,
# ajusta la importación según tu estructura de carpetas (ej. from utils.sanitizer import ...)
from utilities.sanitizer import Sanitizer

from database.conexion import SessionLocal
from database.models import EvaluacionCurso, Matricula, Calificacion
from models.matricula_model import MatriculaModel


class DialogoEsquemaEvaluacion(DialogoBase):
    """Permite al usuario definir los módulos o actividades evaluativas de un curso."""

    def __init__(self, curso_id, parent=None):
        """
        Inicializa el diálogo de configuración de evaluaciones.

        Args:
            curso_id: ID del curso a configurar.
            parent: Widget padre.
        """
        super().__init__(parent)
        self.curso_id = curso_id
        self.setWindowTitle("Configurar Sistema de Evaluación")
        self.setFixedSize(600, 500)
        self.db = SessionLocal()

        # Instancia del modelo centralizado para cálculos
        self.matricula_model = MatriculaModel()

        self.init_ui()
        self.cargar_esquema()

    def init_ui(self):
        """
        Crea la tabla de evaluaciones y el formulario para agregar nuevas.
        """
        layout = QVBoxLayout(self)

        # --- Tabla de Evaluaciones Actuales ---
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["Nombre Actividad", "Porcentaje (%)", "Acción"])

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setMinimumSectionSize(120)
        layout.addWidget(self.tabla)

        # --- Formulario de Nueva Evaluación ---
        form_group = QGroupBox("Agregar Nueva Evaluación")
        form_layout = QHBoxLayout(form_group)

        self.input_nombre = QLineEdit()
        self.input_nombre.setPlaceholderText("Ej: EXAMEN FINAL")
        # USO DEL SANITIZER: Limpia mientras escribes en el campo de agregar
        self.input_nombre.textChanged.connect(lambda: self._forzar_sanitizacion(self.input_nombre))

        self.input_porcentaje = QDoubleSpinBox()
        self.input_porcentaje.setRange(0.1, 100.0)
        self.input_porcentaje.setSuffix(" %")
        self.input_porcentaje.setValue(10.0)

        btn_agregar = QPushButton("Agregar")
        btn_agregar.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        btn_agregar.clicked.connect(self.agregar_evaluacion)

        form_layout.addWidget(QLabel("Nombre:"))
        form_layout.addWidget(self.input_nombre)
        form_layout.addWidget(QLabel("Peso:"))
        form_layout.addWidget(self.input_porcentaje)
        form_layout.addWidget(btn_agregar)

        layout.addWidget(form_group)

        # --- Totales y Cierre ---
        self.lbl_total = QLabel("Total Ponderación: 0%")
        self.lbl_total.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.lbl_total)

        self.btn_cerrar = QPushButton("Finalizar Configuración")
        self.btn_cerrar.clicked.connect(self.accept)
        self.btn_cerrar.setEnabled(False)
        layout.addWidget(self.btn_cerrar)

    def _forzar_sanitizacion(self, widget: QLineEdit):
        """
        Método auxiliar para limpiar el texto de un QLineEdit en tiempo real.
        Evita tildes y fuerza mayúsculas usando Sanitizer.
        """
        texto_original = widget.text()
        if not texto_original:
            return

        # Usamos el sanitizer provisto
        texto_limpio = Sanitizer.casi_limpio(texto_original)

        if texto_original != texto_limpio:
            # Guardamos posición del cursor para no incomodar al usuario
            pos = widget.cursorPosition()
            widget.setText(texto_limpio)
            # Restauramos cursor (ajustando si la longitud cambió, aunque limpiar_texto suele mantenerla)
            widget.setCursorPosition(pos)



    def cargar_esquema(self):
        """
        Carga las evaluaciones existentes desde la BD y las puebla en la tabla.
        """
        self.tabla.setRowCount(0)
        total_pct = 0.0

        try:
            self.db.expire_all()
            evaluaciones = self.db.query(EvaluacionCurso).filter_by(curso_id=self.curso_id).order_by(
                EvaluacionCurso.orden).all()

            for ev in evaluaciones:
                row = self.tabla.rowCount()
                self.tabla.insertRow(row)

                # --- COLUMNA 0: NOMBRE EDITABLE ---
                # Ahora usamos un QLineEdit en lugar de un QTableWidgetItem estático
                input_nombre_existente = QLineEdit(ev.nombre)
                # 1. Sanitizar al escribir (No permite tildes)
                input_nombre_existente.textChanged.connect(
                    lambda _, w=input_nombre_existente: self._forzar_sanitizacion(w)
                )
                # 2. Guardar en BD al terminar de editar (perder foco o Enter)
                input_nombre_existente.editingFinished.connect(
                    lambda eid=ev.id, w=input_nombre_existente: self.actualizar_nombre_bd(eid, w)
                )
                self.tabla.setCellWidget(row, 0, input_nombre_existente)

                # --- COLUMNA 1: PORCENTAJE ---
                spin_pct = QDoubleSpinBox()
                spin_pct.setRange(0.1, 100.0)
                spin_pct.setSuffix(" %")
                spin_pct.setValue(ev.porcentaje)
                spin_pct.valueChanged.connect(lambda val, eid=ev.id: self.actualizar_porcentaje_bd(eid, val))
                self.tabla.setCellWidget(row, 1, spin_pct)

                # --- COLUMNA 2: BORRAR ---
                btn_borrar = QPushButton("Eliminar")
                btn_borrar.setStyleSheet("color: red;")
                btn_borrar.clicked.connect(lambda _, eid=ev.id: self.eliminar_evaluacion(eid))
                self.tabla.setCellWidget(row, 2, btn_borrar)

                total_pct += ev.porcentaje

            self.actualizar_label_total(total_pct)

        except Exception as e:
            self.mostrar_error(f"Error cargando esquema: {e}")

    def actualizar_nombre_bd(self, eval_id, widget: QLineEdit):
        """Actualiza el nombre de la evaluación en la BD cuando se edita en la tabla."""
        nuevo_nombre = widget.text().strip()

        # Validar que no quede vacío
        if not nuevo_nombre:
            self.mostrar_error("El nombre de la actividad no puede estar vacío.")
            # Restaurar el valor anterior desde la BD
            try:
                ev = self.db.query(EvaluacionCurso).get(eval_id)
                if ev: widget.setText(ev.nombre)
            except:
                pass
            return

        try:
            ev = self.db.query(EvaluacionCurso).get(eval_id)
            if ev and ev.nombre != nuevo_nombre:
                ev.nombre = nuevo_nombre
                self.db.commit()
                print(f"Nombre actualizado: {nuevo_nombre}")
        except Exception as e:
            self.db.rollback()
            self.mostrar_error(f"Error al actualizar nombre: {e}")

    def recalcular_promedios_globales(self):
        """
        Recalcula las notas numéricas basándose en los nuevos pesos y luego
        DELEGA la actualización de estados al MatriculaModel centralizado.
        """
        try:
            # 1. Preparar datos de pesos
            esquema = self.db.query(EvaluacionCurso).filter_by(curso_id=self.curso_id).all()
            mapa_pesos = {e.id: e.porcentaje for e in esquema}

            # 2. Recalcular SOLO la Nota Final Numérica
            matriculas = self.db.query(Matricula).filter_by(curso_id=self.curso_id).all()

            for mat in matriculas:
                # Si abandonó, saltamos cálculo (la lógica de estados lo manejará después si es necesario)
                if mat.estado == "NO REALIZO":
                    continue

                notas = self.db.query(Calificacion).filter_by(matricula_id=mat.id).all()

                # Armar estructura para cálculo
                lista_notas = []
                for nota in notas:
                    lista_notas.append({
                        'puntaje': nota.puntaje,
                        'peso': mapa_pesos.get(nota.evaluacion_curso_id, 0.0)
                    })

                # Calculamos el promedio numérico
                nuevo_promedio = self.matricula_model.calcular_nota_ponderada(lista_notas)
                mat.nota_final = nuevo_promedio

            # 3. Guardamos los cambios de NOTAS en la BD
            self.db.commit()

            # 4. LLAMADA CENTRALIZADA PARA ESTADOS
            self.matricula_model.actualizar_estados_por_curso(curso_id=self.curso_id)

            print("Recálculo masivo (Notas + Estados Centralizados) completado.")

        except Exception as e:
            self.db.rollback()
            print(f"Error en recálculo masivo: {e}")

    def actualizar_porcentaje_bd(self, eval_id, nuevo_valor):
        """Actualiza el peso porcentual en la BD y recalcula promedios globales."""
        try:
            ev = self.db.query(EvaluacionCurso).get(eval_id)
            if ev:
                ev.porcentaje = nuevo_valor
                self.db.commit()
                self.recalcular_total_ui()
                self.recalcular_promedios_globales()
        except Exception as e:
            print(f"Error al actualizar porcentaje: {e}")

    def recalcular_total_ui(self):
        """Suma los valores de los spinners de la tabla para actualizar el label de total."""
        total = 0.0
        for i in range(self.tabla.rowCount()):
            widget = self.tabla.cellWidget(i, 1)
            if isinstance(widget, QDoubleSpinBox):
                total += widget.value()
        self.actualizar_label_total(total)

    def actualizar_label_total(self, total_pct):
        """
        Actualiza el texto y color del label de total de ponderación.
        Habilita el botón de finalizar solo si suma 100%.
        """
        self.lbl_total.setText(f"Total Ponderación: {total_pct:.2f}%")
        es_valido = abs(total_pct - 100.0) < 0.01

        if es_valido:
            self.lbl_total.setStyleSheet("color: green; font-weight: bold;")
        elif total_pct > 100.0:
            self.lbl_total.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.lbl_total.setStyleSheet("color: orange; font-weight: bold;")

        if hasattr(self, 'btn_cerrar'):
            self.btn_cerrar.setEnabled(es_valido)

    def agregar_evaluacion(self):
        """Crea una nueva actividad evaluativa y la guarda en la BD."""
        # Sanitizamos explícitamente antes de guardar, por si acaso
        nombre = Sanitizer.limpiar_texto(self.input_nombre.text())
        pct = self.input_porcentaje.value()

        if not nombre:
            self.mostrar_error("Debe ingresar un nombre para la actividad.")
            return

        try:
            nueva = EvaluacionCurso(
                curso_id=self.curso_id, nombre=nombre, porcentaje=pct,
                orden=self.tabla.rowCount() + 1
            )
            self.db.add(nueva)
            self.db.commit()

            self.input_nombre.clear()
            self.cargar_esquema()
            self.recalcular_promedios_globales()
        except Exception as e:
            self.db.rollback()
            self.mostrar_error(f"Error al guardar: {e}")

    def eliminar_evaluacion(self, eval_id):
        """Elimina una evaluación y sus notas asociadas tras confirmación."""
        confirm = QMessageBox.question(self, "Confirmar", "¿Eliminar esta evaluación? Se borrarán las notas asociadas.",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                item = self.db.query(EvaluacionCurso).get(eval_id)
                if item:
                    self.db.delete(item)
                    self.db.commit()
                    self.cargar_esquema()
                    self.recalcular_promedios_globales()
            except Exception as e:
                self.db.rollback()
                self.mostrar_error(str(e))

    def closeEvent(self, event):
        """Cierra la conexión a BD al cerrar la ventana."""
        self.db.close()
        super().closeEvent(event)