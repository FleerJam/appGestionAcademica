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

import unicodedata
from database.conexion import SessionLocal
from database.models import Centro
from database.base_model import BaseCRUDModel

class CentroModel(BaseCRUDModel):
    """Modelo CRUD para la gestión de Centros (Zonales, Locales, Salas)."""
    model = Centro

    @staticmethod
    def parsear_centro(texto: str) -> dict:
        """Analiza una cadena de texto para extraer el tipo y ubicación del centro.

        Normaliza el texto eliminando acentos y estandarizando prefijos conocidos
        (Zonal, Local, Sala) para determinar la clasificación correcta.

        Args:
            texto (str): Nombre crudo del centro.

        Returns:
            dict: Diccionario con claves 'tipo' y 'ubicacion'.
        """
        if not texto:
            return {"tipo": "DESCONOCIDO", "ubicacion": "DESCONOCIDO"}

        s = texto.replace("ñ", "\001").replace("Ñ", "\002")
        s = unicodedata.normalize('NFD', s)
        s = "".join(c for c in s if unicodedata.category(c) != 'Mn')
        t = s.replace("\001", "ñ").replace("\002", "Ñ").strip().upper()

        tipo, ubicacion = "LOCAL", t  # default

        if t.startswith("CENTRO ZONAL"):
            tipo = "ZONAL"
            ubicacion = t.replace("CENTRO ZONAL ECU 911", "").strip()
        elif t.startswith("CENTRO LOCAL"):
            tipo = "LOCAL"
            ubicacion = t.replace("CENTRO LOCAL ECU 911", "").strip()
        elif t.startswith("SALA"):
            tipo = "SALA"
            ubicacion = t.replace("SALA", "").strip()

        # renombrar casos especiales
        renombrar_ubicacion = {"SAN CRISTOBAL": "GALAPAGOS"}
        ubicacion = renombrar_ubicacion.get(ubicacion, ubicacion)

        return {"tipo": tipo, "ubicacion": ubicacion}

    @staticmethod
    def texto_desde_id(centro_id: int) -> str:
        """Obtiene el nombre completo formateado de un centro dado su ID.

        Args:
            centro_id (int): ID único del centro.

        Returns:
            str: Nombre completo (ej. "CENTRO ZONAL ECU 911 QUITO") o cadena vacía.
        """
        session = SessionLocal()
        try:
            centro = session.query(Centro).filter_by(id=centro_id).first()

            if not centro:
                return ""

            # Normalizamos lo que viene de la BD por si acaso
            tipo = centro.tipo.upper()
            ubicacion = centro.ubicacion.upper().strip()

            if tipo == "ZONAL":
                return f"CENTRO ZONAL ECU 911 {ubicacion}"

            elif tipo == "LOCAL":
                return f"CENTRO LOCAL ECU 911 {ubicacion}"

            elif tipo == "SALA":
                return f"SALA {ubicacion}"

            return ubicacion

        finally:
            session.close()