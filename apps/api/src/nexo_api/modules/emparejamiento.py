"""Emparejamiento con el catálogo maestro (propuesta UX §6.4 "Pestaña Emparejamiento y diagramas", ADR 0011).

Candidatos de Consolidación con puntaje y el porqué (medidas como par sin orden ±tolerancia, números, vehículos en común),
comparación lado a lado y vínculo en `app.articulo_parte` (una principal). Al vincular se pueden traer los atributos y aplicaciones
de la parte como sugerencias (origen CONSOLIDACION, sin confirmar). Misma regla de edición que la ficha.
"""

from decimal import Decimal
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.exc import DBAPIError

from ..adapters.consolidacion import Candidato, CatalogoMaestro, Consolidacion, DetalleParte, Medidas, ResumenParte
from ..adapters.minio import FotosMinio
from ..adapters.vehiculos import Vehiculos
from ..auth.dependencias import Usuario, UsuarioActual
from ..auth.registro import fijar_actor
from ..core.bd import Conexion
from ..core.config import config
from ..core.errores import Problema
from .aplicaciones import rangos
from .edicion import articulo, bloquear_para_editar, razon_no_editable, subir_version
from .vehiculos import CatalogoOpcional

router = APIRouter(tags=["emparejamiento"])

PAID_ALTO, PAID_LARGO, PAID_ANCHO = 267, 269, 268
Tolerancia = Annotated[int, Query(ge=0, le=50, description="mm de tolerancia en las medidas")]


@lru_cache
def _catalogo() -> CatalogoMaestro | None:
    url = config().url_externa("consolidacion")
    return Consolidacion(create_engine(url, pool_pre_ping=True, pool_size=3)) if url else None


def obtener_catalogo_maestro() -> CatalogoMaestro | None:
    """Dependencia sustituible en pruebas. None si la API no tiene CONSOLIDACION_* configurado."""
    return _catalogo()


@lru_cache
def _fotos() -> FotosMinio | None:
    try:
        return FotosMinio(config())
    except RuntimeError:
        return None


def obtener_firmador() -> FotosMinio | None:
    """Firma URLs de diagramas guardados en MinIO (rlt-diagramas). None sin MINIO_*."""
    return _fotos()


Maestro = Annotated[CatalogoMaestro | None, Depends(obtener_catalogo_maestro)]
Firmador = Annotated[FotosMinio | None, Depends(obtener_firmador)]


def requerir(m: CatalogoMaestro | None) -> CatalogoMaestro:
    if m is None:
        raise Problema(503, "Catálogo maestro no configurado", "Faltan CONSOLIDACION_* en el entorno de la API.")
    return m


# ---------------------------------------------------------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------------------------------------------------------
class MedidasPanal(BaseModel):
    alto: Decimal | None
    largo: Decimal | None
    ancho: Decimal | None


class ParteCatalogo(BaseModel):
    parte_id: int
    tipo_parte: str | None
    descripcion: str | None
    numeros: str | None
    medidas: MedidasPanal
    n_aplicaciones: int
    n_fuentes: int
    imagen_url: str | None
    estado: str
    fusionada_en_id: int | None


class CandidatoParte(BaseModel):
    parte: ParteCatalogo
    puntaje: int
    razones: list[str]
    invertida: bool                        # alto y largo coinciden, pero al revés


class ParteVinculada(BaseModel):
    parte_id: int
    es_principal: bool
    origen: str
    confirmado_por: str | None
    confirmado_en: str
    parte: ParteCatalogo | None            # None si Consolidación no está disponible o ya no la tiene


class Traidos(BaseModel):
    atributos: int
    aplicaciones: int


class Emparejamiento(BaseModel):
    version: int
    part_terminology_id: int | None
    editable: bool
    razon_no_editable: str | None
    catalogo_disponible: bool
    medidas: MedidasPanal
    tolerancia: int
    vinculadas: list[ParteVinculada]
    candidatos: list[CandidatoParte]
    traidos: Traidos | None = None


class FilaComparacion(BaseModel):
    paid: int
    etiqueta: str
    articulo: str | None
    parte: str | None
    coincide: bool | None                  # None si falta uno de los dos
    diferencia: str | None                 # "+6 mm"


