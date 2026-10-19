"""Búsqueda universal (Ctrl+K, propuesta UX §5): códigos, número de parte, medidas del core o texto de la descripción.

Medidas: `400x518x26` o `400 518` busca alto y largo como par sin orden (SAP los invierte en ~1/3) con tolerancia de ±10 mm;
el tercer número (ancho) también con ±10 mm. El catálogo maestro y los vehículos se suman en los pasos 6 y 7.
"""

import re
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

from ..auth.dependencias import UsuarioActual
from ..core.bd import Conexion
from .panorama import Estado
from .tipo import TipoArticulo

router = APIRouter(prefix="/busqueda", tags=["busqueda"])

TOLERANCIA_MM = 10
LIMITE = 20
_MEDIDAS = re.compile(r"^\s*(\d{2,4}(?:[.,]\d+)?)\s*[x×*\s]\s*(\d{2,4}(?:[.,]\d+)?)(?:\s*[x×*\s]\s*(\d{1,3}(?:[.,]\d+)?))?\s*$", re.I)


class Coincidencia(StrEnum):
    CODIGO = "codigo"
    CODIGO_ANTERIOR = "codigo_anterior"
    NUMERO_PARTE = "numero_parte"
    MEDIDAS = "medidas"
    DESCRIPCION = "descripcion"


class Resultado(BaseModel):
    item_code: str
    descripcion: str | None
    estado: Estado
    categoria_codigo: str | None
    linea: str
    coincide: Coincidencia
    panal_alto_mm: Decimal | None
    panal_largo_mm: Decimal | None
    panal_ancho_mm: Decimal | None


class Resultados(BaseModel):
    consulta: str
    medidas: list[Decimal] | None     # las medidas interpretadas, si la consulta lo era
    articulos: list[Resultado]


def _num(x: str) -> Decimal:
    return Decimal(x.replace(",", "."))


@router.get("", response_model=Resultados, summary="Búsqueda universal de artículos")
def buscar(
    _: UsuarioActual,
    tipo: TipoArticulo,
    c: Conexion,
    q: Annotated[str, Query(min_length=2, max_length=100)],
    todos: Annotated[bool, Query(description="Buscar en todos los tipos de artículo, no solo en el del filtro global")] = False,
) -> Resultados:
    consulta = q.strip()
    p: dict[str, object] = {"cat": tipo.categoria_id, "linea": tipo.linea.value, "lim": LIMITE, "tol": TOLERANCIA_MM}
    del_tipo = "a.activo" + ("" if todos else " and a.categoria_id = :cat and a.linea = cast(:linea as app.linea)")
    columnas = """a.item_code, a.descripcion, a.estado::text as estado, a.categoria_codigo, a.linea::text as linea,
                  a.panal_alto_mm, a.panal_largo_mm, a.panal_ancho_mm"""

    m = _MEDIDAS.match(consulta)
    if m:
        x, y, z = _num(m.group(1)), _num(m.group(2)), m.group(3) and _num(m.group(3))
        p |= {"x": x, "y": y, "z": z}
        filas = c.execute(text(f"""
            select {columnas}, 'medidas' as coincide from app.articulo a
            where {del_tipo}
              and ((abs(a.panal_alto_mm - :x) <= :tol and abs(a.panal_largo_mm - :y) <= :tol)
                   or (abs(a.panal_alto_mm - :y) <= :tol and abs(a.panal_largo_mm - :x) <= :tol))
              and (cast(:z as numeric) is null or abs(a.panal_ancho_mm - :z) <= :tol)
            order by least(abs(a.panal_alto_mm - :x) + abs(a.panal_largo_mm - :y), abs(a.panal_alto_mm - :y) + abs(a.panal_largo_mm - :x))
                     + coalesce(abs(a.panal_ancho_mm - :z), 0), a.item_code
            limit :lim
        """), p).all()
        return Resultados(consulta=consulta, medidas=[v for v in (x, y, z) if v], articulos=[Resultado(**f._mapping) for f in filas])

    p |= {"q": consulta.upper(), "prefijo": f"{consulta}%", "parte": f"%{consulta}%"}
    # Todas las palabras deben aparecer en la descripción (en cualquier orden): "toyota 22r plast"
    palabras = [w for w in re.split(r"\s+", consulta) if w][:6]
    condiciones = " and ".join(f"a.descripcion ilike :w{i}" for i in range(len(palabras))) or "false"
    p |= {f"w{i}": f"%{w}%" for i, w in enumerate(palabras)}
    filas = c.execute(text(f"""
        select * from (
          select distinct on (item_code) * from (
            select {columnas}, 'codigo' as coincide, 1 as prioridad from app.articulo a
              where {del_tipo} and a.item_code ilike :prefijo
            union all
            select {columnas}, 'codigo_anterior', 2 from app.articulo a where {del_tipo} and :q = any (a.codigo_anterior)
            union all
            select {columnas}, 'numero_parte', 3 from app.articulo a where {del_tipo} and a.numero_parte_proveedor ilike :parte
            union all
            select {columnas}, 'descripcion', 4 from app.articulo a where {del_tipo} and {condiciones}
          ) t order by item_code, prioridad
        ) u order by prioridad, item_code limit :lim
    """), p).all()
    return Resultados(consulta=consulta, medidas=None,
                      articulos=[Resultado(**{k: v for k, v in f._mapping.items() if k != "prioridad"}) for f in filas])
