"""Catálogos para el filtro global: categorías en alcance y artículos activos por línea (ADR 0010)."""

from enum import StrEnum

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from ..core.bd import Conexion

router = APIRouter(tags=["catalogos"])


class Linea(StrEnum):
    IMPORTADO = "IMPORTADO"
    FABRICADO = "FABRICADO"


class Categoria(BaseModel):
    id: int
    codigo: str
    nombre: str
    part_terminology_id: int | None
    activos: dict[Linea, int]


@router.get("/categorias", response_model=list[Categoria], summary="Categorías en alcance con artículos activos por línea")
def listar_categorias(c: Conexion) -> list[Categoria]:
    filas = c.execute(text("""
        select c.id, c.codigo_sap, c.nombre, c.part_terminology_id_defecto,
               count(a.id) filter (where a.linea = 'IMPORTADO') as importados,
               count(a.id) filter (where a.linea = 'FABRICADO') as fabricados
        from app.categoria c
        left join app.articulo a on a.categoria_id = c.id and a.activo
        where c.activa
        group by c.id
        order by c.id
    """)).all()
    return [
        Categoria(id=f.id, codigo=f.codigo_sap, nombre=f.nombre, part_terminology_id=f.part_terminology_id_defecto,
                  activos={Linea.IMPORTADO: f.importados, Linea.FABRICADO: f.fabricados})
        for f in filas
    ]
