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

from typing import Optional
from sqlalchemy.exc import SQLAlchemyError
from database.models import Centro


def generar_nombre_centro(tipo: str, ubicacion: str) -> str:
    """Genera el nombre estándar de un centro basado en su tipología y ubicación.

    Args:
        tipo (str): Tipo de centro ('ZONAL', 'LOCAL', 'SALA').
        ubicacion (str): Nombre de la ciudad o ubicación geográfica.

    Returns:
        str: Nombre formateado (ej. "CENTRO ZONAL ECU 911 QUITO").
    """
    """Genera el nombre estándar según el tipo y ubicación."""
    if tipo == "ZONAL":
        return f"CENTRO ZONAL ECU 911 {ubicacion}"
    elif tipo == "LOCAL":
        return f"CENTRO LOCAL ECU 911 {ubicacion}"
    elif tipo == "SALA":
        return f"SALA {ubicacion}"
    return f"CENTRO {ubicacion}"


def insertar_centros(session):
    """Puebla la base de datos con la jerarquía inicial de centros ECU 911.

    Inserta Centros Zonales, luego Centros Locales vinculados a los Zonales,
    y finalmente Salas Operativas vinculadas a sus respectivos padres.

    Args:
        session (Session): Sesión de base de datos activa para realizar las inserciones.

    Raises:
        SQLAlchemyError: Si ocurre un error durante la transacción.
    """
    """Inserta la jerarquía de centros ECU 911 usando la lógica de nombres."""
    print("🌱 Iniciando población de Centros...")

    try:
        # Verificación de seguridad extra por si se llama manualmente
        if session.query(Centro).first():
            print("⚠️ La base de datos ya contiene centros. Abortando población.")
            return

        centros_map = {}

        # 1. ZONALES
        data_zonales = [
            ("UIO", "QUITO"), ("SAM", "SAMBORONDON"), ("CUE", "CUENCA"),
            ("MCH", "MACHALA"), ("AMB", "AMBATO"), ("PTV", "PORTOVIEJO"),
            ("IBA", "IBARRA"),
        ]

        print("   -> Insertando Zonales...")
        centro_padre_id: Optional[str] = None
        # 1. ZONALES
        for siglas, ubicacion in data_zonales:
            nuevo_zonal = Centro(
                nombre=generar_nombre_centro("ZONAL", ubicacion),
                siglas=siglas,
                ubicacion=ubicacion,
                tipo="ZONAL",
                centro_padre_id=centro_padre_id
            )
            session.add(nuevo_zonal)
            session.flush()  # <- esto asegura que nuevo_zonal.id se genere inmediatamente
            centros_map[ubicacion] = nuevo_zonal

        # 2. LOCALES
        data_locales = [
            ("STO", "SANTO DOMINGO", "PORTOVIEJO"), ("ESM", "ESMERALDAS", "IBARRA"),
            ("BBH", "BABAHOYO", "SAMBORONDON"), ("LOJ", "LOJA", "MACHALA"),
            ("RIO", "RIOBAMBA", "AMBATO"), ("MAC", "MACAS", "CUENCA"),
            ("TLC", "TULCAN", "IBARRA"), ("NLO", "NUEVA LOJA", "IBARRA"),
            ("GPS", "GALAPAGOS", "SAMBORONDON")
        ]

        print("   -> Insertando Locales...")
        for siglas, ubicacion, nombre_padre in data_locales:
            padre = centros_map.get(nombre_padre)
            if padre:
                nuevo_local = Centro(
                    nombre=generar_nombre_centro("LOCAL", ubicacion),
                    siglas=siglas,
                    ubicacion=ubicacion,
                    tipo="LOCAL",
                    centro_padre_id=padre.id
                )
                session.add(nuevo_local)
                centros_map[ubicacion] = nuevo_local
        session.flush()

        # 3. SALAS OPERATIVAS
        data_hijos = [
            ("SAZ", "AZOGUES", "CUENCA"), ("SGR", "GUARANDA", "BABAHOYO"),
            ("SCY", "CAYAMBE", "QUITO"), ("SLT", "LATACUNGA", "AMBATO"),
            ("SMT", "MANTA", "PORTOVIEJO"), ("SMJ", "MEJIA", "QUITO"),
            ("STN", "TENA", "QUITO"), ("SOR", "ORELLANA", "QUITO"),
            ("SPY", "PUYO", "AMBATO"), ("SPM", "PEDRO MONCAYO", "QUITO"),
            ("SQV", "QUEVEDO", "BABAHOYO"), ("SRM", "RUMIÑAHUI", "QUITO"),
            ("SSE", "SANTA ELENA", "SAMBORONDON"), ("SZM", "ZAMORA", "LOJA")
        ]

        print("   -> Insertando Salas Operativas...")
        for siglas, ubicacion, nombre_padre in data_hijos:
            padre = centros_map.get(nombre_padre)
            if padre:
                nueva_sala = Centro(
                    nombre=generar_nombre_centro("SALA", ubicacion),
                    siglas=siglas,
                    ubicacion=ubicacion,
                    tipo="SALA",
                    centro_padre_id=padre.id
                )
                session.add(nueva_sala)

        session.commit()
        print("✅ Jerarquía de centros poblada exitosamente.")

    except SQLAlchemyError as e:
        session.rollback()
        print(f"❌ Error BD durante población: {e}")
        raise e