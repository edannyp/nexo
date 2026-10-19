"""Catálogo maestro en Consolidación (`articulos_consolidacion`, solo lectura; ADR 0011). Nexo solo guarda el `parte_id` emparejado.

Medidas del panal en mm: alto (PAdb 267), largo (269) y ancho (268), como en `catalogo.v_parte_busqueda`. Alto y largo se comparan como
par sin orden (algunas fuentes los publican invertidos).
"""

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from sqlalchemy import Engine, text

from .externa import disponible


def normalizar_numero(n: str | None) -> str:
    """Igual que `numero_norm` en Consolidación: mayúsculas y solo [A-Z0-9]."""
    return re.sub(r"[^A-Z0-9]", "", (n or "").upper())


@dataclass(frozen=True)
class Medidas:
    alto: Decimal | None = None
    largo: Decimal | None = None
    ancho: Decimal | None = None


@dataclass
class ResumenParte:
    parte_id: int
    part_terminology_id: int | None
    tipo_parte: str | None
    descripcion: str | None
    numeros: str | None
    medidas: Medidas
    n_aplicaciones: int
    n_fuentes: int
    imagen_url: str | None
    estado: str = "ACTIVA"
    fusionada_en_id: int | None = None


@dataclass
class Candidato:
    parte: ResumenParte
    numeros_coinciden: list[str] = field(default_factory=list)   # "OEM 16400-35090"
    vehiculos_comunes: int = 0


@dataclass
class NumeroParte:
    tipo: str
    marca: str | None
    numero: str


@dataclass
class AtributoParte:
    paid: int
    valor_num: Decimal | None
    uom_code: str | None
    valid_value_id: int | None
    valor_texto: str | None
    valor_original: str | None


@dataclass
class AplicacionParte:
    base_vehicle_id: int | None
    sub_model_id: int | None
    engine_config_id: int | None
    equipment_base_id: int | None


@dataclass
class ImagenParte:
    tipo: str
    url: str | None
    minio_bucket: str | None
    minio_objeto: str | None


@dataclass
class FuenteParte:
    fuente: str
    id_en_fuente: str
    url: str | None


@dataclass
class DetalleParte:
    parte: ResumenParte
    numeros: list[NumeroParte]
    atributos: list[AtributoParte]
    aplicaciones: list[AplicacionParte]
    imagenes: list[ImagenParte]
    fuentes: list[FuenteParte]


class CatalogoMaestro(Protocol):
    def candidatos(self, part_terminology_id: int, medidas: Medidas, tolerancia: int, numeros: Iterable[str],
                   base_vehicle_ids: Iterable[int], limite: int = 60) -> list[Candidato]: ...
    def buscar(self, part_terminology_id: int | None, q: str, tolerancia: int, limite: int = 30) -> list[ResumenParte]: ...
    def resumenes(self, ids: Iterable[int]) -> dict[int, ResumenParte]: ...
    def listar(self, part_terminology_id: int, q: str | None, tolerancia: int, excluir: Iterable[int], limite: int,
               desde: int) -> tuple[int, list[ResumenParte]]: ...
    def detalle(self, parte_id: int) -> DetalleParte | None: ...


_RESUMEN = """b.parte_id, b.part_terminology_id, b.tipo_parte, b.descripcion, b.numeros, b.panal_alto_mm, b.panal_largo_mm,
              b.panal_ancho_mm, b.n_aplicaciones, b.n_fuentes, b.imagen_url"""

# Alto y largo dentro de la tolerancia en cualquier orden
_MEDIDAS = """(cast(:alto as numeric) is not null and cast(:largo as numeric) is not null and (
                 (abs(b.panal_alto_mm - cast(:alto as numeric)) <= :tol and abs(b.panal_largo_mm - cast(:largo as numeric)) <= :tol) or
                 (abs(b.panal_alto_mm - cast(:largo as numeric)) <= :tol and abs(b.panal_largo_mm - cast(:alto as numeric)) <= :tol)))"""

_MEDIDAS_TEXTO = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*[x×*]\s*(\d+(?:[.,]\d+)?)(?:\s*[x×*]\s*(\d+(?:[.,]\d+)?))?\s*$", re.IGNORECASE)


