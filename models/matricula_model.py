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

from datetime import date, datetime
from sqlalchemy import or_, cast, String
from sqlalchemy.orm import joinedload
from database.base_model import BaseCRUDModel
from database.models import Matricula, Persona, Curso
from database.conexion import SessionLocal


class MatriculaModel(BaseCRUDModel):
    """Modelo CRUD con lógica de negocio para la gestión de matrículas y estados académicos."""
    model = Matricula

    @staticmethod
    def _construir_query_base(session, filters=None, or_fields=None):
        """Construye una consulta SQLAlchemy optimizada con Eager Loading.

        Carga anticipadamente las relaciones Persona, Curso, Calificaciones y Centro
        para evitar problemas de sesión (DetachedInstanceError) en la UI. Aplica
        filtros exactos y búsquedas parciales.

        Args:
            session (Session): Sesión activa de base de datos.
            filters (dict, optional): Filtros exactos.
            or_fields (list, optional): Filtros para búsqueda OR.

        Returns:
            Query: Objeto Query configurado.
        """
        # Se agrega joinedload(Matricula.centro) para evitar DetachedInstanceError
        query = session.query(Matricula) \
            .join(Matricula.persona) \
            .options(
            joinedload(Matricula.persona),
            joinedload(Matricula.curso),
            joinedload(Matricula.calificaciones),
            joinedload(Matricula.centro)
        )

        if filters:
            for field, value in filters.items():
                if value is None:
                    continue
                if hasattr(Matricula, field):
                    query = query.filter(getattr(Matricula, field) == value)
                elif field == 'persona_cedula':
                    query = query.filter(Persona.cedula == value)

        if or_fields:
            or_conditions = []
            for field, value in or_fields:
                if field == 'persona_nombre':
                    or_conditions.append(Persona.nombre.ilike(f"%{value}%"))
                elif field == 'persona_institucion_articulada':
                    or_conditions.append(Persona.institucion_articulada.ilike(f"%{value}%"))
                elif field == 'persona_cedula':
                    or_conditions.append(Persona.cedula.ilike(f"%{value}%"))
                elif hasattr(Matricula, field):
                    col = getattr(Matricula, field)
                    or_conditions.append(cast(col, String).ilike(f"%{value}%"))
            if or_conditions:
                query = query.filter(or_(*or_conditions))

        return query

    def count(self, filters=None, or_fields=None, partial_match=False):
        """Cuenta las matrículas que coinciden con los criterios de búsqueda.

        Args:
            filters (dict, optional): Filtros exactos.
            or_fields (list, optional): Filtros parciales.
            partial_match (bool): (No utilizado actualmente, mantenido por compatibilidad).

        Returns:
            int: Número de registros.
        """
        session = SessionLocal()
        try:
            query = self._construir_query_base(session, filters, or_fields)
            return query.count()
        finally:
            session.close()

    def search(self, filters=None, order_by=None, limit=None, offset=None, first=False, or_fields=None,
               partial_match=False):
        """Busca matrículas con soporte avanzado de filtrado, ordenamiento y paginación.

        Args:
            filters (dict, optional): Filtros exactos.
            order_by (str, optional): Campo para ordenar (soporta 'persona_nombre').
            limit (int, optional): Límite de resultados.
            offset (int, optional): Desplazamiento.
            first (bool): Si True, retorna solo el primer resultado.
            or_fields (list): Campos para búsqueda OR.
            partial_match (bool): (No utilizado).

        Returns:
            list | Matricula: Lista de resultados o una instancia única.
        """
        session = SessionLocal()
        try:
            query = self._construir_query_base(session, filters, or_fields)

            if order_by == 'persona_nombre':
                query = query.order_by(Persona.nombre)
            elif order_by and isinstance(order_by, str) and hasattr(Matricula, order_by):
                query = query.order_by(getattr(Matricula, order_by))
            else:
                query = query.order_by(Matricula.id.desc())

            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)

            return query.first() if first else query.all()
        finally:
            session.close()

    # =========================================================================
    #  LÓGICA DE NEGOCIO CENTRALIZADA
    # =========================================================================

    def determinar_estado(self, nota_final, curso_obj, es_abandono=False):
        """Determina el estado académico de una matrícula según reglas de negocio.

        Reglas:
        1. NO REALIZO: Abandono explícito o curso cerrado con nota 0.
        2. APROBADO: Nota >= nota de aprobación del curso.
        3. REPROBADO: Curso cerrado y nota insuficiente.
        4. EN CURSO: Curso vigente y nota insuficiente.

        Args:
            nota_final (float): Calificación final del estudiante.
            curso_obj (Curso): Objeto del curso con fechas y nota mínima.
            es_abandono (bool): Flag manual para indicar deserción.

        Returns:
            str: Estado calculado ('APROBADO', 'REPROBADO', 'EN CURSO', 'NO REALIZO').
        """
        """
        Calcula el estado basándose en las 4 REGLAS principales.
        1. NO REALIZO: Abandono explicito o Curso Cerrado con nota 0.
        2. APROBADO: Nota >= Aprobación (Gana a las fechas).
        3. REPROBADO: Curso Cerrado y Nota insuficiente.
        4. EN CURSO: Curso Abierto y Nota insuficiente.
        """
        # --- REGLA 1: Abandono Manual ---
        if es_abandono:
            return "NO REALIZO"

        # --- REGLA 2: Aprobado (Mérito Académico) ---
        # Si ya tiene la nota, está aprobado sin importar si el curso cerró o no.
        if nota_final >= curso_obj.nota_aprobacion:
            return "APROBADO"

        # Preparar Fechas
        fecha_fin = curso_obj.fecha_final
        hoy = date.today()

        if isinstance(fecha_fin, datetime):
            fecha_fin = fecha_fin.date()

        # Si no tiene fecha fin, asumimos que siempre está abierto
        if not fecha_fin:
            return "EN CURSO"

        # --- EVALUACIÓN DE TIEMPOS ---
        # "El reprobado solo existe si ya esta cerrado el curso (fecha_final < hoy)"
        curso_esta_cerrado = (fecha_fin < hoy)

        if curso_esta_cerrado:
            # --- REGLA 3 y 1b: Cierre de Curso ---
            if nota_final == 0.0 or nota_final is None:
                # Cerró y no hizo nada
                return "NO REALIZO"
            else:
                # Cerró, intentó (nota > 0) pero no alcanzó
                return "REPROBADO"
        else:
            # --- REGLA 4: Curso Vigente ---
            # Aún tiene tiempo de mejorar su nota
            return "EN CURSO"

    def calcular_nota_ponderada(self, lista_notas):
        """Calcula el promedio final basado en pesos porcentuales.

        Args:
            lista_notas (list[dict]): Lista de dicts con claves 'puntaje' y 'peso'.

        Returns:
            float: Promedio ponderado sobre 10, redondeado a 2 decimales.
        """
        """
        Calcula el promedio ponderado final sobre 10.
        """
        suma_ponderada = 0.0

        for item in lista_notas:
            puntaje = item.get('puntaje', 0.0)
            peso = item.get('peso', 0.0)
            suma_ponderada += (puntaje / 10.0) * peso

        promedio_final = round(suma_ponderada / 10.0, 2)
        return promedio_final

    def actualizar_estados_por_curso(self, curso=None, curso_id=None):
        """Recalcula y actualiza los estados de todas las matrículas de un curso.

        Útil cuando cambian los parámetros del curso (fechas, nota mínima).

        Args:
            curso (Curso, optional): Instancia del curso.
            curso_id (int, optional): ID del curso si no se pasa el objeto.

        Raises:
            ValueError: Si no se proporciona curso ni curso_id.
        """
        if curso is None and curso_id is None:
            raise ValueError("Debe proporcionar 'curso' o 'curso_id'")

        session = SessionLocal()
        try:
            if not curso:
                curso = session.query(Curso).get(curso_id)

            if not curso:
                print("Curso no encontrado.")
                return

            matriculas = (
                session.query(Matricula)
                .filter(Matricula.curso_id == curso.id)
                .all()
            )

            c = 0
            for mat in matriculas:
                # CORRECCIÓN: Respetar NO REALIZO aunque la nota sea 0
                es_abandono = (mat.estado == "NO REALIZO")

                nuevo = self.determinar_estado(
                    mat.nota_final or 0.0,
                    curso,
                    es_abandono=es_abandono
                )

                if mat.estado != nuevo:
                    mat.estado = nuevo
                    c += 1

            session.commit()

        except Exception as e:
            session.rollback()
            print(f"Error actualizando curso: {e}")
        finally:
            session.close()

    def actualizar_estados_matriculas(self):
        """Rutina de mantenimiento para actualizar estados vencidos globalmente.

        Busca matrículas 'EN CURSO' asociadas a cursos que ya finalizaron
        y actualiza su estado a 'REPROBADO' o 'NO REALIZO'.
        """
        """
        FUNCIÓN DE MANTENIMIENTO AL INICIO DEL PROGRAMA.
        Busca cursos que YA CERRARON (fecha <= hoy) y actualiza a
        los estudiantes que se quedaron colgados en 'EN CURSO'.
        """
        session = SessionLocal()
        hoy = date.today()

        try:
            # 1. Buscar matrículas 'EN CURSO' de cursos ya cerrados
            matriculas_vencidas = (
                session.query(Matricula)
                .join(Matricula.curso)
                .options(joinedload(Matricula.curso))
                .filter(Curso.fecha_final < hoy)        # Curso cerrado
                .filter(Matricula.estado == "EN CURSO")  # Estado desactualizado
                .all()
            )

            count = 0
            if matriculas_vencidas:
                print(f"Detectadas {len(matriculas_vencidas)} matrículas vencidas. Actualizando...")

                for mat in matriculas_vencidas:
                    # Aplicamos la lógica central.
                    # Nota: es_abandono=False porque si fuera True, el estado sería NO REALIZO, no EN CURSO.
                    nuevo_estado = self.determinar_estado(
                        mat.nota_final or 0.0,
                        mat.curso,
                        es_abandono=False
                    )

                    if mat.estado != nuevo_estado:
                        mat.estado = nuevo_estado
                        count += 1

                session.commit()
                print(f"Mantenimiento completado: {count} registros pasaron a REPROBADO/NO REALIZO.")
            else:
                print("Todos los estados están al día.")

        except Exception as e:
            session.rollback()
            print(f"Error en mantenimiento de estados: {e}")
        finally:
            session.close()