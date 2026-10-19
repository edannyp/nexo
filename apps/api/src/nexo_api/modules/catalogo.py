"""Catálogo maestro, vista inversa (propuesta UX §6.8): qué partes de Consolidación tienen artículo en Nexo y cuáles no, y desde una
parte, los artículos que podrían ser ella (mismo puntaje que el emparejamiento, al revés). Vincular se hace en el artículo."""

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import Connection, text

from ..adapters.consolidacion import Candidato, Medidas, normalizar_numero
from ..auth.dependencias import UsuarioActual
from ..core.bd import Conexion
from ..core.errores import Problema
from .emparejamiento import Maestro, MedidasPanal, ParteCatalogo, Tolerancia, parte_catalogo, puntuar, requerir
from .tipo import TipoArticulo

router = APIRouter(prefix="/catalogo", tags=["catalogo"])


class ParteConArticulos(BaseModel):
    parte: ParteCatalogo
    articulos: int                          # artículos de Nexo vinculados


class PaginaCatalogo(BaseModel):
    disponible: bool
    part_terminology_id: int | None
    total: int
    partes: list[ParteConArticulos]


class ArticuloVinculado(BaseModel):
    item_code: str
    descripcion: str | None
    estado: str
    linea: str
    es_principal: bool


class ArticuloCandidato(BaseModel):
    item_code: str
    descripcion: str | None
    estado: str
    linea: str
    medidas: MedidasPanal
    puntaje: int
    razones: list[str]


class ArticulosDeParte(BaseModel):
    parte: ParteCatalogo
    vinculados: list[ArticuloVinculado]
    candidatos: list[ArticuloCandidato]


def _pt(c: Connection, categoria_id: int) -> int | None:
    return c.execute(text("select part_terminology_id_defecto from app.categoria where id = :c"), {"c": categoria_id}).scalar_one_or_none()


@router.get("", response_model=PaginaCatalogo, summary="Partes del catálogo maestro del tipo elegido, con cuántos artículos las usan")
def listar_catalogo(_: UsuarioActual, tipo: TipoArticulo, c: Conexion, m: Maestro, q: Annotated[str | None, Query(max_length=80)] = None,
                    sin_articulo: bool = False, tolerancia: Tolerancia = 10, limite: Annotated[int, Query(ge=1, le=100)] = 30,
                    desde: Annotated[int, Query(ge=0)] = 0) -> PaginaCatalogo:
    pt = _pt(c, tipo.categoria_id)
    vinculadas = dict(c.execute(text("""select ap.parte_id, count(*) from app.articulo_parte ap join app.articulo a on a.id = ap.articulo_id
                                        where a.categoria_id = :cat group by 1"""), {"cat": tipo.categoria_id}).all())
    c.rollback()
    if m is None or pt is None:
        return PaginaCatalogo(disponible=m is not None, part_terminology_id=pt, total=0, partes=[])
    total, partes = m.listar(pt, q, tolerancia, vinculadas if sin_articulo else [], limite, desde)
    return PaginaCatalogo(disponible=True, part_terminology_id=pt, total=total,
                          partes=[ParteConArticulos(parte=parte_catalogo(p), articulos=vinculadas.get(p.parte_id, 0)) for p in partes])


@router.get("/{parte_id}/articulos", response_model=ArticulosDeParte,
            summary="Artículos de Nexo vinculados a la parte y los que podrían serlo (medidas, números, vehículos)")
