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

from sqlalchemy.exc import IntegrityError
from database.conexion import SessionLocal
from sqlalchemy import or_


class BaseCRUDModel:
    """Clase base abstracta para operaciones CRUD genéricas en modelos SQLAlchemy.

    Proporciona métodos estandarizados para crear, leer, actualizar y eliminar registros,
    así como capacidades de búsqueda y filtrado dinámico. Las clases hijas deben
    definir el atributo de clase `model` con el modelo SQLAlchemy correspondiente.
    """

    model = None  # se define en la subclase

    # ----------------------------
    # MÉTODOS BÁSICOS CRUD
    # ----------------------------
    @staticmethod
    def _get_session():
        """Crea y devuelve una nueva sesión de base de datos local.

        Returns:
            Session: Una instancia de sqlalchemy.orm.Session.
        """
        return SessionLocal()

    def get_all(self):
        """Recupera todos los registros existentes del modelo.

        Returns:
            list: Lista de todas las instancias del modelo en la base de datos.
        """
        with self._get_session() as session:
            return session.query(self.model).all()

    def get_by_id(self, obj_id: int):
        """Busca un registro por su clave primaria (ID).

        Args:
            obj_id (int): El identificador único del registro.

        Returns:
            object: La instancia del modelo si existe, None en caso contrario.
        """
        with self._get_session() as session:
            return session.query(self.model).filter_by(id=obj_id).first()

    def create(self, data: dict):
        """Crea un nuevo registro en la base de datos.

        Args:
            data (dict): Diccionario con los datos para inicializar el modelo.

        Returns:
            object: La instancia del modelo recién creada y persistida.

        Raises:
            IntegrityError: Si ocurre una violación de restricción (ej. clave única duplicada).
        """
        with self._get_session() as session:
            try:
                obj = self.model(**data)
                session.add(obj)
                session.commit()
                session.refresh(obj)
                return obj
            except IntegrityError:
                session.rollback()
                raise

    def update(self, obj_id: int, data: dict):
        """Actualiza un registro existente identificado por su ID.

        Args:
            obj_id (int): ID del registro a actualizar.
            data (dict): Diccionario clave-valor con los campos a modificar.

        Returns:
            object: La instancia actualizada si existe, None si no se encuentra.

        Raises:
            IntegrityError: Si la actualización viola restricciones de integridad.
        """
        with self._get_session() as session:
            try:
                obj = session.query(self.model).filter_by(id=obj_id).first()
                if not obj:
                    return None
                for key, value in data.items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)
                session.commit()
                session.refresh(obj)
                return obj
            except IntegrityError:
                session.rollback()
                raise

    def delete(self, obj_id: int):
        """Elimina un registro de la base de datos por su ID.

        Args:
            obj_id (int): ID del registro a eliminar.

        Returns:
            bool: True si se eliminó correctamente, False si el registro no existía.
        """
        with self._get_session() as session:
            obj = session.query(self.model).filter_by(id=obj_id).first()
            if not obj:
                return False
            session.delete(obj)
            session.commit()
            return True

    # ----------------------------
    # MÉTODO AUXILIAR DE FILTRADO
    # ----------------------------
    def _apply_filters(self, query, filters: dict | None = None, or_fields: list[tuple[str, str]] | None = None):
        """Aplica filtros dinámicos (AND) y de búsqueda parcial (OR) a una consulta.

        Args:
            query (Query): Objeto Query base de SQLAlchemy.
            filters (dict, optional): Filtros de igualdad exacta (AND). {campo: valor}.
            or_fields (list[tuple], optional): Filtros de búsqueda parcial (OR). [(campo, valor)].

        Returns:
            Query: El objeto Query modificado con los filtros aplicados.
        """
        # Filtros exactos (AND)
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.filter(getattr(self.model, field) == value)

        # Filtros parciales (OR)
        if or_fields:
            or_conditions = []
            for field, value in or_fields:
                if hasattr(self.model, field):
                    column = getattr(self.model, field)
                    or_conditions.append(column.ilike(f"%{value}%"))
            if or_conditions:
                query = query.filter(or_(*or_conditions))

        return query

    # ----------------------------
    # MÉTODOS DE CONSULTA AVANZADA
    # ----------------------------
    def count(self, filters: dict | None = None, or_fields: list[tuple[str, str]] | None = None):
        """Cuenta el número de registros que coinciden con los criterios dados.

        Args:
            filters (dict, optional): Filtros exactos (AND).
            or_fields (list[tuple], optional): Filtros parciales (OR).

        Returns:
            int: Cantidad de registros encontrados.
        """
        with self._get_session() as session:
            query = session.query(self.model)
            query = self._apply_filters(query, filters, or_fields)
            return query.count()

    def search(
        self,
        filters: dict | None = None,
        order_by=None,
        limit: int | None = None,
        offset: int | None = None,
        first: bool = False,
        or_fields: list[tuple[str, str]] | None = None
    ):
        """Realiza una búsqueda avanzada con filtros, ordenamiento y paginación.

        Args:
            filters (dict, optional): Filtros exactos (AND).
            order_by (Column, optional): Criterio de ordenamiento SQLAlchemy.
            limit (int, optional): Límite de registros a devolver.
            offset (int, optional): Número de registros a saltar.
            first (bool, optional): Si True, devuelve solo el primer resultado.
            or_fields (list[tuple], optional): Filtros parciales (OR).

        Returns:
            list | object: Lista de resultados o una instancia única si first=True.
        """
        with self._get_session() as session:
            query = session.query(self.model)
            query = self._apply_filters(query, filters, or_fields)

            if order_by is not None:
                query = query.order_by(order_by)
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            return query.first() if first else query.all()