"""Revisión periódica del catálogo maestro (ADR 0012): si una parte emparejada con un artículo ya validado se fusionó, se descartó o
ya no existe en Consolidación, se crea una tarea de verificación CAMBIO_CATALOGO. Solo lee Consolidación. Repetible."""

import json
from dataclasses import dataclass, field
from itertools import batched

from sqlalchemy import Connection, text

from ..adapters.consolidacion import CatalogoMaestro

LOTE = 1000


@dataclass
class ResultadoCatalogo:
    partes: int = 0
    tareas: int = 0
    cambios: dict[str, int] = field(default_factory=dict)        # FUSIONADA / DESCARTADA / NO_EXISTE → partes


def revisar_catalogo(c: Connection, maestro: CatalogoMaestro) -> ResultadoCatalogo:
    res = ResultadoCatalogo()
    vinculos = c.execute(text("""
        select ap.articulo_id, ap.parte_id from app.articulo_parte ap join app.articulo a on a.id = ap.articulo_id
        where a.activo and a.estado in ('VALIDADO', 'SINCRONIZADO')
    """)).all()
    c.rollback()
    partes = sorted({v.parte_id for v in vinculos})
    res.partes = len(partes)
    cambiadas: dict[int, dict] = {}
    for lote in batched(partes, LOTE, strict=False):
        resumenes = maestro.resumenes(lote)
        for parte_id in lote:
            r = resumenes.get(parte_id)
            if r is None:
                cambiadas[parte_id] = {"estado": "NO_EXISTE"}
            elif r.estado != "ACTIVA":
                cambiadas[parte_id] = {"estado": r.estado, "fusionada_en_id": r.fusionada_en_id}
    for d in cambiadas.values():
        res.cambios[d["estado"]] = res.cambios.get(d["estado"], 0) + 1

    with c.begin():
        c.execute(text("select set_config('app.usuario_id', 'PROCESO:REVISAR_CATALOGO', true)"))
        for v in vinculos:
            if v.parte_id in cambiadas:
                res.tareas += c.execute(text("""
                    insert into app.tarea_verificacion (articulo_id, origen, detalle)
                    values (:a, 'CAMBIO_CATALOGO', cast(:d as jsonb)) on conflict do nothing
                """), {"a": v.articulo_id, "d": json.dumps({"parte_id": v.parte_id, **cambiadas[v.parte_id]})}).rowcount
    return res
