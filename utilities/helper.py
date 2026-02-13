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

from PyQt6.QtWidgets import (
    QTableWidget,
    QHeaderView,
    QAbstractItemView,
    QTableWidgetItem,
    QLabel,
    QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QObject, QEvent


class PyQtHelper:
    """
    Clase utilitaria estática para configuraciones comunes de widgets PyQt,
    especialmente QTableWidget y manejo de cursores.
    """

    # -------------------------------------------------
    # CONFIGURACIÓN GENERAL DE TABLAS
    # -------------------------------------------------
    @staticmethod
    def configurar_tabla(
            tabla: QTableWidget,
            headers: list[str],
            anchos: list[int],
            delegado=None,
            columnas_boton: list[int] = None
    ):
        """
        Configura el estilo visual y comportamiento base de una tabla.

        Args:
            tabla (QTableWidget): La instancia de la tabla a configurar.
            headers (list[str]): Lista de títulos para las columnas.
            anchos (list[int]): Lista con el ancho inicial en píxeles para cada columna.
            delegado (QStyledItemDelegate, optional): Delegado para la columna 0 (Legacy).
            columnas_boton (list[int], optional): Índices de columnas que contienen botones interactivos.
                Estas columnas se configurarán como fijas y mostrarán cursor de mano.
        """
        try:
            # 1. Normalización de argumentos para compatibilidad
            cols_activas = columnas_boton if columnas_boton is not None else []

            # Si se pasa un delegado legacy (solo col 0), lo añadimos a la lógica nueva
            if delegado:
                tabla.setItemDelegateForColumn(0, delegado)
                if 0 not in cols_activas:
                    cols_activas.append(0)

            # 2. Configuración Visual Base
            tabla.setColumnCount(len(headers))
            tabla.setHorizontalHeaderLabels(headers)

            tabla.verticalHeader().setVisible(False)
            tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            tabla.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            tabla.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            tabla.setAlternatingRowColors(False)

            # 🔹 Permitir expansión en el layout
            tabla.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            tabla.setSizeAdjustPolicy(QAbstractItemView.SizeAdjustPolicy.AdjustIgnored)
            tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

            # 3. Configuración de Cursores para múltiples columnas
            if cols_activas:
                PyQtHelper.habilitar_cursor_boton(tabla, cols_activas)

            # 4. Configuración de Headers (Fixed vs Stretch)
            header = tabla.horizontalHeader()
            header.setStretchLastSection(False)
            header.setMinimumSectionSize(60)

            for col, ancho in enumerate(anchos):
                # Si la columna está en la lista de botones, es FIJA. Si no, es ELÁSTICA.
                if col in cols_activas:
                    header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
                    header.resizeSection(col, ancho)
                else:
                    header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

            tabla.verticalHeader().setDefaultSectionSize(42)

        except Exception as e:
            print(f"Error configurando tabla: {e}")

    # -------------------------------------------------
    # CARGA DE DATOS
    # -------------------------------------------------
    @staticmethod
    def cargar_datos_en_tabla(
            tabla: QTableWidget,
            filas: list[list],
            id_column: int = 0,
            alineacion: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    ):
        """
        Limpia e inserta un conjunto de datos en la tabla.

        Args:
            tabla (QTableWidget): La tabla donde se cargarán los datos.
            filas (list[list]): Lista de filas, donde cada fila es una lista de valores.
            id_column (int, optional): Índice de la columna en 'filas' que contiene el ID único.
                Este ID se guarda como UserRole en el ítem de esa columna. Por defecto es 0.
            alineacion (Qt.AlignmentFlag, optional): Alineación del texto en las celdas.
        """
        try:
            tabla.setUpdatesEnabled(False)
            tabla.setRowCount(0)

            for row_idx, fila in enumerate(filas):
                tabla.insertRow(row_idx)

                for col_idx, valor in enumerate(fila):
                    item = QTableWidgetItem("" if valor is None else str(valor))
                    item.setTextAlignment(alineacion)

                    # Guardar ID solo en la columna indicada (generalmente la 0, oculta o botón)
                    # Pero en algunos casos el ID viene en la data aunque no se muestre
                    if id_column is not None and col_idx == id_column:
                        item.setData(Qt.ItemDataRole.UserRole, fila[id_column])

                    tabla.setItem(row_idx, col_idx, item)

            tabla.setUpdatesEnabled(True)
        except Exception as e:
            print(e)

    @staticmethod
    def habilitar_cursor_boton(tabla: QTableWidget, columnas_boton: list[int]):
        """
        Instala un filtro de eventos para cambiar el cursor a mano (PointingHand)
        cuando el mouse pasa sobre columnas específicas.

        Args:
            tabla (QTableWidget): La tabla objetivo.
            columnas_boton (list[int]): Lista de índices de columnas interactivas.
        """
        tabla.setMouseTracking(True)
        tabla.viewport().setMouseTracking(True)

        class _FiltroCursor(QObject):
            def __init__(self, target, cols):
                super().__init__(target)
                self.cols = cols

            def eventFilter(self, obj, event):
                if obj == tabla.viewport():
                    if event.type() == QEvent.Type.MouseMove:
                        index = tabla.indexAt(event.pos())
                        # Verifica si la columna actual está en la lista de columnas permitidas
                        if index.isValid() and index.column() in self.cols:
                            tabla.setCursor(Qt.CursorShape.PointingHandCursor)
                        else:
                            tabla.setCursor(Qt.CursorShape.ArrowCursor)

                    elif event.type() == QEvent.Type.Leave:
                        tabla.setCursor(Qt.CursorShape.ArrowCursor)

                return False

        # Instanciamos pasando la lista de columnas
        filtro = _FiltroCursor(tabla, columnas_boton)
        tabla.viewport().installEventFilter(filtro)

        # 🔒 Mantener referencia viva para evitar Garbage Collection
        if not hasattr(tabla, "_cursor_filters"):
            tabla._cursor_filters = []
        tabla._cursor_filters.append(filtro)


# -------------------------------------------------
# PAGINACIÓN UI
# -------------------------------------------------
def actualizar_paginacion_ui(
        pagina_actual,
        total_paginas,
        total_registros,
        lbl_registros: QLabel = None,
        lbl_contador: QLabel = None,
        btn_before: QPushButton = None,
        btn_after: QPushButton = None
):
    """
    Actualiza el estado visual de los controles de paginación.

    Args:
        pagina_actual (int): Número de la página actual (base 1).
        total_paginas (int): Cantidad total de páginas disponibles.
        total_registros (int): Cantidad total de registros.
        lbl_registros (QLabel, optional): Etiqueta para mostrar el total de registros.
        lbl_contador (QLabel, optional): Etiqueta para mostrar "Página X de Y".
        btn_before (QPushButton, optional): Botón de "Anterior" (se deshabilita si es pag 1).
        btn_after (QPushButton, optional): Botón de "Siguiente" (se deshabilita si es la última).
    """

    if lbl_registros:
        lbl_registros.setText(f"Total registros: {total_registros}")

    if lbl_contador:
        lbl_contador.setText(f"Página {pagina_actual} de {total_paginas}")

    if btn_before:
        btn_before.setEnabled(pagina_actual > 1)

    if btn_after:
        btn_after.setEnabled(pagina_actual < total_paginas)