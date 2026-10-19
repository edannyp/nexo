"""Código equivalente de los fabricados (ADR 0018) y equivalencia con un importado (ADR 0005); propuesta UX §6.4 y §6.7.

- Capturar el código (ItemCode, OEM o proveedor) no cambia ni bloquea el estado del artículo; si es el ItemCode de un importado de la
  misma categoría, la base sugiere la equivalencia (trigger `al_cambiar_codigo_equivalente`). Cambiarlo borra su validación.
- Validar el código lo hace un supervisor o administrador con una foto propia validada (`fn_validar_codigo_equivalente`).
- Confirmar la equivalencia y heredar (parte y aplicaciones como sugerencias, `fn_heredar_de_equivalente`) sí edita el artículo:
  misma regla que la ficha.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import Connection, text

from ..auth.dependencias import Rol, Usuario, UsuarioActual, requiere_rol
from ..auth.registro import fijar_actor
from ..core.bd import Conexion
from ..core.errores import Problema
from ..core.negocio import reglas_de_negocio
from .edicion import articulo, bloquear_para_editar, razon_no_editable, subir_version
from .emparejamiento import MedidasPanal, medidas_articulo
from .imagenes import FirmadorOpcional
from .tipo import TipoArticulo

router = APIRouter(tags=["equivalencia"])

ROLES_CAPTURA = {Rol.OPERADOR, Rol.SUPERVISOR, Rol.ADMINISTRADOR}
ROLES_VALIDA = {Rol.SUPERVISOR, Rol.ADMINISTRADOR}
Captura = Annotated[Usuario, Depends(requiere_rol(*ROLES_CAPTURA))]
Valida = Annotated[Usuario, Depends(requiere_rol(*ROLES_VALIDA))]


class TarjetaImportado(BaseModel):
    item_code: str
    descripcion: str | None
    estado: str
    medidas: MedidasPanal
    foto_url: str | None
    aplicaciones: int                       # confirmadas: las que se heredan
    partes: int
    equivalencia: str                       # SUGERIDA / CONFIRMADA / DESCARTADA
    confirmada_por: str | None


class Equivalencia(BaseModel):
    item_code: str
    version: int
    es_fabricado: bool
    codigo_equivalente: str | None
    sugerencias: list[str]                  # de codigo_anterior (SAP)
    estado_codigo: str                      # SIN_CODIGO / ESPERA_FOTO / LISTO_PARA_VALIDAR / VALIDADO
    capturado_por: str | None
    capturado_en: datetime | None
    validado_por: str | None
    validado_en: datetime | None
    fotos_validadas: int
    puede_capturar: bool
    puede_validar: bool
    editable: bool                          # para confirmar y heredar (reserva, Pendiente o Rechazado)
    razon_no_editable: str | None
    importado: TarjetaImportado | None


class Codigo(BaseModel):
    codigo: str | None = Field(None, max_length=60, description="Vacío para quitarlo")


class Confirmar(BaseModel):
    version: int
    heredar: bool = True


class Herencia(BaseModel):
    partes: int
    aplicaciones_sugeridas: int


class EquivalenciaConfirmada(BaseModel):
    equivalencia: Equivalencia
    heredado: Herencia | None


class Fabricado(BaseModel):
    item_code: str
    descripcion: str | None
    estado: str
    codigo_anterior: list[str]
    codigo_equivalente: str | None
    estado_codigo: str
    fotos_validadas: int
    importado: str | None                   # ItemCode del importado equivalente (sugerido o confirmado)


class RevisionFabricados(BaseModel):
    total: int
    por_estado: dict[str, int]
    fabricados: list[Fabricado]


ESTADOS_CODIGO = ("SIN_CODIGO", "ESPERA_FOTO", "LISTO_PARA_VALIDAR", "VALIDADO")


def _bloqueado_por_otro(a, usuario: Usuario) -> None:
    if a.reservado and a.asignado_a != usuario.id:
        raise Problema(409, "Está reservado por otro usuario", f"{a.reservado_por} lo está trabajando.")


def cargar(c: Connection, item_code: str, usuario: Usuario, firmador) -> Equivalencia:
    a = articulo(c, item_code)
    r = c.execute(text("""
        select v.estado_codigo::text as estado_codigo, v.fotos_validadas, cp.nombre as capturado_por, vp.nombre as validado_por
        from app.v_revision_fabricados v
        left join app.usuario cp on cp.id = v.codigo_equivalente_por left join app.usuario vp on vp.id = v.codigo_equivalente_validado_por
        where v.id = :a
    """), {"a": a.id}).one_or_none()
    importado = None
    eq = c.execute(text("""
        select i.*, i.estado::text as estado_txt, e.estado::text as estado_eq, u.nombre as confirmada_por,
               (select count(*) from app.articulo_aplicacion x where x.articulo_id = i.id and x.confirmado_por is not null) as n_apl,
               (select count(*) from app.articulo_parte x where x.articulo_id = i.id) as n_partes,
               (select f.minio_objeto from app.articulo_imagen f where f.articulo_id = i.id and f.origen = 'PROPIA'
                order by f.validada desc, f.orden limit 1) as foto, (select f.minio_bucket from app.articulo_imagen f
                where f.articulo_id = i.id and f.origen = 'PROPIA' order by f.validada desc, f.orden limit 1) as foto_bucket
        from app.articulo_equivalencia e join app.articulo i on i.id = e.importado_id left join app.usuario u on u.id = e.confirmado_por
        where e.fabricado_id = :a and e.estado <> 'DESCARTADA'
        order by (e.estado = 'CONFIRMADA') desc, (i.item_code = :codigo) desc, e.id desc limit 1
    """), {"a": a.id, "codigo": a.codigo_equivalente}).one_or_none()
    if eq is not None:
        m = medidas_articulo(c, eq)
        importado = TarjetaImportado(
            item_code=eq.item_code, descripcion=eq.descripcion, estado=eq.estado_txt,
            medidas=MedidasPanal(alto=m.alto, largo=m.largo, ancho=m.ancho),
            foto_url=firmador.firmar(eq.foto, eq.foto_bucket) if firmador and eq.foto else None,
            aplicaciones=eq.n_apl, partes=eq.n_partes, equivalencia=eq.estado_eq, confirmada_por=eq.confirmada_por)
    c.rollback()
    es_fabricado = a.linea == "FABRICADO"
    razon = razon_no_editable(a, usuario)
    return Equivalencia(
        item_code=a.item_code, version=a.version, es_fabricado=es_fabricado, codigo_equivalente=a.codigo_equivalente,
        sugerencias=[x for x in (a.codigo_anterior or []) if x and x != a.codigo_equivalente],
        estado_codigo=r.estado_codigo if r else "SIN_CODIGO", capturado_por=r.capturado_por if r else None,
        capturado_en=a.codigo_equivalente_en, validado_por=r.validado_por if r else None, validado_en=a.codigo_equivalente_validado_en,
        fotos_validadas=r.fotos_validadas if r else 0,
        puede_capturar=es_fabricado and a.activo and bool(usuario.roles & ROLES_CAPTURA),
        puede_validar=bool(r) and r.estado_codigo == "LISTO_PARA_VALIDAR" and bool(usuario.roles & ROLES_VALIDA),
        editable=razon is None and es_fabricado, razon_no_editable=razon if es_fabricado else "Solo los fabricados tienen equivalente.",
        importado=importado)


@router.get("/articulos/{item_code}/equivalencia", response_model=Equivalencia,
            summary="Código equivalente del fabricado, su estado y la tarjeta del importado equivalente")
def obtener_equivalencia(item_code: str, usuario: UsuarioActual, c: Conexion, firmador: FirmadorOpcional) -> Equivalencia:
    return cargar(c, item_code, usuario, firmador)


@router.put("/articulos/{item_code}/equivalencia", response_model=Equivalencia,
            summary="Capturar o cambiar el código equivalente (borra su validación; no cambia el estado del artículo)",
            responses={409: {"description": "Reservado por otro o no es fabricado"}})
def capturar_codigo_equivalente(item_code: str, datos: Codigo, usuario: Captura, c: Conexion, firmador: FirmadorOpcional
                                ) -> Equivalencia:
    with c.begin():
        fijar_actor(c, usuario.id)
        a = articulo(c, item_code, bloquear=True)
        if a.linea != "FABRICADO" or not a.activo:
            raise Problema(409, "Solo los fabricados activos tienen código equivalente")
        _bloqueado_por_otro(a, usuario)
        c.execute(text("update app.articulo set codigo_equivalente = nullif(trim(:c), '') where id = :a"),
                  {"c": datos.codigo or "", "a": a.id})
    return cargar(c, item_code, usuario, firmador)


@router.post("/articulos/{item_code}/equivalencia/validar", response_model=Equivalencia,
             summary="Validar el código equivalente (supervisor o administrador; requiere foto propia validada)",
             responses={422: {"description": "Sin código o sin foto validada"}})
def validar_codigo_equivalente(item_code: str, usuario: Valida, c: Conexion, firmador: FirmadorOpcional) -> Equivalencia:
    with c.begin():
        fijar_actor(c, usuario.id)
        a = articulo(c, item_code, bloquear=True)
        _bloqueado_por_otro(a, usuario)
        with reglas_de_negocio():
            c.execute(text("select app.fn_validar_codigo_equivalente(:a, :u)"), {"a": a.id, "u": usuario.id})
    return cargar(c, item_code, usuario, firmador)


@router.post("/articulos/{item_code}/equivalencia/confirmar", response_model=EquivalenciaConfirmada,
             summary="Confirmar la equivalencia con el importado y, opcionalmente, heredar su parte y aplicaciones como sugerencias",
             responses={409: {"description": "No editable o versión distinta"}, 422: {"description": "Sin importado sugerido"}})
def confirmar_equivalencia(item_code: str, datos: Confirmar, usuario: UsuarioActual, c: Conexion, firmador: FirmadorOpcional
                           ) -> EquivalenciaConfirmada:
    heredado = None
    with c.begin():
        fijar_actor(c, usuario.id)
        a = bloquear_para_editar(c, item_code, usuario, datos.version)
        confirmada = c.execute(text("""
            update app.articulo_equivalencia set estado = 'CONFIRMADA', confirmado_por = :u, confirmado_en = now()
            where id = (select e.id from app.articulo_equivalencia e join app.articulo i on i.id = e.importado_id
                        where e.fabricado_id = :a and e.estado <> 'DESCARTADA'
                        order by (e.estado = 'CONFIRMADA') desc, (i.item_code = :codigo) desc, e.id desc limit 1)
            returning id
        """), {"a": a.id, "u": usuario.id, "codigo": a.codigo_equivalente}).first()
        if confirmada is None:
            raise Problema(422, "No hay importado equivalente",
                           "Captura como código equivalente el ItemCode de un importado de la misma categoría.")
        if datos.heredar:
            with reglas_de_negocio():
                r = c.execute(text("select app.fn_heredar_de_equivalente(:a, :u)"), {"a": a.id, "u": usuario.id}).scalar_one()
            heredado = Herencia(partes=r["partes"], aplicaciones_sugeridas=r["aplicaciones_sugeridas"])
        subir_version(c, a.id)
    return EquivalenciaConfirmada(equivalencia=cargar(c, item_code, usuario, firmador), heredado=heredado)


@router.get("/fabricados", response_model=RevisionFabricados,
            summary="Revisión de fabricados de la categoría: código equivalente y su estado")
def listar_fabricados(_: Captura, tipo: TipoArticulo, c: Conexion,
                      estado_codigo: Annotated[str | None, Query(pattern="^(SIN_CODIGO|ESPERA_FOTO|LISTO_PARA_VALIDAR|VALIDADO)$")] = None,
                      q: Annotated[str | None, Query(max_length=60)] = None,
                      limite: Annotated[int, Query(ge=1, le=200)] = 50, desde: Annotated[int, Query(ge=0)] = 0) -> RevisionFabricados:
    p = {"cat": tipo.categoria_id, "e": estado_codigo, "q": f"%{(q or '').strip()}%", "lim": limite, "off": desde}
    conteo = dict(c.execute(text("""select estado_codigo::text, count(*) from app.v_revision_fabricados where categoria_id = :cat
                                    group by 1"""), p).all())
    filas = c.execute(text("""
        select v.item_code, v.descripcion, v.estado::text as estado, v.codigo_anterior, v.codigo_equivalente,
               v.estado_codigo::text as estado_codigo, v.fotos_validadas,
               (select i.item_code from app.articulo_equivalencia e join app.articulo i on i.id = e.importado_id
                where e.fabricado_id = v.id and e.estado <> 'DESCARTADA' order by (e.estado = 'CONFIRMADA') desc, e.id desc limit 1)
                 as importado,
               count(*) over () as total
        from app.v_revision_fabricados v
        where v.categoria_id = :cat and (cast(:e as text) is null or v.estado_codigo::text = :e)
          and (v.item_code ilike :q or v.descripcion ilike :q or coalesce(v.codigo_equivalente, '') ilike :q
               or array_to_string(v.codigo_anterior, ' ') ilike :q)
        order by array_position(array['LISTO_PARA_VALIDAR', 'SIN_CODIGO', 'ESPERA_FOTO', 'VALIDADO'], v.estado_codigo::text), v.item_code
        limit :lim offset :off
    """), p).all()
    return RevisionFabricados(
        total=filas[0].total if filas else 0, por_estado={e: conteo.get(e, 0) for e in ESTADOS_CODIGO},
        fabricados=[Fabricado(item_code=f.item_code, descripcion=f.descripcion, estado=f.estado, codigo_anterior=f.codigo_anterior or [],
                              codigo_equivalente=f.codigo_equivalente, estado_codigo=f.estado_codigo, fotos_validadas=f.fotos_validadas,
                              importado=f.importado) for f in filas])
