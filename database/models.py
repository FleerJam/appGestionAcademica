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

from sqlalchemy import (
    Column, String, Float, ForeignKey, Date, JSON,
    UniqueConstraint, Enum, Integer, Boolean, LargeBinary
)
from sqlalchemy.orm import relationship
from database.conexion import Base
from utilities.uid import generar_uid


# ---------------- MODELOS ----------------

class Centro(Base):
    """Modelo que representa un centro operativo o administrativo (Zonal, Local, Sala)."""
    __tablename__ = "centros"

    id = Column(String(26), primary_key=True, default=generar_uid, index=True)
    nombre = Column(String(150), nullable=False)
    siglas = Column(String(10), nullable=False)
    ubicacion = Column(String(100), nullable=False)
    tipo = Column(Enum("LOCAL", "ZONAL", "SALA", name="tipo_centro"), nullable=False)

    centro_padre_id = Column(
        String(26),
        ForeignKey("centros.id", ondelete="SET NULL"),
        nullable=True
    )

    hijos = relationship(
        "Centro",
        backref="padre",
        remote_side="Centro.id"
    )
    personas = relationship("Persona", back_populates="centro")
    matriculas = relationship("Matricula", back_populates="centro")


class Persona(Base):
    """Modelo que representa a un individuo (Estudiante, Instructor, etc.)."""
    __tablename__ = "personas"

    id = Column(String(26), primary_key=True, default=generar_uid, index=True)
    nombre = Column(String(255), nullable=False)
    cedula = Column(String(20), unique=True, nullable=False)
    correo = Column(String(150), unique=True, nullable=True)
    rol = Column(
        Enum("ESTUDIANTE", "INSTRUCTOR", "COORDINADOR", "OTRO", name="rol_persona"),
        nullable=False
    )

    activo = Column(Boolean, default=True, nullable=False)

    centro_id = Column(
        String(26),
        ForeignKey("centros.id"),
        nullable=False
    )

    institucion_articulada = Column(String(255), nullable=True)

    matriculas = relationship(
        "Matricula",
        back_populates="persona",
        cascade="all, delete-orphan"
    )
    certificados = relationship(
        "Certificado",
        back_populates="persona",
        cascade="all, delete-orphan"
    )
    cedulas_alias = relationship(
        "CedulaAlias",
        back_populates="persona",
        cascade="all, delete-orphan"
    )

    centro = relationship("Centro", back_populates="personas")


class PlantillaCertificado(Base):
    """
    Define el diseño visual de un certificado.
    Puede almacenar la configuración JSON para renderizado canvas o el binario de Word.
    """
    __tablename__ = "plantillas_certificado"

    id = Column(String(26), primary_key=True, default=generar_uid, index=True)
    nombre = Column(String(150), nullable=False)  # Ej: "Plantilla Oficial 2026"

    # Configuración del Lienzo / Fondo
    ancho_px = Column(Integer, default=1123)  # A4 Horizontal aprox
    alto_px = Column(Integer, default=794)
    numero_paginas = Column(Integer, default=1)

    # El JSON generado por el diseñador (coordenadas, fuentes, variables)
    configuracion_json = Column(JSON, nullable=False)
    archivo_binario = Column(LargeBinary, nullable=True)
    # Relación inversa (opcional, para ver qué cursos usan esta plantilla)
    cursos = relationship("Curso", back_populates="plantilla")


