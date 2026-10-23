"""Aplicaciones del artículo (propuesta UX §6.4 "Pestaña Aplicaciones", decisión UX 4).

Una aplicación de vehículo = vehículo base (año) + submodelo + motor, de AutoCare o MercadoExterno. Lo que el operador agrega con el
selector queda confirmado; lo sugerido (heredado de un equivalente o del catálogo maestro) se confirma aparte y solo si está completo.
Un grupo (mismo vehículo, submodelo y motor) es el **vehículo principal** (ADR 0025): obligatorio para enviar a validar; si no coincide
con SAP, la base abre el hallazgo VEHICULO_DISTINTO.
Misma regla de edición que la ficha: reserva propia, Pendiente o Rechazado, versión del artículo.
"""

import difflib
import unicodedata

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ..adapters.vehiculos import Vehiculos
from ..auth.dependencias import Usuario, UsuarioActual
from ..auth.registro import fijar_actor
from ..core.bd import Conexion
from ..core.errores import Problema
from .edicion import articulo, bloquear_para_editar, puede_tomar, razon_no_editable, subir_version
from .vehiculos import CatalogoOpcional, OpcionVehiculo, requerir_vehiculos

router = APIRouter(prefix="/articulos/{item_code}/aplicaciones", tags=["aplicaciones"])


class AplicacionItem(BaseModel):
    id: int
    anio: int | None
    base_vehicle_id: int | None
    sub_model_id: int | None
    engine_config_id: int | None
    equipment_base_id: int | None
    origen: str
    confirmado: bool
    completa: bool                         # tiene submodelo y motor (o es de equipo): se puede confirmar


class GrupoAplicacion(BaseModel):
    """Un mismo vehículo (marca, modelo, submodelo, motor) en uno o varios años."""
    titulo: str                            # "Toyota Pickup"
    principal: bool                        # es el vehículo principal del artículo
    detalle: str                           # "DLX · 2.4L L4 22R · Gasolina"
    anios: str                             # "1986–1990, 1992"
    confirmados: int
    sugeridos: int
    items: list[AplicacionItem]


class SugerenciaSap(BaseModel):
    """Lo que SAP dice del vehículo, y su traducción al catálogo cuando se encuentra."""
    marca: str | None
    modelo: str | None
    desde: int | None
    hasta: int | None
    marca_catalogo: OpcionVehiculo | None
    modelos_candidatos: list[OpcionVehiculo]   # del catálogo, ordenados por parecido con el modelo de SAP


class Aplicaciones(BaseModel):
    version: int
    editable: bool
    razon_no_editable: str | None
    puede_tomar: bool                      # no es editable solo porque falta tomarlo (la pestaña ofrece "Tomar")
    catalogo_disponible: bool
    sugerencia_sap: SugerenciaSap | None
    grupos: list[GrupoAplicacion]


class NuevaAplicacion(BaseModel):
    base_vehicle_id: int
    sub_model_id: int
    engine_config_id: int


class Agregar(BaseModel):
    version: int
    items: list[NuevaAplicacion] = Field(min_length=1, max_length=200)
    principal: bool = False                # estas aplicaciones pasan a ser el vehículo principal (reemplaza al anterior)


class PorIds(BaseModel):
    version: int
    ids: list[int] = Field(min_length=1, max_length=500)


def rangos(anios: list[int]) -> str:
    """[1986, 1987, 1988, 1990] → '1986–1988, 1990'."""
    partes, ini, prev = [], None, None
    for a in sorted(set(anios)):
        if ini is None:
            ini = prev = a
        elif a == prev + 1:
            prev = a
        else:
            partes.append(f"{ini}–{prev}" if ini != prev else str(ini))
            ini = prev = a
    if ini is not None:
        partes.append(f"{ini}–{prev}" if ini != prev else str(ini))
    return ", ".join(partes)