class NumeroCatalogo(BaseModel):
    tipo: str
    marca: str | None
    numero: str


class ImagenCatalogo(BaseModel):
    tipo: str
    url: str


class FuenteCatalogo(BaseModel):
    fuente: str
    id_en_fuente: str
    url: str | None


class Comparacion(BaseModel):
    parte: ParteCatalogo
    invertida: bool
    filas: list[FilaComparacion]
    numeros: list[NumeroCatalogo]
    imagenes: list[ImagenCatalogo]
    fuentes: list[FuenteCatalogo]
    vehiculos: list[str]                   # "Toyota Pickup 1986–1994"
    vehiculos_comunes: int
    vinculada: bool


class Vincular(BaseModel):
    version: int
    parte_id: int
    principal: bool = False
    traer_sugerencias: bool = True


class PorParte(BaseModel):
    version: int
    parte_id: int


# ---------------------------------------------------------------------------------------------------------------------------
# Puntaje
# ---------------------------------------------------------------------------------------------------------------------------
def _mm(x: Decimal | None) -> str:
    return f"{x.normalize():f}" if x is not None else "—"


def _cerca(a: Decimal | None, b: Decimal | None, tol: int) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol


def puntuar(art: Medidas, c: Candidato, tol: int) -> tuple[int, list[str], bool]:
    """Puntaje 0–100 y las razones. Alto+largo 40 (35 si invertidos), ancho 15, número 35, vehículos en común 10."""
    p, razones, invertida = 0, [], False
    m = c.parte.medidas
    if _cerca(art.alto, m.alto, tol) and _cerca(art.largo, m.largo, tol):
        p += 40
        razones.append(f"Alto y largo {_mm(m.alto)}×{_mm(m.largo)}" + (" iguales" if (art.alto, art.largo) == (m.alto, m.largo)
                                                                         else f" (±{tol} mm)"))
    elif _cerca(art.alto, m.largo, tol) and _cerca(art.largo, m.alto, tol):
        p, invertida = p + 35, True
        razones.append(f"Alto y largo invertidos ({_mm(m.alto)}×{_mm(m.largo)})")
    if _cerca(art.ancho, m.ancho, tol):
        p += 15
        razones.append(f"Ancho {_mm(m.ancho)}")
    elif art.ancho is not None and m.ancho is not None:
        d = m.ancho - art.ancho
        razones.append(f"Ancho distinto ({'+' if d > 0 else ''}{_mm(d)} mm)")
    if c.numeros_coinciden:
        p += 35
        razones.append(f"{', '.join(c.numeros_coinciden[:2])} coincide")
    if c.vehiculos_comunes:
        p += 10
        razones.append(f"{c.vehiculos_comunes} {'vehículo' if c.vehiculos_comunes == 1 else 'vehículos'} en común")
    return min(p, 100), razones, invertida


# ---------------------------------------------------------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------------------------------------------------------
def _parte(r: ResumenParte) -> ParteCatalogo:
    return ParteCatalogo(parte_id=r.parte_id, tipo_parte=r.tipo_parte, descripcion=r.descripcion, numeros=r.numeros,
                         medidas=MedidasPanal(alto=r.medidas.alto, largo=r.medidas.largo, ancho=r.medidas.ancho),
                         n_aplicaciones=r.n_aplicaciones, n_fuentes=r.n_fuentes, imagen_url=r.imagen_url, estado=r.estado,
                         fusionada_en_id=r.fusionada_en_id)


def medidas_articulo(c: Connection, a) -> Medidas:
    """Lo que hay en Nexo (ficha) y, si falta, lo de SAP."""
    valores = dict(c.execute(text("""select paid, valor_num from app.articulo_atributo
                                     where articulo_id = :a and paid = any(:p) and valor_num is not null"""),
                             {"a": a.id, "p": [PAID_ALTO, PAID_LARGO, PAID_ANCHO]}).all())
    return Medidas(valores.get(PAID_ALTO, a.panal_alto_mm), valores.get(PAID_LARGO, a.panal_largo_mm),
                   valores.get(PAID_ANCHO, a.panal_ancho_mm))


