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

from database.models import CedulaAlias
from database.base_model import BaseCRUDModel

class CedulaAliasModel(BaseCRUDModel):
    """Modelo CRUD para gestionar alias o variantes de cédulas de identidad.

    Permite mapear múltiples entradas de identificación incorrectas o variantes
    a un único registro de persona válido.
    """
    model = CedulaAlias