def _norm(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return "".join(ch for ch in s.upper() if ch.isalnum())


def _copia_catalogo(v: Vehiculos | None, ids) -> dict:
    """Marca, modelo y año de cada vehículo base, para guardarlos con la aplicación (agrupar, filtrar, entregar a SAP)."""
    if v is None:
        return {}
    try:
        return v.base_vehicles(ids)
    except Problema:
        return {}


def _sugerencia(c, a, v: Vehiculos | None) -> SugerenciaSap | None:
    if not (a.marca_vehiculo or a.modelo_vehiculo or a.anio_desde):
        return None
    s = SugerenciaSap(marca=a.marca_vehiculo, modelo=a.modelo_vehiculo, desde=a.anio_desde, hasta=a.anio_hasta or a.anio_desde,
                      marca_catalogo=None, modelos_candidatos=[])
    if v is None or not s.desde or not a.marca_vehiculo:
        return s
    try:
        marcas = v.marcas(s.desde, s.hasta)
        # Homologación confirmada de la marca SAP; si no hay, por nombre
        homologada = c.execute(text("""select make_id from app.homologacion_marca
                                       where marca_codigo_sap = :m and estado = 'CONFIRMADA'"""),
                               {"m": a.marca_vehiculo_codigo}).scalar_one_or_none()
        marca = next((m for m in marcas if m.id == homologada), None) or next(
            (m for m in marcas if _norm(m.nombre) == _norm(a.marca_vehiculo)), None)
        if marca:
            s.marca_catalogo = OpcionVehiculo(id=marca.id, nombre=marca.nombre)
            modelos = v.modelos(marca.id, s.desde, s.hasta)
            homologado = c.execute(text("""select model_id from app.homologacion_modelo
                                           where marca_codigo_sap = :m and modelo_codigo_sap = :o and estado = 'CONFIRMADA'"""),
                                   {"m": a.marca_vehiculo_codigo, "o": a.modelo_vehiculo_codigo}).scalar_one_or_none()
            objetivo = _norm(a.modelo_vehiculo)
            puntaje = {m.id: 2.0 if m.id == homologado else difflib.SequenceMatcher(None, objetivo, _norm(m.nombre)).ratio()
                       for m in modelos}
            s.modelos_candidatos = [OpcionVehiculo(id=m.id, nombre=m.nombre)
                                    for m in sorted(modelos, key=lambda m: -puntaje[m.id])[:6]]
    except Problema:
        pass
    return s


def cargar_aplicaciones(c, item_code: str, usuario: Usuario, v: Vehiculos | None) -> Aplicaciones:
    a = articulo(c, item_code)
    filas = c.execute(text("""
        select id, base_vehicle_id, sub_model_id, engine_config_id, equipment_base_id, origen::text as origen,
               confirmado_por is not null as confirmado, es_principal
        from app.articulo_aplicacion where articulo_id = :a order by id
    """), {"a": a.id}).all()
    sugerencia = _sugerencia(c, a, v)
    c.rollback()

    bvs, subs, mots = {}, {}, {}
    if v is not None and filas:
        try:
            bvs = v.base_vehicles(f.base_vehicle_id for f in filas if f.base_vehicle_id)
            subs = v.submodelos(f.sub_model_id for f in filas if f.sub_model_id)
            mots = v.motores(f.engine_config_id for f in filas if f.engine_config_id)
        except Problema:
            v = None

    grupos: dict[tuple, dict] = {}
    for f in filas:
        bv = bvs.get(f.base_vehicle_id)
        if f.equipment_base_id:
            titulo, detalle = f"Equipo {f.equipment_base_id}", "Maquinaria"
        else:
            titulo = f"{bv.marca} {bv.modelo}" if bv else f"Vehículo {f.base_vehicle_id}"
            detalle = " · ".join([subs.get(f.sub_model_id, "Sin submodelo") if f.sub_model_id else "Sin submodelo",
                                  mots.get(f.engine_config_id, "Sin motor") if f.engine_config_id else "Sin motor"])
        g = grupos.setdefault((titulo, detalle), {"titulo": titulo, "detalle": detalle, "items": [], "principal": False})
        g["principal"] |= f.es_principal
        g["items"].append(AplicacionItem(
            id=f.id, anio=bv.anio if bv else None, base_vehicle_id=f.base_vehicle_id, sub_model_id=f.sub_model_id,
            engine_config_id=f.engine_config_id, equipment_base_id=f.equipment_base_id, origen=f.origen, confirmado=f.confirmado,
            completa=bool(f.equipment_base_id or (f.sub_model_id and f.engine_config_id))))
    salida = []
    for g in sorted(grupos.values(), key=lambda g: (not g["principal"], g["titulo"], g["detalle"])):
        items = sorted(g["items"], key=lambda i: (i.anio or 0, i.id))
        salida.append(GrupoAplicacion(titulo=g["titulo"], principal=g["principal"], detalle=g["detalle"],
                                      anios=rangos([i.anio for i in items if i.anio]),
                                      confirmados=sum(i.confirmado for i in items), sugeridos=sum(not i.confirmado for i in items),
                                      items=items))
    razon = razon_no_editable(a, usuario)
    return Aplicaciones(version=a.version, editable=razon is None, razon_no_editable=razon, puede_tomar=puede_tomar(a, usuario),
                        catalogo_disponible=v is not None,
                        sugerencia_sap=sugerencia, grupos=salida)


@router.get("", response_model=Aplicaciones, summary="Aplicaciones del artículo agrupadas por vehículo, con la sugerencia de SAP")
def listar_aplicaciones(item_code: str, usuario: UsuarioActual, c: Conexion, v: CatalogoOpcional) -> Aplicaciones:
    return cargar_aplicaciones(c, item_code, usuario, v)


@router.post("", response_model=Aplicaciones, summary="Agregar aplicaciones elegidas en el selector (quedan confirmadas)",
             responses={409: {"description": "No editable o versión distinta"}})
def agregar_aplicaciones(item_code: str, datos: Agregar, usuario: UsuarioActual, c: Conexion, v: CatalogoOpcional) -> Aplicaciones:
    bvs = _copia_catalogo(v, [it.base_vehicle_id for it in datos.items])
    with c.begin():
        fijar_actor(c, usuario.id)
        a = bloquear_para_editar(c, item_code, usuario, datos.version)
        if datos.principal:
            c.execute(text("update app.articulo_aplicacion set es_principal = false where articulo_id = :a and es_principal"),
                      {"a": a.id})
        for it in datos.items:
            bv = bvs.get(it.base_vehicle_id)
            p = {"a": a.id, "bv": it.base_vehicle_id, "sm": it.sub_model_id, "ec": it.engine_config_id, "u": usuario.id,
                 "pr": datos.principal, "mk": bv.make_id if bv else None, "mo": bv.model_id if bv else None,
                 "anio": bv.anio if bv else None, "marca": bv.marca if bv else None, "modelo": bv.modelo if bv else None}
            # Si ya estaba (p. ej. sugerida por herencia), se confirma; si no, se agrega confirmada
            confirmada = c.execute(text("""
                update app.articulo_aplicacion set confirmado_por = :u, confirmado_en = now(), es_principal = es_principal or :pr,
                  make_id = :mk, model_id = :mo, anio = :anio, marca = :marca, modelo = :modelo
                where articulo_id = :a and base_vehicle_id = :bv and sub_model_id = :sm and engine_config_id = :ec
                  and equipment_base_id is null and transmission_id is null
                returning id"""), p).first()
            if not confirmada:
                c.execute(text("""
                    insert into app.articulo_aplicacion (articulo_id, base_vehicle_id, sub_model_id, engine_config_id, origen,
                                                         confirmado_por, confirmado_en, es_principal, make_id, model_id, anio,
                                                         marca, modelo)
                    values (:a, :bv, :sm, :ec, 'MANUAL', :u, now(), :pr, :mk, :mo, :anio, :marca, :modelo)"""), p)
        subir_version(c, a.id)
    return cargar_aplicaciones(c, item_code, usuario, v)


@router.post("/confirmar", response_model=Aplicaciones, summary="Confirmar aplicaciones sugeridas (deben tener submodelo y motor)",
             responses={422: {"description": "Alguna está incompleta"}})
def confirmar_aplicaciones(item_code: str, datos: PorIds, usuario: UsuarioActual, c: Conexion, v: CatalogoOpcional) -> Aplicaciones:
    try:
        with c.begin():
            fijar_actor(c, usuario.id)
            a = bloquear_para_editar(c, item_code, usuario, datos.version)
            c.execute(text("""update app.articulo_aplicacion set confirmado_por = :u, confirmado_en = now()
                              where articulo_id = :a and id = any(:ids) and confirmado_por is null"""),
                      {"a": a.id, "ids": datos.ids, "u": usuario.id})
            subir_version(c, a.id)
    except IntegrityError as e:
        if "aplicacion_vehiculo_completa" not in str(e.orig):
            raise
        raise Problema(422, "Completa submodelo y motor antes de confirmar",
                       "Hay aplicaciones sugeridas sin submodelo o sin motor: elígelas en el selector.") from e
    return cargar_aplicaciones(c, item_code, usuario, v)


@router.post("/principal", response_model=Aplicaciones, summary="Marcar un grupo de aplicaciones como el vehículo principal",
             responses={422: {"description": "Las aplicaciones no son un mismo vehículo, submodelo y motor"}})
def marcar_principal(item_code: str, datos: PorIds, usuario: UsuarioActual, c: Conexion, v: CatalogoOpcional) -> Aplicaciones:
    a0 = articulo(c, item_code)
    filas = c.execute(text("""select id, base_vehicle_id from app.articulo_aplicacion
                              where articulo_id = :a and id = any(:ids) and make_id is null and base_vehicle_id is not null"""),
                      {"a": a0.id, "ids": datos.ids}).all()
    c.rollback()
    bvs = requerir_vehiculos(v).base_vehicles(f.base_vehicle_id for f in filas) if filas else {}
    with c.begin():
        fijar_actor(c, usuario.id)
        a = bloquear_para_editar(c, item_code, usuario, datos.version)
        for f in filas:                        # las que llegaron sin copia del catálogo (p. ej. del catálogo maestro)
            bv = bvs.get(f.base_vehicle_id)
            if bv:
                c.execute(text("""update app.articulo_aplicacion set make_id = :mk, model_id = :mo, anio = :anio, marca = :marca,
                                  modelo = :modelo where id = :id"""),
                          {"id": f.id, "mk": bv.make_id, "mo": bv.model_id, "anio": bv.anio, "marca": bv.marca, "modelo": bv.modelo})
        elegidas = c.execute(text("""select count(*) as n,
                                            count(distinct (make_id, model_id, sub_model_id, equipment_base_id)) as grupos
                                     from app.articulo_aplicacion where articulo_id = :a and id = any(:ids)"""),
                             {"a": a.id, "ids": datos.ids}).one()
        if elegidas.n != len(set(datos.ids)) or elegidas.grupos != 1:
            raise Problema(422, "Elige un solo vehículo",
                           "El vehículo principal es una misma marca, modelo y submodelo (en uno o varios años), o un mismo equipo.")
        c.execute(text("""update app.articulo_aplicacion set es_principal = (id = any(:ids))
                          where articulo_id = :a and (es_principal or id = any(:ids))"""), {"a": a.id, "ids": datos.ids})
        subir_version(c, a.id)
    return cargar_aplicaciones(c, item_code, usuario, v)


@router.post("/quitar", response_model=Aplicaciones, summary="Quitar aplicaciones del artículo")
def quitar_aplicaciones(item_code: str, datos: PorIds, usuario: UsuarioActual, c: Conexion, v: CatalogoOpcional) -> Aplicaciones:
    with c.begin():
        fijar_actor(c, usuario.id)
        a = bloquear_para_editar(c, item_code, usuario, datos.version)
        c.execute(text("delete from app.articulo_aplicacion where articulo_id = :a and id = any(:ids)"), {"a": a.id, "ids": datos.ids})
        subir_version(c, a.id)
    return cargar_aplicaciones(c, item_code, usuario, v)