def _vehiculos_articulo(c: Connection, articulo_id: int) -> set[int]:
    return {r[0] for r in c.execute(text("""select base_vehicle_id from app.articulo_aplicacion
                                            where articulo_id = :a and base_vehicle_id is not null"""), {"a": articulo_id})}


def cargar(c: Connection, item_code: str, usuario: Usuario, m: CatalogoMaestro | None, tolerancia: int,
           traidos: Traidos | None = None) -> Emparejamiento:
    a = articulo(c, item_code)
    medidas = medidas_articulo(c, a)
    bvs = _vehiculos_articulo(c, a.id)
    vinculadas = c.execute(text("""
        select ap.parte_id, ap.es_principal, ap.origen::text as origen, u.nombre as confirmado_por, ap.confirmado_en
        from app.articulo_parte ap left join app.usuario u on u.id = ap.confirmado_por
        where ap.articulo_id = :a order by ap.es_principal desc, ap.confirmado_en
    """), {"a": a.id}).all()
    c.rollback()

    resumenes, candidatos = {}, []
    if m is not None:
        try:
            resumenes = m.resumenes(v.parte_id for v in vinculadas)
            if a.part_terminology_id:
                numeros = [a.numero_parte_proveedor or "", *(a.codigo_anterior or [])]
                ya = {v.parte_id for v in vinculadas}
                for cand in m.candidatos(a.part_terminology_id, medidas, tolerancia, numeros, bvs):
                    if cand.parte.parte_id in ya:
                        continue
                    puntaje, razones, invertida = puntuar(medidas, cand, tolerancia)
                    candidatos.append(CandidatoParte(parte=_parte(cand.parte), puntaje=puntaje, razones=razones, invertida=invertida))
        except Problema:
            m = None
    candidatos.sort(key=lambda x: (-x.puntaje, -x.parte.n_fuentes, x.parte.parte_id))
    razon = razon_no_editable(a, usuario)
    return Emparejamiento(
        version=a.version, part_terminology_id=a.part_terminology_id, editable=razon is None, razon_no_editable=razon,
        catalogo_disponible=m is not None,
        medidas=MedidasPanal(alto=medidas.alto, largo=medidas.largo, ancho=medidas.ancho), tolerancia=tolerancia,
        vinculadas=[ParteVinculada(parte_id=v.parte_id, es_principal=v.es_principal, origen=v.origen, confirmado_por=v.confirmado_por,
                                   confirmado_en=v.confirmado_en.isoformat(),
                                   parte=_parte(resumenes[v.parte_id]) if v.parte_id in resumenes else None) for v in vinculadas],
        candidatos=candidatos[:20], traidos=traidos)


@router.get("/articulos/{item_code}/emparejamiento", response_model=Emparejamiento,
            summary="Partes vinculadas y candidatos del catálogo maestro con puntaje y el porqué")
def obtener_emparejamiento(item_code: str, usuario: UsuarioActual, c: Conexion, m: Maestro, tolerancia: Tolerancia = 10
                           ) -> Emparejamiento:
    return cargar(c, item_code, usuario, m, tolerancia)


@router.get("/catalogo/partes", response_model=list[ParteCatalogo],
            summary="Búsqueda manual en el catálogo maestro: medidas (400x518x26), número o descripción")
def buscar_partes(_: UsuarioActual, m: Maestro, q: Annotated[str, Query(min_length=2, max_length=80)],
                  part_terminology_id: int | None = None, tolerancia: Tolerancia = 10) -> list[ParteCatalogo]:
    return [_parte(r) for r in requerir(m).buscar(part_terminology_id, q.strip(), tolerancia)]


def _texto_valor(f, opciones: dict[int, str]) -> str | None:
    if f is None:
        return None
    if f.valid_value_id is not None:
        return opciones.get(f.valid_value_id, str(f.valid_value_id))
    if f.valor_num is not None:
        return f"{Decimal(f.valor_num).normalize():f}" + (f" {f.uom_code.lower()}" if f.uom_code else "")
    return f.valor_texto


