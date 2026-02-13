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

from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtCore import Qt, QSize, QRect, QEvent
from PyQt6.QtGui import QIcon, QMouseEvent


class BotonDetalleDelegate(QStyledItemDelegate):
    """
    Delegado personalizado para renderizar un botón con icono dentro de una celda
    de QTableWidget y manejar sus eventos de clic.
    """

    def __init__(self, callback, icon_path: str, columna: int = 0, parent=None):
        """
        Inicializa el delegado del botón.

        Args:
            callback (callable): Función a ejecutar al hacer clic. Recibe el ID del objeto como argumento.
            icon_path (str): Ruta al archivo de imagen del icono.
            columna (int, optional): Índice de la columna donde se dibujará el botón. Por defecto es 0.
            parent (QObject, optional): Objeto padre.
        """
        super().__init__(parent)
        self.callback = callback
        self.icon = QIcon(icon_path)
        self.columna = columna

    def paint(self, painter, option, index):
        """
        Dibuja el icono centrado en la celda si corresponde a la columna configurada.

        Args:
            painter (QPainter): Objeto pintor para dibujar.
            option (QStyleOptionViewItem): Opciones de estilo de la celda.
            index (QModelIndex): Índice del modelo que se está pintando.
        """
        # Solo pintar si estamos en la columna correcta
        if index.column() != self.columna:
            super().paint(painter, option, index)
            return

        # Dibujar icono centrado
        icon_size = QSize(20, 20)
        padding = 6

        # Ajuste de rectángulo para padding
        rect = option.rect.adjusted(padding, padding, -padding, -padding)

        # Cálculo de posición centrada
        x = rect.x() + (rect.width() - icon_size.width()) // 2
        y = rect.y() + (rect.height() - icon_size.height()) // 2
        icon_rect = QRect(x, y, icon_size.width(), icon_size.height())

        self.icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)

    def editorEvent(self, event, model, option, index):
        """
        Maneja los eventos de usuario, específicamente el clic izquierdo del mouse
        para disparar el callback.

        Args:
            event (QEvent): El evento ocurrido.
            model (QAbstractItemModel): El modelo de datos.
            option (QStyleOptionViewItem): Opciones de estilo.
            index (QModelIndex): Índice donde ocurrió el evento.

        Returns:
            bool: True si el evento fue manejado, False en caso contrario.
        """
        # Detectar clic izquierdo
        if (
                event.type() == QEvent.Type.MouseButtonPress
                and index.column() == self.columna
                and isinstance(event, QMouseEvent)
                and event.button() == Qt.MouseButton.LeftButton
        ):
            # 1. Intentar obtener ID de la columna actual
            objeto_id = index.data(Qt.ItemDataRole.UserRole)

            # 2. Si es None (porque el Helper solo guarda IDs en col 0), buscar en la columna 0
            if objeto_id is None:
                objeto_id = index.sibling(index.row(), 0).data(Qt.ItemDataRole.UserRole)

            # Ejecutar acción si encontramos un ID válido
            if objeto_id is not None:
                self.callback(objeto_id)
            return True

        return False