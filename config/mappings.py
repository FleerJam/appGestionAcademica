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

"""Configuración de mapeos y constantes para el procesamiento de datos.

Este módulo define las estructuras de datos estáticas utilizadas para la
normalización de columnas de Excel, validación de campos obligatorios y
corrección de nombres de centros.
"""

# Mapeo de columnas esperadas en el Excel y sus posibles alias
COLUMNA_ALIAS = {
    'cedula': ['CEDULA', 'IDENTIFICACION', 'DNI', 'ID_PERSONA', 'USUARIO', 'CEDULA DE IDENTIDAD'],
    'nombre': ['NOMBRE', 'NOMBRES', 'PRIMER NOMBRE'],
    'apellido': ['APELLIDO', 'APELLIDOS', 'PATERNO', 'APELLIDO(S)'],
    'correo': ['CORREO', 'EMAIL', 'MAIL', 'E-MAIL'],
    'centro': ['CENTRO', 'UBICACION', 'LUGAR', 'SEDE'],
    'institucion_articulada': ['INSTITUCION', 'INSTITUCION ARTICULADA']
}
"""dict: Diccionario que asocia nombres de columnas normalizados con sus posibles alias.

Las claves representan el nombre interno utilizado en el sistema, y los valores
son listas de cadenas con los posibles encabezados que pueden aparecer en los
archivos de entrada.
"""

# Columnas que son obligatorias para procesar
COLUMNAS_OBLIGATORIAS = ['cedula', 'nombre', 'apellido', 'correo', 'centro']
"""list: Lista de identificadores de columnas requeridas.

Define los campos que deben estar presentes obligatoriamente en el conjunto de
datos para que el procesamiento continúe sin errores.
"""

# Correcciones automáticas de nombres de centros
CORRECCIONES_CENTROS = {
    "CENTRO LOCAL ECU 911 SAN CRISTOBAL": "CENTRO LOCAL ECU 911 GALAPAGOS",
    "PLANTA CENTRAL": "CENTRO ZONAL ECU 911 QUITO",
    "CIUDADANO": "CENTRO ZONAL ECU 911 QUITO"
}
"""dict: Mapeo para la corrección y estandarización de nombres de centros.

Se utiliza para reemplazar nombres de centros inconsistentes o antiguos (claves)
por sus denominaciones oficiales estandarizadas (valores).
"""