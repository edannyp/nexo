"""Análisis de ventas por tipo de artículo (ADR 0022): solo con el permiso VER_ANALISIS_VENTAS. Unidades, nunca montos."""

from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from ..auth.dependencias import Permiso, requiere_permiso
from ..core.bd import Conexion
from .panorama import Estado
from .tipo import TipoArticulo

router = APIRouter(prefix="/ventas", tags=["ventas"], dependencies=[Depends(requiere_permiso(Permiso.VER_ANALISIS_VENTAS))])

MESES_SERIE = 24


class PuntoSerie(BaseModel):
    mes: date
    unidades: Decimal


class ArticuloVenta(BaseModel):
    articulo_id: int
    item_code: str
    descripcion: str | None
    estado: Estado
    clase: str | None
    unidades: Decimal
    unidades_previas: Decimal
    participacion: Decimal | None
    top_pct: Decimal | None
    tendencia: Decimal | None
    abcxyz_empresa: str | None
    serie: list[Decimal]          # últimos 12 meses completos, del más antiguo al más reciente


class AnalisisVentas(BaseModel):
    meses: int
    actualizado_en: datetime | None
    serie: list[PuntoSerie]       # unidades del tipo, últimos 24 meses completos
    articulos: list[ArticuloVenta]


@router.get("", response_model=AnalisisVentas, summary="Análisis de ventas del tipo de artículo (requiere permiso)")
def analizar_ventas(tipo: TipoArticulo, c: Conexion) -> AnalisisVentas:
    p = {"cat": tipo.categoria_id, "linea": tipo.linea.value, "n": MESES_SERIE}
    meses = c.execute(text("select valor::int from meta.parametro where clave = 'ventas.meses_periodo'")).scalar_one()
    actualizado = c.execute(text("select max(ejecutada_en) from meta.carga_ventas")).scalar_one()
    serie = c.execute(text("""
        with m as (select generate_series(date_trunc('month', current_date) - make_interval(months => :n),
                                          date_trunc('month', current_date) - interval '1 month', interval '1 month')::date as mes)
        select m.mes, coalesce(sum(v.unidades), 0) as unidades
        from m
        left join app.venta_mensual v on v.mes = m.mes
          and v.item_code in (select item_code from app.articulo a
                              where a.activo and a.categoria_id = :cat and a.linea = cast(:linea as app.linea))
        group by m.mes order by m.mes
    """), p).all()
    articulos = c.execute(text("""
        with m as (select generate_series(date_trunc('month', current_date) - interval '12 months',
                                          date_trunc('month', current_date) - interval '1 month', interval '1 month')::date as mes)
        select v.articulo_id, v.item_code, a.descripcion, a.estado::text as estado, v.clase, v.unidades, v.unidades_previas,
               v.participacion, v.top_pct, v.tendencia, v.abcxyz_empresa,
               array(select coalesce(vm.unidades, 0) from m left join app.venta_mensual vm on vm.item_code = v.item_code and vm.mes = m.mes
                     order by m.mes) as serie
        from app.v_indicador_venta v join app.articulo a on a.id = v.articulo_id
        where v.categoria_id = :cat and v.linea = cast(:linea as app.linea) and v.unidades > 0
        order by v.unidades desc, v.item_code limit 100
    """), p).all()
    return AnalisisVentas(meses=meses, actualizado_en=actualizado, serie=[PuntoSerie(**f._mapping) for f in serie],
                          articulos=[ArticuloVenta(**f._mapping) for f in articulos])
