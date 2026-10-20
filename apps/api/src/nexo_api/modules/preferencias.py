"""Preferencias del usuario: el filtro global guardado en el servidor (ADR 0010), para que lo siga entre equipos."""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..auth.dependencias import UsuarioActual
from ..auth.registro import fijar_actor
from ..core.bd import Conexion
from ..core.errores import Problema
from .catalogos import Linea

router = APIRouter(prefix="/preferencias", tags=["preferencias"])


class Preferencias(BaseModel):
    cat: str = Field(pattern=r"^\d{2}$", description="Código SAP de la categoría (dos dígitos)")
    linea: Linea


@router.get("", response_model=Preferencias, summary="Preferencias del usuario (por defecto Radiadores · Importados)")
def obtener_preferencias(usuario: UsuarioActual, c: Conexion) -> Preferencias:
    fila = c.execute(text("""
        select c.codigo_sap as cat, p.linea::text as linea
        from app.preferencia_usuario p join app.categoria c on c.id = p.categoria_id where p.usuario_id = :id
    """), {"id": usuario.id}).one_or_none()
    return Preferencias(cat=fila.cat, linea=Linea(fila.linea)) if fila else Preferencias(cat="25", linea=Linea.IMPORTADO)


@router.put("", response_model=Preferencias, summary="Guardar preferencias", responses={422: {"description": "Categoría inexistente"}})
def guardar_preferencias(datos: Preferencias, usuario: UsuarioActual, c: Conexion) -> Preferencias:
    with c.begin():
        fijar_actor(c, usuario.id)
        guardado = c.execute(text("""
            insert into app.preferencia_usuario (usuario_id, categoria_id, linea)
            select :u, c.id, cast(:linea as app.linea) from app.categoria c where c.codigo_sap = :cat and c.activa
            on conflict (usuario_id) do update set categoria_id = excluded.categoria_id, linea = excluded.linea
            returning usuario_id
        """), {"u": usuario.id, "cat": datos.cat, "linea": datos.linea.value}).one_or_none()
    if guardado is None:
        mensaje = f"La categoría {datos.cat} no existe o no está activa."
        raise Problema(422, "Categoría no válida", errors=[{"campo": "cat", "mensaje": mensaje}])
    return datos