def comparar_filas(config_filas, art: dict, parte: dict, opciones: dict[int, str], tol: int) -> list[FilaComparacion]:
    filas = []
    for r in config_filas:
        va, vp = art.get(r.paid), parte.get(r.paid)
        coincide = diferencia = None
        if va is not None and vp is not None:
            if va.valid_value_id is not None or vp.valid_value_id is not None:
                coincide = va.valid_value_id == vp.valid_value_id
            elif va.valor_num is not None and vp.valor_num is not None:
                d = Decimal(vp.valor_num) - Decimal(va.valor_num)
                coincide = abs(d) <= (tol if r.requiere_uom else 0)
                diferencia = None if d == 0 else f"{d.normalize():+f}" + (" mm" if r.requiere_uom else "")
            else:
                coincide = (va.valor_texto or "").strip().lower() == (vp.valor_texto or "").strip().lower()
        if va is None and vp is None:
            continue
        filas.append(FilaComparacion(paid=r.paid, etiqueta=r.etiqueta, articulo=_texto_valor(va, opciones),
                                     parte=_texto_valor(vp, opciones), coincide=coincide, diferencia=diferencia))
    return filas


def _vehiculos_texto(v: Vehiculos | None, d: DetalleParte) -> list[str]:
    ids = [x.base_vehicle_id for x in d.aplicaciones if x.base_vehicle_id]
    if not ids:
        return []
    if v is None:
        return [f"{len(set(ids))} vehículos (catálogo de vehículos no disponible)"]
    try:
        bvs = v.base_vehicles(ids)
    except Problema:
        return [f"{len(set(ids))} vehículos"]
    grupos: dict[str, list[int]] = {}
    for i in set(ids):
        if i in bvs:
            grupos.setdefault(f"{bvs[i].marca} {bvs[i].modelo}", []).append(bvs[i].anio)
    return [f"{k} {rangos(a)}" for k, a in sorted(grupos.items())]


@router.get("/articulos/{item_code}/emparejamiento/{parte_id}", response_model=Comparacion,
            summary="Comparación lado a lado del artículo con una parte del catálogo maestro")
def comparar_parte(item_code: str, parte_id: int, _: UsuarioActual, c: Conexion, m: Maestro, v: CatalogoOpcional, firmador: Firmador,
                   tolerancia: Tolerancia = 10) -> Comparacion:
    d = requerir(m).detalle(parte_id)
    if d is None:
        raise Problema(404, "La parte no existe en el catálogo maestro")
    a = articulo(c, item_code)
    pt = a.part_terminology_id or d.parte.part_terminology_id
    config_filas = c.execute(text("""select paid, coalesce(etiqueta, nombre) as etiqueta, requiere_uom from meta.atributo_config
                                     where part_terminology_id = :pt and habilitado order by orden nulls last, paid"""),
                             {"pt": pt}).all()
    art = {f.paid: f for f in c.execute(text("""select paid, valor_num, uom_code, valid_value_id, valor_texto
                                                 from app.articulo_atributo where articulo_id = :a"""), {"a": a.id})}
    medidas = medidas_articulo(c, a)
    for paid, valor in ((PAID_ALTO, medidas.alto), (PAID_LARGO, medidas.largo), (PAID_ANCHO, medidas.ancho)):
        if paid not in art and valor is not None:                      # aún sin ficha: lo de SAP
            art[paid] = type("V", (), {"valor_num": valor, "uom_code": "MM", "valid_value_id": None, "valor_texto": None})()
    ids_valor = [x.valid_value_id for x in [*art.values(), *d.atributos] if x.valid_value_id]
    opciones = {r.valid_value_id: f"{r.valor} ({r.valor_es})" if r.valor_es else r.valor for r in c.execute(text("""
        select v.valid_value_id, v.valor, t.valor_es from meta.atributo_valor_permitido v
        left join meta.traduccion_valor t using (valid_value_id) where v.valid_value_id = any(:ids)"""), {"ids": ids_valor})}
    bvs = _vehiculos_articulo(c, a.id)
    vinculada = c.execute(text("select 1 from app.articulo_parte where articulo_id = :a and parte_id = :p"),
                          {"a": a.id, "p": parte_id}).first() is not None
    c.rollback()

    imagenes = []
    for i in d.imagenes:
        url = i.url
        if url is None and firmador is not None and i.minio_objeto:
            url = firmador.firmar(i.minio_objeto, i.minio_bucket)
        if url:
            imagenes.append(ImagenCatalogo(tipo=i.tipo, url=url))
    _, _, invertida = puntuar(medidas, Candidato(d.parte), tolerancia)
    return Comparacion(
        parte=_parte(d.parte), invertida=invertida,
        filas=comparar_filas(config_filas, art, {x.paid: x for x in d.atributos}, opciones, tolerancia),
        numeros=[NumeroCatalogo(tipo=n.tipo, marca=n.marca, numero=n.numero) for n in d.numeros], imagenes=imagenes,
        fuentes=[FuenteCatalogo(fuente=f.fuente, id_en_fuente=f.id_en_fuente, url=f.url) for f in d.fuentes],
        vehiculos=_vehiculos_texto(v, d),
        vehiculos_comunes=len(bvs & {x.base_vehicle_id for x in d.aplicaciones if x.base_vehicle_id}), vinculada=vinculada)