def medidas_de_texto(q: str) -> Medidas | None:
    """'400x518x26' o '400 x 518' → Medidas; None si no son medidas."""
    m = _MEDIDAS_TEXTO.match(q)
    if not m:
        return None
    a, b, c = (Decimal(x.replace(",", ".")) if x else None for x in m.groups())
    return Medidas(a, b, c)


def _resumen(f, estado: str = "ACTIVA", fusionada_en_id: int | None = None) -> ResumenParte:
    return ResumenParte(f.parte_id, f.part_terminology_id, f.tipo_parte, f.descripcion, f.numeros,
                        Medidas(f.panal_alto_mm, f.panal_largo_mm, f.panal_ancho_mm), f.n_aplicaciones or 0, f.n_fuentes or 0,
                        f.imagen_url, estado, fusionada_en_id)


class Consolidacion:
    def __init__(self, motor: Engine):
        self.motor = motor

    def _filas(self, sql: str, p: dict) -> list:
        with disponible("Catálogo maestro"), self.motor.connect() as c:
            c.execute(text("set transaction read only"))
            return c.execute(text(sql), p).all()

    def candidatos(self, part_terminology_id: int, medidas: Medidas, tolerancia: int, numeros: Iterable[str],
                   base_vehicle_ids: Iterable[int], limite: int = 60) -> list[Candidato]:
        nums = sorted({n for n in (normalizar_numero(x) for x in numeros) if len(n) >= 3})
        bvs = sorted(set(base_vehicle_ids))
        filas = self._filas(f"""
            with n as (select parte_id, array_agg(distinct tipo::text || ' ' || numero) as coinciden
                       from catalogo.parte_numero where numero_norm = any(cast(:nums as text[])) group by parte_id),
                 v as (select parte_id, count(distinct base_vehicle_id) as comunes
                       from catalogo.parte_aplicacion where base_vehicle_id = any(cast(:bvs as integer[])) group by parte_id)
            select {_RESUMEN}, coalesce(n.coinciden, '{{}}') as numeros_coinciden, coalesce(v.comunes, 0) as vehiculos_comunes
            from catalogo.v_parte_busqueda b left join n using (parte_id) left join v using (parte_id)
            where b.part_terminology_id = :pt and (n.parte_id is not null or v.parte_id is not null or {_MEDIDAS})
            limit :lim
        """, {"pt": part_terminology_id, "nums": nums, "bvs": bvs, "alto": medidas.alto, "largo": medidas.largo,
              "tol": tolerancia, "lim": limite})
        return [Candidato(_resumen(f), sorted(f.numeros_coinciden), f.vehiculos_comunes) for f in filas]

    def buscar(self, part_terminology_id: int | None, q: str, tolerancia: int, limite: int = 30) -> list[ResumenParte]:
        """Búsqueda manual: medidas (`400x518x26`), número (parcial) o palabras de la descripción."""
        medidas = medidas_de_texto(q)
        p = {"pt": part_terminology_id, "lim": limite, "tol": tolerancia}
        if medidas:
            filtro = _MEDIDAS + (" and (cast(:ancho as numeric) is null or abs(b.panal_ancho_mm - cast(:ancho as numeric)) <= :tol)")
            p |= {"alto": medidas.alto, "largo": medidas.largo, "ancho": medidas.ancho}
        else:
            filtro = """(exists (select 1 from catalogo.parte_numero n where n.parte_id = b.parte_id and n.numero_norm like :num)
                         or b.descripcion ilike all (cast(:palabras as text[])))"""
            num = normalizar_numero(q)
            p |= {"num": f"%{num}%" if len(num) >= 3 else "", "palabras": [f"%{w}%" for w in q.split()] or ["%"]}
        filas = self._filas(f"""
            select {_RESUMEN} from catalogo.v_parte_busqueda b
            where (cast(:pt as integer) is null or b.part_terminology_id = :pt) and {filtro}
            order by b.n_fuentes desc, b.parte_id limit :lim
        """, p)
        return [_resumen(f) for f in filas]

    def listar(self, part_terminology_id: int, q: str | None, tolerancia: int, excluir: Iterable[int], limite: int,
               desde: int) -> tuple[int, list[ResumenParte]]:
        """Catálogo (vista inversa): partes activas del tipo, opcionalmente filtradas como la búsqueda manual y sin las de `excluir`."""
        p: dict = {"pt": part_terminology_id, "excluir": sorted(set(excluir)), "lim": limite, "off": desde, "tol": tolerancia}
        filtro = "true"
        if q and q.strip():
            medidas = medidas_de_texto(q)
            if medidas:
                filtro = _MEDIDAS + " and (cast(:ancho as numeric) is null or abs(b.panal_ancho_mm - cast(:ancho as numeric)) <= :tol)"
                p |= {"alto": medidas.alto, "largo": medidas.largo, "ancho": medidas.ancho}
            else:
                num = normalizar_numero(q)
                filtro = """(exists (select 1 from catalogo.parte_numero n where n.parte_id = b.parte_id and n.numero_norm like :num)
                             or b.descripcion ilike all (cast(:palabras as text[])))"""
                p |= {"num": f"%{num}%" if len(num) >= 3 else "", "palabras": [f"%{w}%" for w in q.split()]}
        filas = self._filas(f"""
            select {_RESUMEN}, count(*) over () as total from catalogo.v_parte_busqueda b
            where b.part_terminology_id = :pt and b.parte_id <> all(cast(:excluir as bigint[])) and {filtro}
            order by b.n_fuentes desc, b.parte_id limit :lim offset :off
        """, p)
        return (filas[0].total if filas else 0), [_resumen(f) for f in filas]

    def resumenes(self, ids: Iterable[int]) -> dict[int, ResumenParte]:
        """También partes fusionadas o descartadas (para avisar en lo ya emparejado)."""
        ids = sorted(set(ids))
        if not ids:
            return {}
        filas = self._filas("""
            select p.id as parte_id, p.part_terminology_id, pt.nombre as tipo_parte, p.descripcion, p.estado::text as estado,
                   p.fusionada_en_id, b.numeros, b.panal_alto_mm, b.panal_largo_mm, b.panal_ancho_mm, b.n_aplicaciones, b.n_fuentes,
                   b.imagen_url
            from catalogo.parte p left join ref.part_terminology pt using (part_terminology_id)
            left join catalogo.v_parte_busqueda b on b.parte_id = p.id
            where p.id = any(:ids)
        """, {"ids": ids})
        return {f.parte_id: _resumen(f, f.estado, f.fusionada_en_id) for f in filas}

    def detalle(self, parte_id: int) -> DetalleParte | None:
        resumen = self.resumenes([parte_id]).get(parte_id)
        if resumen is None:
            return None
        p = {"p": parte_id}
        numeros = [NumeroParte(f.tipo, f.marca, f.numero) for f in self._filas("""
            select distinct n.tipo::text as tipo, m.nombre as marca, n.numero from catalogo.parte_numero n
            left join catalogo.marca_pieza m on m.id = n.marca_pieza_id where n.parte_id = :p order by 1, 3""", p)]
        atributos = [AtributoParte(*f) for f in self._filas("""
            select distinct on (a.paid) a.paid, a.valor_num, a.uom_code, a.valid_value_id, a.valor_texto, a.valor_original
            from catalogo.parte_atributo a join catalogo.registro_fuente r on r.id = a.registro_fuente_id
            join catalogo.fuente f on f.id = r.fuente_id
            where a.parte_id = :p order by a.paid, f.prioridad, a.id""", p)]
        aplicaciones = [AplicacionParte(*f) for f in self._filas("""
            select distinct base_vehicle_id, sub_model_id, engine_config_id, equipment_base_id from catalogo.parte_aplicacion
            where parte_id = :p order by 1, 2, 3""", p)]
        imagenes = [ImagenParte(*f) for f in self._filas("""
            select tipo::text, url, minio_bucket, minio_objeto from catalogo.parte_imagen where parte_id = :p order by orden, id""", p)]
        fuentes = [FuenteParte(*f) for f in self._filas("""
            select f.nombre, r.id_en_fuente, r.url from catalogo.registro_fuente r join catalogo.fuente f on f.id = r.fuente_id
            where r.parte_id = :p and r.vigente order by f.prioridad, r.id""", p)]
        return DetalleParte(resumen, numeros, atributos, aplicaciones, imagenes, fuentes)
