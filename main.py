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

import sys
import os
import ctypes # Para forzar el icono en la barra de tareas de Windows
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon  # Importación necesaria
from qt_material import apply_stylesheet
from PyQt6.QtCore import QTranslator, QLibraryInfo, QTimer
from controllers.master import MasterController
from database.setup import inicializar_base_de_datos
from models.matricula_model import MatriculaModel
import database.config as config

# Configuración de rutas para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.platform == "win32":
    myappid = 'dnae.matriculas.v1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# --- 2. Función para manejar rutas internas del ejecutable ---
def resource_path(relative_path):
    """ Obtiene la ruta absoluta para recursos, compatible con PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def main():
    """
    Punto de entrada principal de la aplicación.

    Realiza la secuencia de arranque completa:
    1. Inicializa la conexión y estructura de la base de datos.
    2. Ejecuta tareas de mantenimiento de datos (actualización de estados de matrículas).
    3. Configura la instancia de QApplication y carga las traducciones al español.
    4. Aplica el tema visual (qt_material) y las hojas de estilo CSS personalizadas definidas en la configuración.
    5. Instancia y muestra la ventana principal (MasterController).
    6. Inicia el bucle de eventos de la interfaz gráfica.
    """
    inicializar_base_de_datos()
    MatriculaModel().actualizar_estados_matriculas()
    app = QApplication(sys.argv)
    translator = QTranslator()
    translator.load(
        "qt_es",
        QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    )
    app.installTranslator(translator)

    icon_path = resource_path(os.path.join("assets", "icons", "logo_app.ico"))
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)

    apply_stylesheet(
        app,
        theme=config.THEME_XML,  # <--- Desde config
        invert_secondary=True,
        css_file=config.CSS_FILE,  # <--- Desde config
        extra={'font_family': config.FONT_FAMILY}  # <--- Desde config
    )

    window = MasterController()
    window.setWindowTitle(config.APP_TITLE)
    window.setMinimumSize(0, 0)  # Elimina restricciones mínimas
    window.setMaximumSize(16777215, 16777215)  # Valor máximo permitido por Qt

    QTimer.singleShot(100, window.showMaximized)

    # Ejecutar loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()