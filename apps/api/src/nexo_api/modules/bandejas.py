"""Bandejas y flujo: "Siguiente", reserva (latido y soltar) y transiciones de estado (context/workflow-estados.md)."""

from datetime import datetime
from enum import StrEnum

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..auth.dependencias import Rol, UsuarioActual
from ..auth.registro import fijar_actor
from ..core.bd import Conexion
from ..core.errores import Problema
from ..core.negocio import reglas_de_negocio
from .articulos import ArticuloDetalle, cargar_detalle
from .panorama import Estado
from .tipo import TipoArticulo

router = APIRouter(tags=["bandejas"])

MINUTOS_RESERVA = 30


class Bandeja(StrEnum):
    OPERADOR = "operador"        # PENDIENTE y RECHAZADO
    SUPERVISOR = "supervisor"    # POR_VALIDAR (nunca lo que el propio supervisor envió)


_BANDEJAS = {
    Bandeja.OPERADOR: (["PENDIENTE", "RECHAZADO"], {Rol.OPERADOR, Rol.SUPERVISOR}),
    Bandeja.SUPERVISOR: (["POR_VALIDAR"], {Rol.SUPERVISOR, Rol.ADMINISTRADOR}),
}


class Siguiente(BaseModel):
    articulo: ArticuloDetalle | None = Field(description="null si la bandeja está vacía")


class Transicion(BaseModel):
    destino: Estado
    motivo: str | None = Field(None, max_length=500)
    version: int = Field(description="Versión que ve el usuario: si otro lo cambió, responde 409")


class ReservaRenovada(BaseModel):
    hasta: datetime


@router.post("/bandejas/{bandeja}/siguiente", response_model=Siguiente, summary="Reserva el siguiente artículo de la bandeja")
def tomar_siguiente(bandeja: Bandeja, usuario: UsuarioActual, tipo: TipoArticulo, c: Conexion) -> Siguiente:
    estados, roles = _BANDEJAS[bandeja]
    if not usuario.roles & roles:
        raise Problema(403, "Tu rol no trabaja esta bandeja")
    with c.begin():
        item = c.execute(text("""
            select (app.fn_tomar_siguiente(:u, cast(:e as app.estado_articulo[]), cast(:cat as smallint),
                                          cast(:linea as app.linea), :min)).item_code
        """), {"u": usuario.id, "e": estados, "cat": tipo.categoria_id, "linea": tipo.linea.value, "min": MINUTOS_RESERVA}).scalar_one()
    return Siguiente(articulo=cargar_detalle(c, item, usuario) if item else None)


def _id(c, item_code: str) -> int:
    i = c.execute(text("select id from app.articulo where item_code = upper(:ic)"), {"ic": item_code}).scalar_one_or_none()
    if i is None:
        raise Problema(404, "El artículo no existe")
    return i


@router.post("/articulos/{item_code}/asignacion", response_model=ReservaRenovada, summary="Tomar este artículo (reservarlo)",
             responses={409: {"description": "Reservado por otro usuario o inactivo"}})
def reservar_articulo(item_code: str, usuario: UsuarioActual, c: Conexion) -> ReservaRenovada:
    with c.begin(), reglas_de_negocio():
        hasta = c.execute(text("select app.fn_reservar(:a, :u, :m)"),
                          {"a": _id(c, item_code), "u": usuario.id, "m": MINUTOS_RESERVA}).scalar_one()
    return ReservaRenovada(hasta=hasta)


@router.put("/articulos/{item_code}/asignacion", response_model=ReservaRenovada, summary="Latido: renueva la reserva propia",
            responses={409: {"description": "La reserva ya no es tuya"}})
def renovar_reserva(item_code: str, usuario: UsuarioActual, c: Conexion) -> ReservaRenovada:
    with c.begin(), reglas_de_negocio():
        hasta = c.execute(text("select app.fn_renovar_reserva(:a, :u, :m)"),
                          {"a": _id(c, item_code), "u": usuario.id, "m": MINUTOS_RESERVA}).scalar_one()
    return ReservaRenovada(hasta=hasta)


@router.delete("/articulos/{item_code}/asignacion", status_code=204, summary="Soltar: devuelve el artículo a la bandeja")
def soltar_reserva(item_code: str, usuario: UsuarioActual, c: Conexion) -> None:
    with c.begin():
        c.execute(text("select app.fn_soltar_reserva(:a, :u)"), {"a": _id(c, item_code), "u": usuario.id})


@router.post("/articulos/{item_code}/transiciones", response_model=ArticuloDetalle, summary="Cambiar el estado del artículo",
             responses={403: {"description": "Rol o doble control"}, 409: {"description": "Conflicto o reservado por otro"},
                        422: {"description": "Falta motivo o requisitos"}})
def transicionar(item_code: str, datos: Transicion, usuario: UsuarioActual, c: Conexion) -> ArticuloDetalle:
    with c.begin():
        fijar_actor(c, usuario.id)
        a = c.execute(text("""select a.id, a.asignado_a, a.asignado_hasta > now() as reservado, u.nombre
                              from app.articulo a left join app.usuario u on u.id = a.asignado_a
                              where a.item_code = upper(:ic) for update of a"""), {"ic": item_code}).one_or_none()
        if a is None:
            raise Problema(404, "El artículo no existe")
        if a.reservado and a.asignado_a != usuario.id:
            raise Problema(409, "Está reservado por otro usuario", f"{a.nombre} lo está trabajando.")
        with reglas_de_negocio():
            c.execute(text("""select app.fn_transicionar(:a, cast(:d as app.estado_articulo), 'USUARIO', :u, :m, null, :v)"""),
                      {"a": a.id, "d": datos.destino.value, "u": str(usuario.id), "m": datos.motivo, "v": datos.version})
    return cargar_detalle(c, item_code, usuario)
