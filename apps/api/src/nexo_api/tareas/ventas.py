"""Refresca la copia de apoyo de ventas (ADR 0022): unidades por artículo y mes, y la clasificación de la empresa."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import Connection, text

from ..adapters.clickhouse import FuenteVentas


@dataclass(frozen=True)
class ResultadoVentas:
    desde: date
    articulos: int
    filas: int
    referencias: int


def inicio_ventana(hoy: date, meses_periodo: int) -> date:
    """Primer mes necesario: dos periodos completos (actual y anterior, para la tendencia) antes del mes en curso."""
    total = hoy.year * 12 + (hoy.month - 1) - 2 * meses_periodo
    return date(total // 12, total % 12 + 1, 1)


def actualizar_ventas(c: Connection, fuente: FuenteVentas, hoy: date | None = None) -> ResultadoVentas:
    """Reemplaza la ventana de meses en `app.venta_mensual` (solo artículos que existen en Nexo) en una transacción."""
    with c.begin():
        meses = int(c.execute(text("select valor::int from meta.parametro where clave = 'ventas.meses_periodo'")).scalar_one())
        desde = inicio_ventana(hoy or date.today(), meses)
        conocidos = set(c.execute(text("select item_code from app.articulo")).scalars())

        filas = [{"i": v.item_code, "m": v.mes, "u": v.unidades} for v in fuente.ventas_mensuales(desde) if v.item_code in conocidos]
        c.execute(text("delete from app.venta_mensual where mes >= :desde"), {"desde": desde})
        if filas:
            c.execute(text("insert into app.venta_mensual (item_code, mes, unidades) values (:i, :m, :u)"), filas)

        refs = [{"i": r.item_code, "c": r.abcxyz_empresa, "u": r.ultima_venta} for r in fuente.referencias() if r.item_code in conocidos]
        if refs:
            c.execute(text("""
                insert into app.venta_referencia (item_code, abcxyz_empresa, ultima_venta) values (:i, :c, :u)
                on conflict (item_code) do update set abcxyz_empresa = excluded.abcxyz_empresa,
                  ultima_venta = excluded.ultima_venta, actualizado_en = now()
            """), refs)
        articulos = len({f["i"] for f in filas})
        c.execute(text("insert into meta.carga_ventas (meses, articulos, filas) values (:m, :a, :f)"),
                  {"m": meses, "a": articulos, "f": len(filas)})
    return ResultadoVentas(desde=desde, articulos=articulos, filas=len(filas), referencias=len(refs))