# ---------------------------------------------------------------------------------------------------------------------------
# Escritura
# ---------------------------------------------------------------------------------------------------------------------------
def _traer(c: Connection, a, d: DetalleParte) -> Traidos:
    """Atributos y aplicaciones de la parte como sugerencias. Nunca pisa lo que el artículo ya tiene."""
    habilitados = {r.paid: r for r in c.execute(text("""
        select paid, requiere_uom, uom_defecto from meta.atributo_config where part_terminology_id = :pt and habilitado"""),
        {"pt": a.part_terminology_id})}
    permitidos = {(r[0], r[1]) for r in c.execute(text("""select paid, valid_value_id from meta.atributo_valor_permitido
                                                           where part_terminology_id = :pt"""), {"pt": a.part_terminology_id})}
    n_atr = 0
    for x in d.atributos:
        r = habilitados.get(x.paid)
        if r is None or (x.valid_value_id is not None and (x.paid, x.valid_value_id) not in permitidos):
            continue
        if x.valid_value_id is None and x.valor_num is None and not x.valor_texto:
            continue
        uom = (x.uom_code or r.uom_defecto) if r.requiere_uom and x.valor_num is not None else None
        valor = {"num": x.valor_num if x.valid_value_id is None else None, "uom": uom, "vv": x.valid_value_id,
                 "txt": x.valor_texto if x.valid_value_id is None and x.valor_num is None else None}
        try:
            with c.begin_nested():
                n_atr += c.execute(text("""
                    insert into app.articulo_atributo (articulo_id, paid, valor_num, uom_code, valid_value_id, valor_texto, origen,
                                                       parte_id)
                    values (:a, :p, :num, :uom, :vv, :txt, 'CONSOLIDACION', :parte) on conflict (articulo_id, paid) do nothing
                """), {"a": a.id, "p": x.paid, "parte": d.parte.parte_id, **valor}).rowcount
        except DBAPIError:                     # un valor que la base no acepta no impide vincular: se omite
            continue
    n_apl = 0
    for x in d.aplicaciones:
        if not (x.base_vehicle_id or x.equipment_base_id):
            continue
        n_apl += c.execute(text("""
            insert into app.articulo_aplicacion (articulo_id, base_vehicle_id, equipment_base_id, sub_model_id, engine_config_id,
                                                 origen, parte_id)
            values (:a, :bv, :eq, :sm, :ec, 'CONSOLIDACION', :parte) on conflict do nothing
        """), {"a": a.id, "bv": x.base_vehicle_id, "eq": x.equipment_base_id, "sm": x.sub_model_id, "ec": x.engine_config_id,
               "parte": d.parte.parte_id}).rowcount
    return Traidos(atributos=n_atr, aplicaciones=n_apl)


@router.post("/articulos/{item_code}/partes", response_model=Emparejamiento,
             summary="Vincular una parte del catálogo maestro (opcionalmente como principal y trayendo sus datos como sugerencias)",
             responses={409: {"description": "No editable o versión distinta"}, 422: {"description": "Parte no válida"}})
