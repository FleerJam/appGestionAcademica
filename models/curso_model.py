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

from datetime import date

from database.base_model import BaseCRUDModel
from database.models import Curso, Matricula
from database.conexion import SessionLocal  # Asumiendo que BaseCRUDModel usa SessionLocal

class CursoModel(BaseCRUDModel):
    """Modelo CRUD para la gestión de Cursos y capacitaciones."""
    model = Curso

    @staticmethod
    def cursos_activos_count():
        """Cuenta el número total de cursos que aún no han finalizado.

        Returns:
            int: Cantidad de cursos con fecha_final mayor a la fecha actual.
        """
        """
        Retorna la cantidad de cursos cuya fecha final es mayor a hoy.
        """
        session = SessionLocal()
        try:
            hoy = date.today()
            count = session.query(Curso).filter(Curso.fecha_final > hoy).count()

            return count
        finally:
            session.close()

    @staticmethod
    def estudiantes_inscritos(curso_id):
        """Cuenta el número de estudiantes matriculados en un curso específico.

        Args:
            curso_id (int): ID del curso.

        Returns:
            int: Cantidad de registros en la tabla de matrículas para este curso.
        """
        """
        Retorna la cantidad de estudiantes inscritos en un curso.
        """
        session = SessionLocal()
        try:
            count = session.query(Matricula).filter(Matricula.curso_id == curso_id).count()
            return count
        finally:
            session.close()

    @staticmethod
    def debug_cursos_activos():
        """Imprime en consola el estado (ACTIVO/NO ACTIVO) de todos los cursos.

        Método de utilidad para depuración que lista nombres y fechas de fin.

        Returns:
            int: Cantidad de cursos activos encontrados.
        """
        """
        Imprime todos los cursos y su fecha_final, además de mostrar cuáles cuentan como activos.
        """
        session = SessionLocal()
        try:
            hoy = date.today()
            cursos = session.query(Curso).all()
            print(f"Hoy: {hoy}\n")
            activos = 0
            for c in cursos:
                print(f"Curso: {c.nombre}, Fecha final: {c.fecha_final}")
                if c.fecha_final > hoy:
                    print(" -> ACTIVO")
                    activos += 1
                else:
                    print(" -> NO ACTIVO")
            print(f"\nCantidad de cursos activos: {activos}")
            return activos
        finally:
            session.close()

    @staticmethod
    def cursos_activos():
        """Recupera la lista de objetos Curso que están vigentes.

        Returns:
            list: Lista de cursos con fecha_final mayor o igual a hoy, ordenados por nombre.
        """
        """
        Retorna los cursos activos ordenados alfabéticamente.
        """
        session = SessionLocal()
        try:
            hoy = date.today()
            cursos = (
                session.query(Curso)
                .filter(Curso.fecha_final >= hoy)
                .order_by(Curso.nombre.asc())
                .all()
            )
            return cursos
        finally:
            session.close()