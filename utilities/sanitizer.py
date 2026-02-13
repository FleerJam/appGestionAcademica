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
import pandas as pd
from typing import Any

class Sanitizer:
    """Clase utilitaria estática para limpieza y validación de datos."""

    @staticmethod
    def limpiar_texto(texto: Any) -> str:
        """
        Normaliza texto eliminando acentos y caracteres especiales, manteniendo la Ñ.
        Convierte a mayúsculas.

        Args:
            texto (Any): Texto de entrada.

        Returns:
            str: Texto limpio y en mayúsculas.
        """
        if pd.isna(texto) or str(texto).strip() == "":
            return ""

        txt = str(texto).strip()
        # Protección de la Ñ
        txt = txt.replace("ñ", "__ENYE__").replace("Ñ", "__ENYE_MAYUS__")

        # Normalización unicode (eliminar tildes)
        txt = unicodedata.normalize("NFD", txt)
        txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")

        # Restauración de la Ñ y mayúsculas
        txt = txt.replace("__ENYE__", "ñ").replace("__ENYE_MAYUS__", "Ñ")
        return txt.upper()
    @staticmethod
    def casi_limpio(texto: Any) -> str:
        """
        Normaliza texto eliminando acentos y caracteres especiales,
        manteniendo la Ñ y forzando mayúsculas.

        Args:
            texto (Any): Texto de entrada.

        Returns:
            str: Texto limpio.
        """
        if pd.isna(texto) or str(texto).strip() == "":
            return ""

        txt = str(texto)

        # Proteger la Ñ
        txt = txt.replace("ñ", "__ENYE__").replace("Ñ", "__ENYE_MAYUS__")

        # Normalización unicode (elimina tildes)
        txt = unicodedata.normalize("NFD", txt)
        txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")

        # Restaurar Ñ y forzar mayúsculas
        txt = txt.replace("__ENYE__", "ñ").replace("__ENYE_MAYUS__", "Ñ")

        return txt.upper()
    @staticmethod
    def limpiar_cedula(valor: Any) -> str:
        """
        Limpia puntos, guiones y espacios de una cédula.
        Maneja valores float (ej: 17123.0) convirtiéndolos correctamente.

        Args:
            valor (Any): Valor de entrada.

        Returns:
            str: Cadena numérica limpia.
        """
        if pd.isna(valor):
            return ""
        c = str(valor).strip().replace('.0', '')
        return c.replace('-', '').replace('.', '').replace(',', '')

    @staticmethod
    def limpiar_nota(valor: Any) -> float:
        """
        Convierte un valor de Excel a float, manejando comas decimales
        y valores no numéricos.

        Args:
            valor (Any): Valor de entrada (str, float, int).

        Returns:
            float: Valor numérico o 0.0 si es inválido.
        """
        if pd.isna(valor): return 0.0
        s_val = str(valor).strip().replace(',', '.')
        if s_val in ["-", "", "nan", "None"]: return 0.0
        try:
            return float(s_val)
        except ValueError:
            return 0.0

    @staticmethod
    def validar_cedula_ecuador(cedula: str) -> bool:
        """
        Valida si una cédula ecuatoriana es válida usando el algoritmo de Módulo 10.

        Args:
            cedula (str): Cédula de 10 dígitos.

        Returns:
            bool: True si es válida, False en caso contrario.
        """
        if not cedula.isdigit() or len(cedula) != 10:
            return False

        # 2. Validar código de provincia (01 al 24, o 30)
        provincia = int(cedula[0:2])
        if not (1 <= provincia <= 24 or provincia == 30):
            return False

        # 4. Algoritmo Módulo 10
        total = 0
        coeficientes = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        for i in range(9):
            valor = int(cedula[i]) * coeficientes[i]
            if valor >= 10:
                valor -= 9
            total += valor

        digito_verificador = int(cedula[9])
        residuo = total % 10
        esperado = 0 if residuo == 0 else 10 - residuo

        return digito_verificador == esperado