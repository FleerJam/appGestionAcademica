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
from database.base_model import BaseCRUDModel
from database.models import PlantillaCertificado



class PlantillaCertificadoModel(BaseCRUDModel):
    """Modelo CRUD para gestionar las plantillas de diseño de certificados.

    Permite almacenar y recuperar configuraciones JSON o archivos binarios Word
    utilizados para la generación de diplomas.
    """
    model = PlantillaCertificado