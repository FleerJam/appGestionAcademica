#  Copyright (c) 2026 Fleer
import os
import sys
from dotenv import load_dotenv, set_key

# 1. DETERMINAR RUTAS BASE
if getattr(sys, 'frozen', False):
    # Si es .exe, BASE_DIR será la carpeta del ejecutable
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Si es Python normal, la carpeta del script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENV_PATH = os.path.join(BASE_DIR, '.env')
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

def actualizar_env(clave, valor):
    """Actualiza o crea una variable de entorno en el archivo .env.

    Se utiliza para persistir configuraciones de usuario como credenciales de BD
    o rutas de carpetas.

    Args:
        clave (str): Nombre de la variable de entorno.
        valor (str): Valor a asignar.
    """
    if not os.path.exists(ENV_PATH):
        with open(ENV_PATH, 'w') as f: f.write("")
    set_key(ENV_PATH, clave, str(valor))

# 2. CONFIGURACIÓN DE BASE DE DATOS
DB_TYPE = os.getenv("DB_TYPE", "sqlite")
DB_NAME = os.getenv("DB_NAME", "academia.db")

if DB_TYPE == "sqlite":
    db_path = os.path.join(BASE_DIR, DB_NAME)
    DATABASE_URL = f"sqlite:///{db_path}"
else:
    _user = os.getenv("DB_USER")
    _pass = os.getenv("DB_PASS")
    _host = os.getenv("DB_HOST")
    _name = os.getenv("DB_NAME_REMOTE")
    _port = os.getenv("DB_PORT", "5432")

    if not all([_user, _pass, _host, _name]):
        fallback_path = os.path.join(BASE_DIR, 'temp_fallback.db')
        DATABASE_URL = f"sqlite:///{fallback_path}"
    else:
        DATABASE_URL = f"postgresql://{_user}:{_pass}@{_host}:{_port}/{_name}"

# 3. RUTAS DE ASSETS, ESTILOS Y CARPETA COMPARTIDA
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
STYLES_DIR = os.path.join(BASE_DIR, 'views')
CSS_FILE = os.path.join(STYLES_DIR, 'styles.css')

# --- NUEVO: RUTA PARA CERTIFICADOS FIRMADOS (NUBE/RED) ---
# Si no hay ruta en el .env, usa una carpeta local por defecto
DEFAULT_SHARED_DIR = os.path.join(ASSETS_DIR, 'certificados_firmados')
SHARED_FOLDER_PATH = os.getenv("SHARED_FOLDER_PATH", DEFAULT_SHARED_DIR)

# 4. CONFIGURACIÓN VISUAL (UI)
THEME_XML = 'light_blue.xml'
FONT_FAMILY = 'Roboto'
APP_TITLE = "Sistema de Gestión Académica"