"""Salud del servicio: viva (proceso) y lista (base accesible y migrada)."""

from importlib.metadata import version

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..core.bd import Motor
from ..core.errores import problema

router = APIRouter(prefix="/salud", tags=["salud"])


class Viva(BaseModel):
    estado: str
    version: str


class Lista(BaseModel):
    estado: str
    migracion: str


@router.get("", response_model=Viva, summary="El proceso responde")
def obtener_salud() -> Viva:
    return Viva(estado="ok", version=version("nexo-api"))


@router.get("/lista", response_model=Lista, summary="La base responde y está migrada",
            responses={503: {"description": "Base no disponible"}})
def obtener_salud_lista(motor: Motor) -> Lista | JSONResponse:
    try:
        with motor.connect() as c:
            migracion = c.execute(text("select version_num from alembic_version")).scalar_one()
    except SQLAlchemyError:
        return problema(503, "Base no disponible", "No se pudo consultar la base nexo o no está migrada.")
    return Lista(estado="ok", migracion=migracion)
