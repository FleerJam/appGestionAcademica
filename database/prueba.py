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

import random
from datetime import timedelta
from faker import Faker
from sqlalchemy.orm import Session
from database.conexion import engine, Base
from database.models import Curso  # Asegúrate de importar tu modelo Curso

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

# Inicializar Faker
faker = Faker("es_ES")  # Español

# Opciones para campos
TIPOS_CURSO = ["CURSO", "TALLER", "CONFERENCIA/CHARLA"]
MODALIDADES = ["PRESENCIAL", "VIRTUAL", "SEMIPRESENCIAL"]
PARTICIPANTES_OBJETIVO = [
    "Personal del SIS ECU 911",
    "Instituciones articuladas y/o vinculadas",
    "Ciudadanía en general"
]


def generar_curso_aleatorio():
    """Genera una instancia de Curso con datos ficticios para pruebas.

    Returns:
        Curso: Objeto curso con datos aleatorios (nombre, fechas, modalidad, etc).
    """
    nombre = f"{faker.word().capitalize()} {faker.word().capitalize()} {faker.random_number(digits=4)}"
    tipo_curso = random.choice(TIPOS_CURSO)
    modalidad = random.choice(MODALIDADES)
    responsable = faker.name()
    duracion_horas = random.randint(1, 40)
    nota_aprobacion = round(random.uniform(3.0, 7.0), 2)

    # Fechas aleatorias en los próximos 6 meses
    fecha_inicio = faker.date_between(start_date="today", end_date="+180d")
    fecha_final = fecha_inicio + timedelta(days=random.randint(1, 30))

    # Participantes objetivo aleatorios
    participantes = random.sample(PARTICIPANTES_OBJETIVO, k=random.randint(1, len(PARTICIPANTES_OBJETIVO)))

    return Curso(
        nombre=nombre,
        tipo_curso=tipo_curso,
        modalidad=modalidad,
        responsable=responsable,
        duracion_horas=duracion_horas,
        nota_aprobacion=nota_aprobacion,
        fecha_inicio=fecha_inicio,
        fecha_final=fecha_final,
        participantes_objetivo=participantes
    )


def crear_cursos(n=500):
    """Crea e inserta masivamente un número especificado de cursos aleatorios en la BD.

    Args:
        n (int, optional): Cantidad de cursos a generar. Defaults to 500.
    """
    with Session(engine) as session:
        cursos = [generar_curso_aleatorio() for _ in range(n)]
        session.add_all(cursos)
        session.commit()
        print(f"✅ Se han creado {n} cursos de prueba exitosamente.")


if __name__ == "__main__":
    crear_cursos(25)