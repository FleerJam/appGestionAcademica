Sistema de Gestión Académica y Certificación (Código Abierto)

Bienvenido al repositorio del software de gestión de capacitaciones. Este proyecto está diseñado para ser flexible, modular y fácil de adaptar. Si eres desarrollador o deseas implementar este sistema en tu organización, esta guía te ayudará a configurar el entorno y entender sus capacidades.

1. Configuración del Entorno de Desarrollo

Este sistema está desarrollado en Python y utiliza PyQt/PySide para la interfaz gráfica y SQLAlchemy para la gestión de la base de datos.

Pasos para empezar:

Clonación del Repositorio: ```bash
git clone https://github.com/tu-usuario/nombre-del-repo.git
cd nombre-del-repo




Creación de Entorno Virtual: Se recomienda el uso de un entorno virtual para gestionar las dependencias:

python -m venv venv
source venv/bin/scripts/activate  # En Windows: venv\Scripts\activate


Instalación de Dependencias: Instale las librerías necesarias mediante el archivo de requerimientos:

pip install -r requirements.txt


Configuración de la Base de Datos: El sistema es compatible con SQLite (por defecto para pruebas), PostgreSQL y MySQL. Puede ajustar la cadena de conexión en el archivo de configuración correspondiente o mediante la interfaz.

2. Estructura del Proyecto

Para facilitar la modificación del código, el proyecto se divide en:

/controllers: Contiene la lógica de control que conecta la UI con los datos.

/models: Definición de la lógica de negocio y cálculos académicos.

/database: Esquemas de SQLAlchemy, modelos de tablas y migraciones.

/utilities: Clases transversales para sanitización, importación de Excel y validación de documentos.

/views o archivos .ui: Archivos de diseño de la interfaz gráfica.

3. Funcionalidades Principales

El sistema ofrece una base sólida que puede ser extendida según sus necesidades:

Gestión Académica y de Datos

Validación de Identidad: Módulo de validación de cédulas (Ecuador) fácilmente adaptable a otros países en utilities/sanitizer.py.

Motor de Importación: Lógica basada en Pandas para procesar archivos Excel con mapeo dinámico de columnas.

Sanitización de Datos: Limpieza automática de cadenas de texto y normalización de formatos.

Generación y Firma de Documentos

Motor Word a PDF: Utiliza plantillas de Word con etiquetas dinámicas {} para generar certificados masivos.

Módulo de Firma Digital: Flujo de trabajo diseñado para integrar firmas electrónicas externas (compatibles con FirmaEC) y vinculación automática mediante metadatos de archivos.

4. Compilación y Distribución

Si desea generar un ejecutable final tras realizar sus cambios, el proyecto es compatible con:

Nuitka: (Recomendado para optimización y protección de código).

PyInstaller: Para empaquetado rápido.

5. Contribuciones y Modificaciones

Este proyecto es de código abierto. Si desea contribuir:

Realice un Fork del proyecto.

Cree una rama para su funcionalidad (git checkout -b feature/NuevaMejora).

Realice un Pull Request para revisión.

6. Requisitos del Sistema (Desarrollo)

Lenguaje: Python 3.9 o superior.

Interfaz: PyQt6 o PySide6.

Base de Datos: SQLite, MySQL o PostgreSQL.

Herramientas de Diseño: Qt Designer (opcional para editar archivos .ui).
