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

from sqlalchemy import inspect, event
from sqlalchemy.engine import Engine

from database.conexion import engine, Base, SessionLocal
from database.models import Centro, TipoCertificado

# Lista por defecto movida aquí. Solo se usa para la primera inicialización.
TIPOS_CERTIFICADO_DEFAULT = [
    "APROBACION",
    "PARTICIPACION",
    "RECONOCIMIENTO",
    "VINCULACION"
]


# -------------------------------------------------
# SQLite: activar ON DELETE CASCADE
# -------------------------------------------------
@event.listens_for(Engine, "connect")
def activar_foreign_keys_sqlite(dbapi_connection, connection_record):
    """
    SOLUCIÓN: Validar que el conector activo sea 'sqlite3'
    antes de enviarle el comando PRAGMA. Si es PostgreSQL, se omite.
    """
    if dbapi_connection.__class__.__module__ == "sqlite3":
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        except Exception:
            pass


def inicializar_base_de_datos():
    """
    Crea la estructura de la base de datos si no existe
    y carga datos iniciales (Centros, Tipos de Certificado).

    Verifica la existencia de tablas mediante inspección y si están vacías,
    ejecuta rutinas de población inicial.
    """
    print(f"🔄 Inicializando base de datos ({engine.dialect.name})...")

    # 1. Crear tablas
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Estructura de tablas verificada/creada.")
    except Exception as e:
        print(f"❌ Error crítico creando tablas: {e}")
        return

    # 2. Población inicial
    session = SessionLocal()
    try:
        inspector = inspect(engine)

        # Centros
        if inspector.has_table("centros"):
            if session.query(Centro).count() == 0:
                print("ℹ️ Insertando centros iniciales...")
                try:
                    from database.centros import insertar_centros
                    insertar_centros(session)
                    print("✅ Centros insertados.")
                except ImportError:
                    print("⚠️ No se encontró la rutina de inserción de centros.")

        # Tipos de certificado
        if inspector.has_table("tipos_certificado"):
            if session.query(TipoCertificado).count() == 0:
                print("ℹ️ Insertando tipos de certificado por defecto...")
                for nombre in TIPOS_CERTIFICADO_DEFAULT:
                    session.add(TipoCertificado(nombre=nombre))

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"❌ Error inicializando datos: {e}")
    finally:
        session.close()