class Curso(Base):
    """Modelo que representa un evento de capacitación o adiestramiento."""
    __tablename__ = "cursos"

    id = Column(String(26), primary_key=True, default=generar_uid, index=True)
    nombre = Column(String(255), nullable=False)
    tipo_curso = Column(String(255), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_final = Column(Date, nullable=False)
    responsable = Column(String(255), nullable=False)
    participantes_objetivo = Column(JSON, nullable=False)
    duracion_horas = Column(Integer, nullable=False)
    modalidad = Column(String(100), nullable=False)
    nota_aprobacion = Column(Float, default=7.0, nullable=False)

    # NUEVO: Vinculación con la plantilla de certificado
    plantilla_id = Column(
        String(26),
        ForeignKey("plantillas_certificado.id", ondelete="SET NULL"),
        nullable=True
    )

    plantilla = relationship("PlantillaCertificado", back_populates="cursos")
    matriculas = relationship("Matricula", back_populates="curso", cascade="all, delete-orphan")
    certificados = relationship("Certificado", back_populates="curso", cascade="all, delete-orphan")
    evaluaciones = relationship("EvaluacionCurso", back_populates="curso", cascade="all, delete-orphan")


class Matricula(Base):
    """Modelo asociativo que vincula a una Persona con un Curso y registra su estado académico."""
    __tablename__ = "matriculas"

    id = Column(String(26), primary_key=True, default=generar_uid, index=True)

    persona_id = Column(
        String(26),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False
    )
    curso_id = Column(
        String(26),
        ForeignKey("cursos.id", ondelete="CASCADE"),
        nullable=False
    )
    centro_id = Column(
        String(26),
        ForeignKey("centros.id"),
        nullable=False
    )

    nota_final = Column(Float)
    estado = Column(String(50), default="En curso")
    ruta_pdf_generado = Column(String(300))
    ruta_pdf_firmado = Column(String(300))
    codigo_validacion = Column(String(100), unique=True)

    persona = relationship("Persona", back_populates="matriculas")
    curso = relationship("Curso", back_populates="matriculas")
    centro = relationship("Centro", back_populates="matriculas")
    calificaciones = relationship(
        "Calificacion",
        back_populates="matricula",
        cascade="all, delete-orphan"
    )


class Calificacion(Base):
    """Modelo que almacena la nota de un estudiante en una evaluación específica."""
    __tablename__ = "calificaciones"

    id = Column(String(26), primary_key=True, default=generar_uid)

    matricula_id = Column(
        String(26),
        ForeignKey("matriculas.id", ondelete="CASCADE"),
        nullable=False
    )

    evaluacion_curso_id = Column(
        String(26),
        ForeignKey("evaluaciones_curso.id", ondelete="CASCADE"),
        nullable=False
    )

    puntaje = Column(Float, default=0.0, nullable=False)

    matricula = relationship("Matricula", back_populates="calificaciones")
    evaluacion = relationship("EvaluacionCurso")


class CedulaAlias(Base):
    """Modelo para registrar variantes o errores comunes de una cédula para corrección automática."""
    __tablename__ = "cedula_alias"

    id = Column(String(26), primary_key=True, default=generar_uid, index=True)
    alias_valor = Column(String(255), nullable=False)

    persona_id = Column(
        String(26),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False
    )

    persona = relationship("Persona", back_populates="cedulas_alias")

    __table_args__ = (
        UniqueConstraint("persona_id", "alias_valor", name="uq_persona_alias"),
    )


class TipoCertificado(Base):
    """Catálogo de tipos de certificados (Aprobación, Asistencia, etc.)."""
    __tablename__ = "tipos_certificado"

    id = Column(String(26), primary_key=True, default=generar_uid, index=True)
    nombre = Column(String(100), nullable=False, unique=True)


class Certificado(Base):
    """Modelo que representa un certificado emitido y su código de validación."""
    __tablename__ = "certificados"

    id = Column(String(26), primary_key=True, default=generar_uid, index=True)

    persona_id = Column(
        String(26),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False
    )
    curso_id = Column(
        String(26),
        ForeignKey("cursos.id", ondelete="CASCADE"),
        nullable=False
    )
    tipo_certificado_id = Column(
        String(26),
        ForeignKey("tipos_certificado.id"),
        nullable=False
    )

    fecha_emision = Column(Date, nullable=False)
    ruta_pdf = Column(String(300))
    codigo_validacion = Column(String(100), unique=True)

    persona = relationship("Persona", back_populates="certificados")
    tipo_certificado = relationship("TipoCertificado")
    curso = relationship("Curso", back_populates="certificados")


class EvaluacionCurso(Base):
    """Modelo que define una actividad evaluativa (Examen, Tarea) dentro de un curso."""
    __tablename__ = "evaluaciones_curso"

    id = Column(String(26), primary_key=True, default=generar_uid)
    curso_id = Column(
        String(26),
        ForeignKey("cursos.id", ondelete="CASCADE"),
        nullable=False
    )

    nombre = Column(String(255), nullable=False)
    porcentaje = Column(Float, nullable=False)
    orden = Column(Integer, default=0)
    obligatorio = Column(Boolean, default=True)

    curso = relationship("Curso", back_populates="evaluaciones")