def articulos_de_parte(parte_id: int, _: UsuarioActual, tipo: TipoArticulo, c: Conexion, m: Maestro,
                       tolerancia: Tolerancia = 10) -> ArticulosDeParte:
    d = requerir(m).detalle(parte_id)
    if d is None:
        raise Problema(404, "La parte no existe en el catálogo maestro")
    vinculados = c.execute(text("""
        select a.item_code, a.descripcion, a.estado::text as estado, a.linea::text as linea, ap.es_principal
        from app.articulo_parte ap join app.articulo a on a.id = ap.articulo_id where ap.parte_id = :p order by a.item_code
    """), {"p": parte_id}).all()
    nums = sorted({normalizar_numero(n.numero) for n in d.numeros} - {""})
    bvs = sorted({x.base_vehicle_id for x in d.aplicaciones if x.base_vehicle_id})
    mp = d.parte.medidas
    filas = c.execute(text("""
        with m as (
          select a.id, a.item_code, a.descripcion, a.estado::text as estado, a.linea::text as linea, a.numero_parte_proveedor,
                 a.codigo_anterior,
                 coalesce((select valor_num from app.articulo_atributo x where x.articulo_id = a.id and x.paid = 267),
                          a.panal_alto_mm) as alto,
                 coalesce((select valor_num from app.articulo_atributo x where x.articulo_id = a.id and x.paid = 269),
                          a.panal_largo_mm) as largo,
                 coalesce((select valor_num from app.articulo_atributo x where x.articulo_id = a.id and x.paid = 268),
                          a.panal_ancho_mm) as ancho
          from app.articulo a
          where a.activo and a.categoria_id = :cat
            and not exists (select 1 from app.articulo_parte ap where ap.articulo_id = a.id and ap.parte_id = :p)
        )
        select m.*,
               (select array_agg(n) from unnest(array_append(coalesce(m.codigo_anterior, '{}'), m.numero_parte_proveedor)) n
                where regexp_replace(upper(n), '[^A-Z0-9]', '', 'g') = any(cast(:nums as text[]))) as numeros,
               (select count(distinct x.base_vehicle_id) from app.articulo_aplicacion x
                where x.articulo_id = m.id and x.base_vehicle_id = any(cast(:bvs as integer[]))) as comunes
        from m
        where (cast(:alto as numeric) is not null and cast(:largo as numeric) is not null and (
                (abs(m.alto - cast(:alto as numeric)) <= :tol and abs(m.largo - cast(:largo as numeric)) <= :tol) or
                (abs(m.alto - cast(:largo as numeric)) <= :tol and abs(m.largo - cast(:alto as numeric)) <= :tol)))
           or regexp_replace(upper(coalesce(m.numero_parte_proveedor, '')), '[^A-Z0-9]', '', 'g') = any(cast(:nums as text[]))
           or exists (select 1 from unnest(m.codigo_anterior) n
                      where regexp_replace(upper(n), '[^A-Z0-9]', '', 'g') = any(cast(:nums as text[])))
           or exists (select 1 from app.articulo_aplicacion x
                      where x.articulo_id = m.id and x.base_vehicle_id = any(cast(:bvs as integer[])))
        limit 100
    """), {"cat": tipo.categoria_id, "p": parte_id, "nums": nums, "bvs": bvs, "alto": mp.alto, "largo": mp.largo,
           "tol": tolerancia}).all()
    c.rollback()
    candidatos = []
    for f in filas:
        art = Medidas(f.alto, f.largo, f.ancho)
        puntaje, razones, _ = puntuar(art, Candidato(d.parte, [f"Número {n}" for n in (f.numeros or [])], f.comunes), tolerancia)
        candidatos.append(ArticuloCandidato(item_code=f.item_code, descripcion=f.descripcion, estado=f.estado, linea=f.linea,
                                            medidas=MedidasPanal(alto=f.alto, largo=f.largo, ancho=f.ancho), puntaje=puntaje,
                                            razones=razones))
    candidatos.sort(key=lambda x: (-x.puntaje, x.item_code))
    return ArticulosDeParte(
        parte=parte_catalogo(d.parte),
        vinculados=[ArticuloVinculado(item_code=v.item_code, descripcion=v.descripcion, estado=v.estado, linea=v.linea,
                                      es_principal=v.es_principal) for v in vinculados],
        candidatos=candidatos[:20])
