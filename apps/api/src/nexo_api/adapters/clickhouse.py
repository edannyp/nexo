"""Ventas desde ClickHouse (solo lectura, datos de apoyo — ADR 0022). Solo unidades: nunca se leen montos."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Protocol

import clickhouse_connect

from ..core.config import Config


@dataclass(frozen=True)
class VentaMes:
    item_code: str
    mes: date
    unidades: float


@dataclass(frozen=True)
class Referencia:
    item_code: str
    abcxyz_empresa: str | None
    ultima_venta: date | None


class FuenteVentas(Protocol):
    def ventas_mensuales(self, desde: date) -> Iterator[VentaMes]: ...
    def referencias(self) -> Iterator[Referencia]: ...


class VentasClickHouse:
    def __init__(self, cfg: Config):
        if not cfg.clickhouse_host:
            raise RuntimeError("Falta CLICKHOUSE_HOST: no hay de dónde leer las ventas.")
        self.c = clickhouse_connect.get_client(host=cfg.clickhouse_host, port=cfg.clickhouse_port,
                                               username=cfg.clickhouse_user, password=cfg.clickhouse_password)

    def ventas_mensuales(self, desde: date) -> Iterator[VentaMes]:
        r = self.c.query("""
            select id_articulo, mes, sum(unidades)
            from rlt_mov.mart_ventas_articulo_mes
            where mes >= {desde:Date}
            group by id_articulo, mes
        """, parameters={"desde": desde})
        for item, mes, unidades in r.result_rows:
            yield VentaMes(item, mes, float(unidades))

    def referencias(self) -> Iterator[Referencia]:
        clases = dict(self.c.query("""
            select id_articulo, argMax(categoria_abcxyz, execution_date)
            from rlt_ml.latest_clasificacion_abcxyz group by id_articulo
        """).result_rows)
        ultimas = self.c.query("select id_articulo, max(ultima_venta) from rlt_mov.mart_ventas_articulo_mes group by id_articulo")
        vistos = set()
        for item, ultima in ultimas.result_rows:
            vistos.add(item)
            yield Referencia(item, clases.get(item), ultima)
        for item, clase in clases.items():
            if item not in vistos:
                yield Referencia(item, clase, None)
