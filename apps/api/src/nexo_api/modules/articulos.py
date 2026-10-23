"""Artículos: listado con filtros (Explorar), detalle con requisitos y acciones, e historial (propuesta UX §6.2, §6.4)."""

import base64
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import Connection, text

from ..auth.dependencias import Rol, Usuario, UsuarioActual
from ..core.bd import Conexion
from ..core.errores import Problema
from .panorama import Estado
from .tipo import TipoArticulo

router = APIRouter(prefix="/articulos", tags=["articulos"])


class Orden(StrEnum):
    VENTA = "venta"            # clase y participación (por defecto: lo que más importa primero)
    CODIGO = "codigo"
    DESCRIPCION = "descripcion"
    ESTADO = "estado"
    ANIO = "anio"
    RECIENTE = "reciente"      # último cambio
    FALTANTES = "faltantes"


class Completitud(StrEnum):
    COMPLETA = "completa"
    INCOMPLETA = "incompleta"


class Reserva(StrEnum):
    MIA = "mia"
    LIBRE = "libre"
    OTROS = "otros"


class ArticuloFila(BaseModel):
    id: int
    item_code: str
    descripcion: str | None
    estado: Estado
    version: int
    marca_vehiculo: str | None
    modelo_vehiculo: str | None
    anio_desde: int | None
    anio_hasta: int | None
    vehiculo_principal: str | None # "Toyota Hilux 2005–2015" (ADR 0025); null si aún no lo tiene
    panal_alto_mm: Decimal | None
    panal_largo_mm: Decimal | None
    panal_ancho_mm: Decimal | None
    faltan: int                    # requisitos pendientes para enviar a revisión
    fotos: int
    emparejado: bool
    hallazgos: int
    clase: str | None
    participacion: Decimal | None
    tendencia: Decimal | None
    reservado_por: str | None      # nombre de quien lo tiene reservado (vigente)
    reservado_hasta: datetime | None
    actualizado_en: datetime


class PaginaArticulos(BaseModel):
    items: list[ArticuloFila]
    total: int
    next_cursor: str | None


_COLUMNAS = """
    a.id, a.item_code, a.descripcion, a.estado::text as estado, a.version, a.marca_vehiculo, a.modelo_vehiculo,
    a.anio_desde, a.anio_hasta, vp.texto as vehiculo_principal, a.panal_alto_mm, a.panal_largo_mm, a.panal_ancho_mm,
    cardinality(app.fn_requisitos_por_validar(a.id)) as faltan,
    (select count(*) from app.articulo_imagen i where i.articulo_id = a.id and i.origen = 'PROPIA') as fotos,
    exists (select 1 from app.articulo_parte x where x.articulo_id = a.id) as emparejado,
    (select count(*) from app.hallazgo_calidad_sap h where h.articulo_id = a.id and h.corregido_en is null) as hallazgos,
    v.clase, v.participacion, v.tendencia,
    case when a.asignado_hasta > now() then u.nombre end as reservado_por,
    case when a.asignado_hasta > now() then a.asignado_hasta end as reservado_hasta,
    a.actualizado_en
"""
_DESDE = """
    from app.articulo a
    left join (select articulo_id, clase, participacion, tendencia from app.v_indicador_venta
               where categoria_id = :cat and linea = cast(:linea as app.linea)) v on v.articulo_id = a.id
    left join app.usuario u on u.id = a.asignado_a
    left join lateral (
        select concat_ws(' ', min(x.marca), min(x.modelo), concat_ws('–', min(x.anio), nullif(max(x.anio), min(x.anio)))) as texto
        from app.articulo_aplicacion x where x.articulo_id = a.id and x.es_principal having count(*) > 0) vp on true
"""
_ORDEN = {
    Orden.VENTA: "coalesce(v.clase, 'Z'), v.participacion desc nulls last, a.item_code",
    Orden.CODIGO: "a.item_code",
    Orden.DESCRIPCION: "a.descripcion, a.item_code",
    Orden.ESTADO: "a.estado, a.item_code",
    Orden.ANIO: "a.anio_desde nulls last, a.item_code",
    Orden.RECIENTE: "a.actualizado_en desc, a.item_code",
    Orden.FALTANTES: "faltan desc, a.item_code",
}


def _cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode()


