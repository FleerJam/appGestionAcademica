#  Copyright (c) 2026 Fleer
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import DATABASE_URL  # <--- Importamos desde config

# Crear Engine
# echo=True solo si quieres ver el SQL en consola
engine = create_engine(DATABASE_URL, echo=False)

# --- CORRECCIÓN ---
# Escuchamos el evento en TODOS los motores, pero validamos dentro
# si la conexión específica es SQLite antes de ejecutar el comando.
@event.listens_for(Engine, "connect")
def activar_foreign_keys_sqlite(dbapi_connection, connection_record):
    """Activa el soporte de claves foráneas (Foreign Keys) para conexiones SQLite.

    SQLAlchemy no habilita esto por defecto en SQLite. Se ejecuta automáticamente
    al conectar si el driver es 'sqlite3'.

    Args:
        dbapi_connection: La conexión cruda de la DBAPI.
        connection_record: El registro de contexto de la conexión.
    """
    # Verificamos si el módulo de la conexión es sqlite3
    if "sqlite3" in str(dbapi_connection.__class__.__module__):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        except Exception:
            # Si por alguna razón falla o no es SQLite, ignoramos el error
            pass
        finally:
            cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()