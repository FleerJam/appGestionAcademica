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
from database.models import Calificacion

class CalificacionModel(BaseCRUDModel):
    """Modelo CRUD para la gestión de calificaciones individuales."""
    model = Calificacion

    def get_by_matricula(self, matricula_id: str):
        """Devuelve todas las calificaciones asociadas a una matrícula específica.

        Args:
            matricula_id (str): ID de la matrícula.

        Returns:
            list: Lista de objetos Calificacion encontrados.
        """
        """Devuelve todas las calificaciones de una matrícula."""
        return self.search(filters={"matricula_id": matricula_id})

    def get_actividades(self, matricula_id: str):
        """Obtiene los identificadores o nombres de las actividades calificadas.

        Args:
            matricula_id (str): ID de la matrícula.

        Returns:
            list: Lista de nombres/identificadores de actividades presentes.
        """
        """Devuelve solo los nombres de las actividades (módulos) de una matrícula."""
        calificaciones = self.get_by_matricula(matricula_id)
        return [c.actividad for c in calificaciones]

    def actualizar_calificacion(self, matricula_id: str, actividad: str, puntaje: float):
        """Actualiza el puntaje de una actividad existente o crea una nueva si no existe.

        Args:
            matricula_id (str): ID de la matrícula.
            actividad (str): Identificador de la actividad/módulo.
            puntaje (float): Nota a registrar.

        Returns:
            object: Instancia de Calificacion creada o actualizada.
        """
        """Actualiza o crea una calificación para un módulo específico."""
        calificaciones = self.search(filters={"matricula_id": matricula_id, "actividad": actividad}, first=True)
        if calificaciones:
            return self.update(calificaciones.id, {"puntaje": puntaje})
        else:
            return self.create({"matricula_id": matricula_id, "actividad": actividad, "puntaje": puntaje})

    def calcular_nota_final(self, matricula_id: str):
        """Calcula el promedio aritmético simple de las calificaciones registradas.

        Args:
            matricula_id (str): ID de la matrícula.

        Returns:
            float: Promedio calculado redondeado a 2 decimales, o 0.0 si no hay notas.
        """
        """Calcula la nota final promedio de una matrícula."""
        calificaciones = self.get_by_matricula(matricula_id)
        if not calificaciones:
            return 0.0
        total = sum(c.puntaje for c in calificaciones)
        return round(total / len(calificaciones), 2)