def vincular_parte(item_code: str, datos: Vincular, usuario: UsuarioActual, c: Conexion, m: Maestro,
                   tolerancia: Tolerancia = 10) -> Emparejamiento:
    d = requerir(m).detalle(datos.parte_id)
    if d is None or d.parte.estado != "ACTIVA":
        raise Problema(422, "Esa parte no se puede vincular",
                       "No existe o ya no está activa en el catálogo maestro" +
                       (f" (se fusionó en la parte {d.parte.fusionada_en_id})." if d and d.parte.fusionada_en_id else "."))
    traidos = None
    with c.begin():
        fijar_actor(c, usuario.id)
        a = bloquear_para_editar(c, item_code, usuario, datos.version)
        if a.part_terminology_id and d.parte.part_terminology_id != a.part_terminology_id:
            raise Problema(422, "La parte es de otro tipo", f"El artículo es {a.part_terminology_id} y la parte "
                                                            f"{d.parte.part_terminology_id} ({d.parte.tipo_parte}).")
        hay = c.execute(text("select count(*) from app.articulo_parte where articulo_id = :a"), {"a": a.id}).scalar_one()
        principal = datos.principal or hay == 0                       # la primera queda como principal
        if principal:
            c.execute(text("update app.articulo_parte set es_principal = false where articulo_id = :a and es_principal"), {"a": a.id})
        c.execute(text("""
            insert into app.articulo_parte (articulo_id, parte_id, es_principal, origen, confirmado_por)
            values (:a, :p, :pr, 'CONSOLIDACION', :u)
            on conflict (articulo_id, parte_id) do update set es_principal = excluded.es_principal or app.articulo_parte.es_principal
        """), {"a": a.id, "p": datos.parte_id, "pr": principal, "u": usuario.id})
        if datos.traer_sugerencias:
            traidos = _traer(c, a, d)
        subir_version(c, a.id)
    return cargar(c, item_code, usuario, m, tolerancia, traidos)


@router.post("/articulos/{item_code}/partes/principal", response_model=Emparejamiento, summary="Marcar una parte vinculada como principal")
def marcar_parte_principal(item_code: str, datos: PorParte, usuario: UsuarioActual, c: Conexion, m: Maestro,
                           tolerancia: Tolerancia = 10) -> Emparejamiento:
    with c.begin():
        fijar_actor(c, usuario.id)
        a = bloquear_para_editar(c, item_code, usuario, datos.version)
        if not c.execute(text("select 1 from app.articulo_parte where articulo_id = :a and parte_id = :p"),
                         {"a": a.id, "p": datos.parte_id}).first():
            raise Problema(404, "Esa parte no está vinculada")
        c.execute(text("update app.articulo_parte set es_principal = false where articulo_id = :a and es_principal"), {"a": a.id})
        c.execute(text("update app.articulo_parte set es_principal = true where articulo_id = :a and parte_id = :p"),
                  {"a": a.id, "p": datos.parte_id})
        subir_version(c, a.id)
    return cargar(c, item_code, usuario, m, tolerancia)


@router.post("/articulos/{item_code}/partes/quitar", response_model=Emparejamiento,
             summary="Desvincular una parte (y quitar sus sugerencias aún sin confirmar)")
def desvincular_parte(item_code: str, datos: PorParte, usuario: UsuarioActual, c: Conexion, m: Maestro,
                      tolerancia: Tolerancia = 10) -> Emparejamiento:
    with c.begin():
        fijar_actor(c, usuario.id)
        a = bloquear_para_editar(c, item_code, usuario, datos.version)
        quitada = c.execute(text("delete from app.articulo_parte where articulo_id = :a and parte_id = :p returning es_principal"),
                            {"a": a.id, "p": datos.parte_id}).first()
        if quitada is None:
            raise Problema(404, "Esa parte no está vinculada")
        p = {"a": a.id, "p": datos.parte_id}
        c.execute(text("""delete from app.articulo_atributo where articulo_id = :a and parte_id = :p and origen = 'CONSOLIDACION'
                          and confirmado_por is null"""), p)
        c.execute(text("""delete from app.articulo_aplicacion where articulo_id = :a and parte_id = :p and origen = 'CONSOLIDACION'
                          and confirmado_por is null"""), p)
        if quitada.es_principal:                                      # la siguiente más antigua pasa a principal
            c.execute(text("""update app.articulo_parte set es_principal = true where id = (
                                select id from app.articulo_parte where articulo_id = :a order by confirmado_en, id limit 1)"""),
                      {"a": a.id})
        subir_version(c, a.id)
    return cargar(c, item_code, usuario, m, tolerancia)
