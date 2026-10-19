"""Bases externas (AutoCare, MercadoExterno, Consolidación): si no responden, 503 con problem+json en vez de un error interno."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import OperationalError

from ..core.errores import Problema


@contextmanager
def disponible(nombre: str) -> Iterator[None]:
    try:
        yield
    except OperationalError as e:
        raise Problema(503, f"{nombre} no disponible", "No se pudo consultar. Intenta de nuevo en unos minutos.") from e
