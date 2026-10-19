"""Errores como RFC 9457 `application/problem+json` (architecture/api/convenciones.md)."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

log = logging.getLogger("nexo_api")

TIPO_PROBLEMA = "application/problem+json"


def problema(status: int, title: str, detail: str | None = None, **extra: object) -> JSONResponse:
    cuerpo = {"type": "about:blank", "title": title, "status": status} | ({"detail": detail} if detail else {}) | extra
    return JSONResponse(cuerpo, status_code=status, media_type=TIPO_PROBLEMA)


def registrar(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http(_: Request, e: HTTPException) -> JSONResponse:
        titulo = e.detail if isinstance(e.detail, str) else "Error"
        return problema(e.status_code, titulo)

    @app.exception_handler(RequestValidationError)
    async def validacion(_: Request, e: RequestValidationError) -> JSONResponse:
        errores = [{"campo": ".".join(str(p) for p in err["loc"][1:]), "mensaje": err["msg"]} for err in e.errors()]
        return problema(422, "Datos inválidos", errors=errores)

    @app.exception_handler(Exception)
    async def inesperado(request: Request, e: Exception) -> JSONResponse:
        log.exception("Error no controlado en %s %s", request.method, request.url.path, exc_info=e)
        return problema(500, "Error interno", "Ocurrió un error inesperado. Si se repite, avisa al administrador.")
