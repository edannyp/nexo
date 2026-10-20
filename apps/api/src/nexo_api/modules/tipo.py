"""Filtro global (ADR 0010) como dependencia: `?cat=25&linea=IMPORTADO` → categoría y línea validadas."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy import text

from ..core.bd import Conexion
from ..core.errores import Problema
from .catalogos import Linea


@dataclass(frozen=True)
class Tipo:
    categoria_id: int
    codigo: str
    nombre: str
    linea: Linea


def tipo_articulo(c: Conexion,
                  cat: Annotated[str, Query(pattern=r"^\d{2}$", description="Código SAP de la categoría")] = "25",
                  linea: Annotated[Linea, Query(description="Línea")] = Linea.IMPORTADO) -> Tipo:
    fila = c.execute(text("select id, codigo_sap, nombre from app.categoria where codigo_sap = :c and activa"), {"c": cat}).one_or_none()
    c.rollback()
    if fila is None:
        raise Problema(422, "Categoría no válida", errors=[{"campo": "cat", "mensaje": f"La categoría {cat} no existe o no está activa."}])
    return Tipo(categoria_id=fila.id, codigo=fila.codigo_sap, nombre=fila.nombre, linea=linea)


TipoArticulo = Annotated[Tipo, Depends(tipo_articulo)]
