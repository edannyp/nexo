"""Hallazgos de calidad de SAP: datos que deben corregirse EN SAP (Nexo no escribe en SAP). Se cierran solos cuando el siguiente
lote del ETL trae el dato corregido."""

import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import Connection, text

from ..auth.dependencias import Rol, requiere_rol
from ..core.bd import Conexion
from .tipo import Tipo, TipoArticulo

router = APIRouter(prefix="/hallazgos-sap", tags=["calidad-sap"],
                   dependencies=[Depends(requiere_rol(Rol.SUPERVISOR, Rol.ADMINISTRADOR))])

DESCRIPCION_TIPO = {
    "MARCA_INVALIDA": "Marca que no es una marca (vacía, basura o código genérico)",
    "VALOR_NO_RECONOCIDO": "Valor de lista, unidad o modelo que no se reconoce",
    "ANIOS_INVERTIDOS": "Año inicial mayor que el final",
    "NOMBRE_INACTIVO_SIN_CONGELAR": "Dice INACTIVO en el nombre pero no está congelado",
    "MEDIDAS_INVERTIDAS": "Alto y largo intercambiados",
    "SUBCATEGORIA_INCONSISTENTE": "Subcategoría que no corresponde a la categoría",
    "VEHICULO_DISTINTO": "El vehículo de SAP no es el vehículo principal que confirmó Nexo",
}


class Grupo(BaseModel):
    tipo: str
    descripcion: str
    campo_sap: str
    n: int


class Hallazgo(BaseModel):
    id: int
    tipo: str
    campo_sap: str
    valor: str | None
    item_code: str
    descripcion_articulo: str | None
    detectado_en: datetime


class HallazgosSap(BaseModel):
    grupos: list[Grupo]
    hallazgos: list[Hallazgo]


def _hallazgos(c: Connection, tipo: Tipo) -> list[Hallazgo]:
    filas = c.execute(text("""
        select h.id, h.tipo::text as tipo, h.campo_sap, h.valor, a.item_code, a.descripcion as descripcion_articulo, h.detectado_en
        from app.hallazgo_calidad_sap h join app.articulo a on a.id = h.articulo_id
        where h.corregido_en is null and a.categoria_id = :cat and a.linea = cast(:linea as app.linea)
        order by h.tipo, h.campo_sap, a.item_code
    """), {"cat": tipo.categoria_id, "linea": tipo.linea.value}).all()
    return [Hallazgo(**f._mapping) for f in filas]


@router.get("", response_model=HallazgosSap, summary="Hallazgos abiertos del tipo de artículo, agrupados")
def listar_hallazgos_sap(tipo: TipoArticulo, c: Conexion) -> HallazgosSap:
    hallazgos = _hallazgos(c, tipo)
    conteo: dict[tuple[str, str], int] = {}
    for h in hallazgos:
        conteo[(h.tipo, h.campo_sap)] = conteo.get((h.tipo, h.campo_sap), 0) + 1
    grupos = [Grupo(tipo=t, descripcion=DESCRIPCION_TIPO.get(t, t), campo_sap=campo, n=n)
              for (t, campo), n in sorted(conteo.items(), key=lambda x: -x[1])]
    return HallazgosSap(grupos=grupos, hallazgos=hallazgos)


@router.get("/csv", summary="Hallazgos abiertos en CSV (se abre en Excel)", response_class=Response,
            responses={200: {"content": {"text/csv": {}}}})
def exportar_hallazgos_sap(tipo: TipoArticulo, c: Conexion) -> Response:
    salida = io.StringIO()
    w = csv.writer(salida)
    w.writerow(["Artículo", "Descripción", "Hallazgo", "Campo SAP", "Valor en SAP", "Detectado"])
    for h in _hallazgos(c, tipo):
        w.writerow([h.item_code, h.descripcion_articulo, DESCRIPCION_TIPO.get(h.tipo, h.tipo), h.campo_sap, h.valor,
                    h.detectado_en.strftime("%Y-%m-%d")])
    nombre = f"hallazgos-sap-{tipo.codigo}-{tipo.linea.value.lower()}.csv"
    # BOM para que Excel reconozca UTF-8 (acentos)
    return Response("﻿" + salida.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}"'})
