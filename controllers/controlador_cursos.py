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
from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

# --- IMPORTACIONES DEL PROYECTO ---
from utilities.helper import PyQtHelper, actualizar_paginacion_ui
from models.curso_model import CursoModel
from utilities.delegado import BotonDetalleDelegate
from utilities.dialogos import DialogoEsquemaEvaluacion


# ---------------- CONTROLADOR PRINCIPAL ----------------
class ControladorCursos(QWidget):
    """Controlador principal para la gestión y visualización del listado de cursos.

    Esta clase maneja la interfaz de usuario correspondiente al catálogo de adiestramientos.
    Permite visualizar los cursos en una tabla paginada, filtrarlos por nombre o modalidad,
    y ejecutar acciones específicas (ver detalle, configurar esquema, borrar) mediante
    botones integrados en las celdas.
    """

    signal_abrir_detalle = pyqtSignal(object)  # Emite el objeto curso al MainController

    def __init__(self):
        """Inicializa el controlador de cursos.

        Carga la interfaz gráfica desde el archivo .ui, instancia el modelo de datos,
        configura los delegados para los botones de acción y establece la configuración
        inicial de la paginación.
        """
        super().__init__()

        # Cargar UI
        try:
            uic.loadUi("views/adiestramientos.ui", self)
        except Exception as e:
            QMessageBox.critical(self, "Error UI", f"No se pudo cargar la interfaz: {e}")
            return

        # Modelo
        self.model_curso = CursoModel()

        # CAMBIO: Agregamos una columna más para el botón Borrar (índice 2)
        # Índices: 0=Detalle, 1=Esquema, 2=Borrar, 3=Nombre...
        self.columnas_headers = ["", "", "", "Nombre Curso", "Fecha Inicio", "Fecha Fin", "Duración", "Modalidad",
                                 "Inscritos"]

        # Paginación
        self.registros_por_pagina = 50
        self.pagina_actual = 1
        self.total_registros = 0
        self.total_paginas = 1

        # 1. Delegado de VER DETALLE (Columna 0)
        self.delegado_detalle = BotonDetalleDelegate(
            callback=self.abrir_detalle_curso,
            icon_path="assets/icons/ver-detalles.png",
            columna=0
        )

        # 2. Delegado de ESQUEMA EVALUACIÓN (Columna 1)
        self.delegado_esquema = BotonDetalleDelegate(
            callback=self.abrir_esquema_curso,
            icon_path="assets/icons/checklist.png",
            columna=1
        )

        # 3. NUEVO: Delegado de BORRAR CURSO (Columna 2)
        self.delegado_borrar = BotonDetalleDelegate(
            callback=self.borrar_curso,
            icon_path="assets/icons/delete.png",  # Asegúrate de tener este icono
            columna=2
        )

        # Setup UI
        self.setup_ui_elements()
        self.cargar_formato_tabla()
        self.cargar_datos_tabla()

    # ---------------- CONFIGURACIÓN UI ----------------
    def setup_ui_elements(self):
        """Configura los elementos de la interfaz de usuario y conecta sus señales.

        Asigna funciones a los botones de navegación (anterior/siguiente), al botón
        de recarga y al campo de búsqueda.
        """
        if hasattr(self, 'btn_recargar'):
            self.btn_recargar.clicked.connect(self.recargar_datos)
            self.btn_recargar.setIcon(QIcon("assets/icons/refresh.png"))

        if hasattr(self, 'input_buscar'):
            self.input_buscar.textChanged.connect(self.filtrar_tabla)

        if hasattr(self, 'btn_before'):
            self.btn_before.clicked.connect(self.pagina_anterior)
        if hasattr(self, 'btn_after'):
            self.btn_after.clicked.connect(self.pagina_siguiente)

    # ---------------- ACCIONES ----------------
    def recargar_datos(self):
        """Reinicia la vista a la primera página y recarga los datos desde la BD.

        Limpia el campo de búsqueda si existe.
        """
        self.pagina_actual = 1
        if hasattr(self, 'input_buscar'):
            self.input_buscar.clear()
        self.cargar_datos_tabla()

    def filtrar_tabla(self):
        """Filtra la tabla según el texto ingresado en el buscador.

        Reinicia la paginación a la primera página cada vez que cambia el filtro.
        """
        self.pagina_actual = 1
        self.cargar_datos_tabla()

    # ---------------- FORMATO TABLA ----------------
    def cargar_formato_tabla(self):
        """Configura la estructura visual y funcional de la tabla de cursos.

        Define el ancho de las columnas y asigna los delegados (botones personalizados)
        a las primeras tres columnas (Detalle, Esquema, Borrar).
        """
        tabla = getattr(self, 'tabla_cursos', None)
        if not tabla:
            return

        # CAMBIO: Ajuste de anchos para las 9 columnas (3 botones + 6 datos)
        # 40px para cada botón
        anchos = [40, 40, 40, 250, 110, 110, 80, 120, 80]

        # Configuración base usando el Helper
        # columnas_boton=[0, 1, 2] -> Fija las 3 primeras columnas y les pone cursor de mano
        PyQtHelper.configurar_tabla(
            tabla,
            self.columnas_headers,
            anchos,
            columnas_boton=[0, 1, 2]
        )

        # Asignar los delegados a sus columnas específicas
        tabla.setItemDelegateForColumn(0, self.delegado_detalle)
        tabla.setItemDelegateForColumn(1, self.delegado_esquema)
        tabla.setItemDelegateForColumn(2, self.delegado_borrar)  # <--- Nuevo delegado

    # ---------------- PAGINACIÓN ----------------
    def pagina_anterior(self):
        """Retrocede a la página anterior de resultados y actualiza la tabla."""
        if self.pagina_actual > 1:
            self.pagina_actual -= 1
            self.cargar_datos_tabla()

    def pagina_siguiente(self):
        """Avanza a la página siguiente de resultados y actualiza la tabla."""
        if self.pagina_actual < self.total_paginas:
            self.pagina_actual += 1
            self.cargar_datos_tabla()

    def actualizar_interfaz_paginacion(self):
        """Actualiza el estado visual de los controles de paginación.

        Habilita o deshabilita botones y actualiza las etiquetas de conteo de registros
        según la página actual y el total de datos.
        """
        actualizar_paginacion_ui(
            pagina_actual=self.pagina_actual,
            total_paginas=self.total_paginas,
            total_registros=self.total_registros,
            lbl_registros=getattr(self, 'lbl_registros', None),
            lbl_contador=getattr(self, 'lbl_contador', None),
            btn_before=getattr(self, 'btn_before', None),
            btn_after=getattr(self, 'btn_after', None)
        )

    # ---------------- CARGA DE DATOS ----------------
    def cargar_datos_tabla(self):
        """Consulta la base de datos y rellena la tabla con la información de los cursos.

        Realiza las siguientes tareas:
        1. Obtiene los filtros de búsqueda.
        2. Calcula el total de registros y páginas.
        3. Obtiene el segmento de datos (offset/limit) correspondiente a la página actual.
        4. Formatea fechas y cuenta inscritos.
        5. Inserta los datos en el widget QTableWidget.
        """
        tabla = getattr(self, 'tabla_cursos', None)
        if not tabla:
            return

        tabla.setUpdatesEnabled(False)
        tabla.setRowCount(0)

        texto_busqueda = getattr(self, 'input_buscar', None)
        texto_busqueda = texto_busqueda.text().strip() if texto_busqueda else ""

        try:
            or_fields = [('nombre', texto_busqueda), ('modalidad', texto_busqueda)] if texto_busqueda else []

            # Total de registros
            self.total_registros = self.model_curso.count(or_fields=or_fields)

            # Total de páginas
            self.total_paginas = max(
                1,
                (self.total_registros + self.registros_por_pagina - 1) // self.registros_por_pagina
            )

            # 🔒 Asegurar página válida
            if self.pagina_actual > self.total_paginas:
                self.pagina_actual = self.total_paginas

            offset = (self.pagina_actual - 1) * self.registros_por_pagina

            # Obtener registros de la página actual
            cursos = self.model_curso.search(
                order_by="nombre",
                limit=self.registros_por_pagina,
                offset=offset,
                or_fields=or_fields
            )

        except Exception as e:
            print(f"Error cargando datos: {e}")
            tabla.setUpdatesEnabled(True)
            return

        filas = []
        for curso in cursos:
            f_inicio = curso.fecha_inicio.strftime("%d/%m/%Y") if curso.fecha_inicio else ""
            f_fin = curso.fecha_final.strftime("%d/%m/%Y") if curso.fecha_final else ""
            duracion = f"{curso.duracion_horas}h" if curso.duracion_horas else ""
            modalidad = getattr(curso, 'modalidad', "")
            inscritos = str(self.model_curso.estudiantes_inscritos(curso.id)) if hasattr(self.model_curso,
                                                                                         'estudiantes_inscritos') else "0"

            filas.append([
                curso.id,  # Col 0: ID para botón detalle
                curso.id,  # Col 1: ID para botón esquema
                curso.id,  # Col 2: ID para botón borrar (NUEVO)
                curso.nombre,
                f_inicio,
                f_fin,
                duracion,
                modalidad,
                inscritos
            ])

        # id_column=0 guarda el ID principal en la columna 0.
        # Los delegados 1 y 2 buscarán en la col 0 automáticamente gracias al cambio previo en BotonDetalleDelegate.
        PyQtHelper.cargar_datos_en_tabla(
            tabla,
            filas,
            id_column=0,
            alineacion=Qt.AlignmentFlag.AlignCenter
        )
        self.actualizar_interfaz_paginacion()

    # ---------------- ACCIONES DELEGADOS ----------------
    def abrir_detalle_curso(self, id_curso):
        """Emite una señal para abrir la vista detallada del curso seleccionado.

        Args:
            id_curso (int): ID del curso a visualizar.
        """
        curso = self.model_curso.get_by_id(id_curso)
        if curso:
            self.signal_abrir_detalle.emit(curso)
        else:
            QMessageBox.warning(self, "Error", "No se encontró la información del curso seleccionado.")

    def abrir_esquema_curso(self, id_curso):
        """Abre el diálogo modal para configurar el esquema de evaluación del curso.

        Args:
            id_curso (int): ID del curso a configurar.
        """
        """Abre el diálogo para configurar las evaluaciones."""
        dlg = DialogoEsquemaEvaluacion(id_curso, self)
        dlg.exec()

    def borrar_curso(self, id_curso):
        """Elimina un curso de la base de datos tras un proceso de doble confirmación.

        Debido a que la eliminación es en cascada (borra estudiantes, notas, etc.),
        se solicita una confirmación estándar y luego una advertencia crítica.

        Args:
            id_curso (int): ID del curso a eliminar.
        """
        """Elimina el curso tras doble confirmación."""
        curso = self.model_curso.get_by_id(id_curso)
        nombre_curso = curso.nombre if curso else "este curso"

        # 1. Primera confirmación
        confirmacion1 = QMessageBox.question(
            self,
            "Eliminar Curso",
            f"¿Está seguro de que desea eliminar el curso:\n'{nombre_curso}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirmacion1 != QMessageBox.StandardButton.Yes:
            return

        # 2. Segunda confirmación (Advertencia Crítica)
        confirmacion2 = QMessageBox.warning(
            self,
            "Confirmación Final - IRREVERSIBLE",
            f"¡ADVERTENCIA CRÍTICA!\n\n"
            f"Al eliminar '{nombre_curso}' se borrarán permanentemente:\n"
            f"- Todos los estudiantes matriculados.\n"
            f"- Todas las calificaciones y asistencias.\n"
            f"- La configuración del esquema de evaluación.\n\n"
            f"¿Realmente desea continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if confirmacion2 == QMessageBox.StandardButton.Yes:
            try:
                exito = self.model_curso.delete(id_curso)
                if exito:
                    QMessageBox.information(self, "Eliminado", "El curso ha sido eliminado correctamente.")
                    self.recargar_datos()
                else:
                    QMessageBox.warning(self, "Error", "No se pudo eliminar el curso (no encontrado o bloqueado).")
            except Exception as e:
                QMessageBox.critical(self, "Error Crítico", f"Ocurrió un error al intentar eliminar:\n{e}")