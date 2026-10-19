"""Traduce los errores de negocio que lanza la base (`raise exception 'CODIGO: detalle'`) a problem+json para el usuario.

La lógica de las reglas vive en la base (funciones `app.fn_*`); aquí solo se decide el estado HTTP y el mensaje.
"""

import re
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import DBAPIError

from .errores import Problema

# código → (estado HTTP, título para el usuario)
ERRORES = {
    "ARTICULO_NO_EXISTE": (404, "El artículo no existe"),
    "CONFLICTO_VERSION": (409, "Otro usuario cambió este artículo"),
    "ARTICULO_INACTIVO": (409, "El artículo está inactivo"),
    "TRANSICION_NO_PERMITIDA": (409, "Ese cambio de estado no está permitido"),
    "MOTIVO_OBLIGATORIO": (422, "Falta el motivo"),
    "ROL_INSUFICIENTE": (403, "Tu rol no permite esta acción"),
    "DOBLE_CONTROL": (403, "No puedes validar ni rechazar lo que tú enviaste a revisión"),
    "REQUISITOS_INCOMPLETOS": (422, "Faltan datos para enviar a revisión"),
    "RESERVA_PERDIDA": (409, "El artículo ya no está reservado por ti"),
    "RESERVADO_POR_OTRO": (409, "Está reservado por otro usuario"),
}
_CODIGO = re.compile(r"^([A-Z_]+): ?(.*)$", re.S)


@contextmanager
def reglas_de_negocio() -> Iterator[None]:
    """Envuelve llamadas a funciones de la base: un `CODIGO: detalle` conocido se convierte en `Problema`."""
    try:
        yield
    except DBAPIError as e:
        mensaje = str(getattr(e.orig, "diag", None) and e.orig.diag.message_primary or e.orig).strip()
        m = _CODIGO.match(mensaje)
        if not m or m.group(1) not in ERRORES:
            raise
        status, titulo = ERRORES[m.group(1)]
        detalle = m.group(2).strip() or None
        errores = [{"campo": "motivo", "mensaje": "Escribe el motivo."}] if m.group(1) == "MOTIVO_OBLIGATORIO" else None
        raise Problema(status, titulo, detalle, errors=errores) from e