def _offset(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        return max(0, int(base64.urlsafe_b64decode(cursor.encode()).decode()))
    except ValueError as e:
        raise Problema(422, "Cursor no válido", errors=[{"campo": "cursor", "mensaje": "Vuelve a la primera página."}]) from e


@router.get("", response_model=PaginaArticulos, summary="Artículos del tipo elegido con filtros, orden y paginación")
def listar_articulos(
    usuario: UsuarioActual,
    tipo: TipoArticulo,
    c: Conexion,
    q: Annotated[str | None, Query(max_length=100, description="Código, número de parte o texto de la descripción")] = None,
    estado: Annotated[list[Estado] | None, Query()] = None,
    completitud: Completitud | None = None,
    con_foto: bool | None = None,
    emparejado: bool | None = None,
    con_hallazgo: bool | None = None,
    con_principal: bool | None = None,
    vehiculo: Annotated[str | None, Query(max_length=60, description="Marca o modelo del vehículo principal")] = None,
    clase: Annotated[list[str] | None, Query(description="A, B, C o SIN_VENTA")] = None,
    reserva: Reserva | None = None,
    orden: Orden = Orden.VENTA,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> PaginaArticulos:
    p: dict[str, object] = {"cat": tipo.categoria_id, "linea": tipo.linea.value, "yo": usuario.id}
    filtros = ["a.activo", "a.categoria_id = :cat", "a.linea = cast(:linea as app.linea)"]
    if q and q.strip():
        p["q"] = q.strip()
        p["q_like"] = f"%{q.strip()}%"
        filtros.append("(a.item_code ilike :q_like or a.numero_parte_proveedor ilike :q_like or a.descripcion ilike :q_like"
                       " or upper(:q) = any (a.codigo_anterior) or a.codigo_equivalente ilike :q_like)")
    if estado:
        p["estados"] = [e.value for e in estado]
        filtros.append("a.estado::text = any (:estados)")
    if completitud:
        filtros.append(f"cardinality(app.fn_requisitos_por_validar(a.id)) {'=' if completitud == Completitud.COMPLETA else '>'} 0")
    if con_foto is not None:
        filtros.append(f"{'' if con_foto else 'not '}exists (select 1 from app.articulo_imagen i "
                       "where i.articulo_id = a.id and i.origen = 'PROPIA')")
    if emparejado is not None:
        filtros.append(f"{'' if emparejado else 'not '}exists (select 1 from app.articulo_parte x where x.articulo_id = a.id)")
    if con_hallazgo is not None:
        filtros.append(f"{'' if con_hallazgo else 'not '}exists (select 1 from app.hallazgo_calidad_sap h "
                       "where h.articulo_id = a.id and h.corregido_en is null)")
    if con_principal is not None:
        filtros.append(f"vp.texto is {'not ' if con_principal else ''}null")
    if vehiculo and vehiculo.strip():
        p["veh"] = f"%{vehiculo.strip()}%"
        filtros.append("vp.texto ilike :veh")
    if clase:
        p["clases"] = [x for x in clase if x in {"A", "B", "C"}]
        sin_venta = "SIN_VENTA" in clase
        filtros.append(f"(v.clase = any (:clases){' or v.clase is null' if sin_venta else ''})")
    if reserva == Reserva.MIA:
        filtros.append("a.asignado_a = :yo and a.asignado_hasta > now()")
    elif reserva == Reserva.LIBRE:
        filtros.append("(a.asignado_hasta is null or a.asignado_hasta <= now())")
    elif reserva == Reserva.OTROS:
        filtros.append("a.asignado_a <> :yo and a.asignado_hasta > now()")

    donde = " where " + " and ".join(filtros)
    total = c.execute(text(f"select count(*) {_DESDE} {donde}"), p).scalar_one()
    offset = _offset(cursor)
    p |= {"limit": limit, "offset": offset}
    filas = c.execute(text(f"select {_COLUMNAS} {_DESDE} {donde} order by {_ORDEN[orden]} limit :limit offset :offset"), p).all()
    siguiente = _cursor(offset + limit) if offset + limit < total else None
    return PaginaArticulos(items=[ArticuloFila(**f._mapping) for f in filas], total=total, next_cursor=siguiente)


# ---------------------------------------------------------------------------------------------------------------------
# Detalle
# ---------------------------------------------------------------------------------------------------------------------

class Requisito(BaseModel):
    codigo: str
    etiqueta: str
    pestana: str           # dónde se resuelve en el espacio de trabajo


class AccionEstado(BaseModel):
    destino: Estado
    etiqueta: str
    requiere_motivo: bool
    habilitada: bool
    razon: str | None = None


class ReservaInfo(BaseModel):
    usuario_id: int
    nombre: str
    hasta: datetime
    mia: bool


class HallazgoArticulo(BaseModel):
    tipo: str
    campo_sap: str
    valor: str | None


class ArticuloDetalle(BaseModel):
    id: int
    item_code: str
    descripcion: str | None
    estado: Estado
    version: int
    activo: bool
    linea: str
    categoria_codigo: str | None
    numero_parte_proveedor: str | None
    codigo_anterior: list[str] | None
    codigo_equivalente: str | None
    datos_sap: dict[str, object]           # datos normalizados de SAP (solo lectura) con etiqueta del negocio
    requisitos: list[Requisito]
    acciones: list[AccionEstado]
    reserva: ReservaInfo | None
    ultimo_motivo: str | None              # motivo del último rechazo o reapertura
    hallazgos: list[HallazgoArticulo]
    fotos: int
    clase: str | None
    participacion: Decimal | None
    tendencia: Decimal | None


# Campos de SAP que se muestran en el espacio de trabajo (orden y etiqueta del negocio)
CAMPOS_SAP = [
    ("marca_vehiculo", "Marca"), ("modelo_vehiculo", "Línea (modelo)"), ("anio_desde", "Año desde"), ("anio_hasta", "Año hasta"),
    ("motor", "Motor"), ("cilindrada", "Cilindrada"), ("transmision", "Transmisión"),
    ("panal_alto_mm", "Alto (mm)"), ("panal_largo_mm", "Largo (mm)"), ("panal_ancho_mm", "Ancho (mm)"),
    ("tamano_panal", "Tamaño"), ("filas_panal", "Filas"), ("tipo_panal", "Tipo de panal"), ("material_panal", "Material panal"),
    ("material_tanque", "Material tanque"), ("dimension_tanque", "Dimensión tanques"), ("tipo_flujo", "Tipo flujo"),
    ("entrada_diametro", "Diámetro entrada"), ("entrada_ubicacion", "Ubicación entrada"), ("salida_diametro", "Diámetro salida"),
    ("salida_ubicacion", "Ubicación salida"), ("incluye_tapon", "Incluye tapón"), ("material_descripcion", "Material (SAP)"),
]

_ETIQUETA_DESTINO = {
    Estado.POR_VALIDAR: "Enviar a revisión", Estado.VALIDADO: "Validar", Estado.RECHAZADO: "Rechazar",
    Estado.PENDIENTE: "Reabrir", Estado.SINCRONIZADO: "Marcar sincronizado",
}


def _requisitos(c: Connection, articulo_id: int, part_terminology_id: int | None) -> list[Requisito]:
    codigos = c.execute(text("select app.fn_requisitos_por_validar(:id)"), {"id": articulo_id}).scalar_one() or []
    etiquetas = dict(c.execute(text("""select nombre, coalesce(etiqueta, nombre) from meta.atributo_config
                                       where part_terminology_id = :pt"""), {"pt": part_terminology_id}).tuples().all())
    salida = []
    for cod in codigos:
        if cod.startswith("ATRIBUTO:"):
            nombre = cod.split(":", 1)[1]
            salida.append(Requisito(codigo=cod, etiqueta=etiquetas.get(nombre, nombre), pestana="ficha"))
        elif cod == "VEHICULO_PRINCIPAL":
            salida.append(Requisito(codigo=cod, etiqueta="Vehículo principal (confirmado)", pestana="aplicaciones"))
        elif cod == "TIPO_DE_PARTE":
            salida.append(Requisito(codigo=cod, etiqueta="Tipo de parte", pestana="ficha"))
        else:
            salida.append(Requisito(codigo=cod, etiqueta=cod, pestana="ficha"))
    return salida


def _acciones(c: Connection, articulo_id: int, estado: str, activo: bool, usuario: Usuario, requisitos: list[Requisito],
              reserva_ajena: bool) -> list[AccionEstado]:
    """Cambios de estado posibles para este usuario, con la razón si no se pueden hacer ahora (la base vuelve a validar)."""
    reglas = c.execute(text("""select destino::text, roles::text[] as roles, requiere_motivo, prohibe_mismo_usuario
                               from app.transicion_permitida where origen = cast(:e as app.estado_articulo) and actor_tipo = 'USUARIO'"""),
                       {"e": estado}).all()
    enviado_por = c.execute(text("select app.fn_enviado_por(:id)"), {"id": articulo_id}).scalar_one()
    acciones = []
    for r in reglas:
        if not usuario.roles & {Rol(x) for x in r.roles}:
            continue
        destino = Estado(r.destino)
        razon = None
        if not activo:
            razon = "El artículo está inactivo."
        elif reserva_ajena:
            razon = "Está reservado por otro usuario."
        elif r.prohibe_mismo_usuario and enviado_por == str(usuario.id):
            razon = "Tú lo enviaste a revisión: debe validarlo otro supervisor."
        elif destino == Estado.POR_VALIDAR and requisitos:
            razon = f"Faltan {len(requisitos)} requisito(s)."
        acciones.append(AccionEstado(destino=destino, etiqueta=_ETIQUETA_DESTINO[destino], requiere_motivo=r.requiere_motivo,
                                     habilitada=razon is None, razon=razon))
    return acciones


def cargar_detalle(c: Connection, item_code: str, usuario: Usuario) -> ArticuloDetalle:
    a = c.execute(text("""
        select a.*, a.estado::text as estado_txt, a.linea::text as linea_txt, u.nombre as reservado_por,
               v.clase, v.participacion, v.tendencia
        from app.articulo a
        left join app.usuario u on u.id = a.asignado_a
        left join app.v_indicador_venta v on v.articulo_id = a.id and v.categoria_id = a.categoria_id and v.linea = a.linea
        where a.item_code = upper(:ic)
    """), {"ic": item_code}).one_or_none()
    if a is None:
        raise Problema(404, "El artículo no existe", f"No hay un artículo «{item_code}» en Nexo.")
    a = a._mapping
    vigente = a["asignado_hasta"] is not None and a["asignado_hasta"] > datetime.now(a["asignado_hasta"].tzinfo)
    reserva = ReservaInfo(usuario_id=a["asignado_a"], nombre=a["reservado_por"], hasta=a["asignado_hasta"],
                          mia=a["asignado_a"] == usuario.id) if vigente else None
    requisitos = _requisitos(c, a["id"], a["part_terminology_id"])
    acciones = _acciones(c, a["id"], a["estado_txt"], a["activo"], usuario, requisitos, reserva is not None and not reserva.mia)
    ultimo_motivo = c.execute(text("""
        select motivo from audit.bitacora_articulo
        where articulo_id = :id and tipo = 'TRANSICION' and estado_destino in ('RECHAZADO', 'PENDIENTE') and motivo is not null
          and estado_origen is not null
        order by id desc limit 1
    """), {"id": a["id"]}).scalar_one_or_none() if a["estado_txt"] in ("RECHAZADO", "PENDIENTE") else None
    hallazgos = c.execute(text("""select tipo::text as tipo, campo_sap, valor from app.hallazgo_calidad_sap
                                  where articulo_id = :id and corregido_en is null order by tipo"""), {"id": a["id"]}).all()
    fotos = c.execute(text("select count(*) from app.articulo_imagen where articulo_id = :id and origen = 'PROPIA'"),
                      {"id": a["id"]}).scalar_one()
    return ArticuloDetalle(
        id=a["id"], item_code=a["item_code"], descripcion=a["descripcion"], estado=Estado(a["estado_txt"]), version=a["version"],
        activo=a["activo"], linea=a["linea_txt"], categoria_codigo=a["categoria_codigo"],
        numero_parte_proveedor=a["numero_parte_proveedor"], codigo_anterior=a["codigo_anterior"],
        codigo_equivalente=a["codigo_equivalente"],
        datos_sap={etiqueta: a[col] for col, etiqueta in CAMPOS_SAP if a[col] is not None},
        requisitos=requisitos, acciones=acciones, reserva=reserva, ultimo_motivo=ultimo_motivo,
        hallazgos=[HallazgoArticulo(**h._mapping) for h in hallazgos], fotos=fotos,
        clase=a["clase"], participacion=a["participacion"], tendencia=a["tendencia"],
    )


@router.get("/{item_code}", response_model=ArticuloDetalle, summary="Detalle del artículo: datos SAP, requisitos y acciones posibles",
            responses={404: {"description": "No existe"}})
def obtener_articulo(item_code: str, usuario: UsuarioActual, c: Conexion) -> ArticuloDetalle:
    return cargar_detalle(c, item_code, usuario)


class EventoHistorial(BaseModel):
    id: int
    tipo: str
    estado_origen: Estado | None
    estado_destino: Estado | None
    actor: str               # nombre del usuario o el proceso (ETL, salida…)
    motivo: str | None
    detalle: dict | None
    creado_en: datetime


@router.get("/{item_code}/historial", response_model=list[EventoHistorial], summary="Bitácora del artículo (más reciente primero)")
def historial_articulo(item_code: str, _: UsuarioActual, c: Conexion) -> list[EventoHistorial]:
    filas = c.execute(text("""
        select b.id, b.tipo::text as tipo, b.estado_origen::text as estado_origen, b.estado_destino::text as estado_destino,
               coalesce(u.nombre, b.actor) as actor, b.motivo, b.detalle, b.creado_en
        from audit.bitacora_articulo b join app.articulo a on a.id = b.articulo_id
        left join app.usuario u on b.actor_tipo = 'USUARIO' and u.id::text = b.actor
        where a.item_code = upper(:ic) order by b.id desc limit 200
    """), {"ic": item_code}).all()
    return [EventoHistorial(**f._mapping) for f in filas]
