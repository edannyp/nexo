"""Vistas guardadas de Explorar por usuario (filtros, columnas y orden)."""

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..auth.dependencias import UsuarioActual
from ..core.bd import Conexion

router = APIRouter(prefix="/vistas", tags=["vistas"])


class NuevaVista(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)
    parametros: dict[str, Any] = Field(description="Filtros, orden y columnas, tal como los usa la consola")
    pantalla: str = "explorar"


class Vista(NuevaVista):
    id: int
    creada_en: datetime


@router.get("", response_model=list[Vista], summary="Vistas guardadas del usuario")
def listar_vistas(usuario: UsuarioActual, c: Conexion, pantalla: str = "explorar") -> list[Vista]:
    filas = c.execute(text("""select id, nombre, parametros, pantalla, creada_en from app.vista_guardada
                              where usuario_id = :u and pantalla = :p order by nombre"""), {"u": usuario.id, "p": pantalla}).all()
    return [Vista(**f._mapping) for f in filas]


@router.put("", response_model=Vista, summary="Guardar (o reemplazar) una vista por su nombre")
def guardar_vista(datos: NuevaVista, usuario: UsuarioActual, c: Conexion) -> Vista:
    with c.begin():
        fila = c.execute(text("""
            insert into app.vista_guardada (usuario_id, pantalla, nombre, parametros) values (:u, :p, :n, cast(:par as jsonb))
            on conflict (usuario_id, pantalla, nombre) do update set parametros = excluded.parametros
            returning id, nombre, parametros, pantalla, creada_en
        """), {"u": usuario.id, "p": datos.pantalla, "n": datos.nombre.strip(), "par": json.dumps(datos.parametros)}).one()
    return Vista(**fila._mapping)


@router.delete("/{vista_id}", status_code=204, summary="Borrar una vista propia")
def borrar_vista(vista_id: int, usuario: UsuarioActual, c: Conexion) -> None:
    with c.begin():
        c.execute(text("delete from app.vista_guardada where id = :id and usuario_id = :u"), {"id": vista_id, "u": usuario.id})
