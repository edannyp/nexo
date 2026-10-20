"""Importación inicial de las fotos propias que ya están en MinIO (ADR 0013). Solo lee MinIO; escribe en Nexo. Repetible."""

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from sqlalchemy import Connection, text

from ..adapters.minio import PREFIJO, FuenteFotos

EXTENSIONES = {".webp", ".jpg", ".jpeg", ".png"}


@dataclass
class ResultadoFotos:
    importadas: int = 0
    ya_estaban: int = 0
    articulos: int = 0
    carpetas_sin_articulo: list[str] = field(default_factory=list)   # p. ej. RAD00617_REVISIÓN: se reportan, no se asocian
    no_son_imagen: list[str] = field(default_factory=list)            # p. ej. TEST.svg


def _orden(nombre: str) -> int:
    m = re.search(r"_(\d+)$", PurePosixPath(nombre).stem)
    return int(m.group(1)) if m else 1


def importar_fotos(c: Connection, fuente: FuenteFotos) -> ResultadoFotos:
    res = ResultadoFotos()
    por_articulo: dict[str, list[str]] = {}
    # Solo las carpetas de las categorías en alcance ({código}_{NOMBRE}); las demás no son asunto de Nexo
    codigos = c.execute(text("select codigo_sap from app.categoria where activa order by codigo_sap")).scalars().all()
    c.rollback()
    claves = (k for codigo in codigos for k in fuente.listar(f"{PREFIJO}{codigo}_"))
    for clave in claves:
        partes = clave.split("/")
        if len(partes) != 4 or PurePosixPath(clave).suffix.lower() not in EXTENSIONES:
            res.no_son_imagen.append(clave)
            continue
        por_articulo.setdefault(partes[2].strip().upper(), []).append(clave)

    with c.begin():
        ids = dict(c.execute(text("select item_code, id from app.articulo where item_code = any(:c)"),
                             {"c": list(por_articulo)}).tuples().all())
        sin = Counter()
        for item, claves in sorted(por_articulo.items()):
            if item not in ids:
                sin[item] += len(claves)
                continue
            res.articulos += 1
            for clave in sorted(claves, key=_orden):
                nueva = c.execute(text("""
                    insert into app.articulo_imagen (articulo_id, origen, minio_bucket, minio_objeto, orden)
                    values (:a, 'PROPIA', :b, :o, :n)
                    on conflict (minio_bucket, minio_objeto) where minio_objeto is not null do nothing
                    returning id
                """), {"a": ids[item], "b": fuente.bucket, "o": clave, "n": _orden(clave)}).first()
                if nueva:
                    res.importadas += 1
                else:
                    res.ya_estaban += 1
        res.carpetas_sin_articulo = sorted(sin)
    return res
