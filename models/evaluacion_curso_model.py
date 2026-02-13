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
from database.models import EvaluacionCurso
from database.base_model import BaseCRUDModel
from typing import List, Dict

class EvaluacionCursoModel(BaseCRUDModel):
    """Modelo CRUD para gestionar las definiciones de evaluaciones de un curso."""
    """CRUD para la tabla Persona."""
    model = EvaluacionCurso


    def delete_by_curso(self, curso_id: int):
        """Elimina todas las evaluaciones asociadas a un curso.

        Se utiliza antes de actualizar la estructura de evaluación para evitar
        duplicados o inconsistencias.

        Args:
            curso_id (int): ID del curso.
        """
        """
        Elimina todas las evaluaciones configuradas para un curso específico.
        Útil para reiniciar la configuración de evaluaciones antes de guardar una nueva.
        """
        with self._get_session() as session:
            # Elimina todos los registros que coincidan con el curso_id
            session.query(self.model).filter_by(curso_id=curso_id).delete()
            session.commit()

    def get_by_curso(self, curso_id: int):
        """Obtiene las evaluaciones configuradas para un curso, ordenadas por secuencia.

        Args:
            curso_id (int): ID del curso.

        Returns:
            list: Lista de objetos EvaluacionCurso.
        """
        """
        Obtiene todas las evaluaciones de un curso ordenadas por su campo 'orden'.
        """
        return self.search(filters={"curso_id": curso_id}, order_by="orden")

    def obtener_esquema_curso(self, curso_id: int) -> List[Dict]:
        """Recupera la estructura simplificada de evaluaciones para lógica de negocio.

        Args:
            curso_id (int): ID del curso.

        Returns:
            List[Dict]: Lista de diccionarios con keys 'id', 'nombre', 'porcentaje'.
        """
        """
        Retorna una lista de diccionarios con la estructura de evaluación del curso.
        Ej: [{'id': 'uuid', 'nombre': 'Examen', 'porcentaje': 40.0}]
        """
        try:
            # Reutilizamos el método existente que ya ordena y filtra correctamente
            # Esto es más seguro y consistente con BaseCRUDModel que usar sesiones crudas
            resultados = self.get_by_curso(curso_id)

            esquema = []
            for ev in resultados:
                esquema.append({
                    'id': ev.id,
                    'nombre': ev.nombre,
                    'porcentaje': ev.porcentaje
                })
            return esquema
        except Exception as e:
            print(f"Error obteniendo esquema: {e}")
            return []