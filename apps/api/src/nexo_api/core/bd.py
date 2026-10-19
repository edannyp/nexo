"""Conexión a la base `nexo`. La lógica de negocio vive en la base (funciones `app.fn_*`); la API la expone."""

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Connection, Engine, create_engine

from .config import config


@lru_cache
def _motor() -> Engine:
    return create_engine(config().url_bd, pool_pre_ping=True, pool_size=5, max_overflow=5)


def obtener_motor() -> Engine:
    """Dependencia sustituible en pruebas (`app.dependency_overrides[obtener_motor]`)."""
    return _motor()


Motor = Annotated[Engine, Depends(obtener_motor)]


def conexion(motor: Motor) -> Iterator[Connection]:
    with motor.connect() as c:
        yield c


Conexion = Annotated[Connection, Depends(conexion)]
