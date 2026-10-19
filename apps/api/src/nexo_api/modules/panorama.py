"""Panorama del tipo de artículo elegido (architecture/ux/propuesta.md §6.1). Una sola consulta por bloque, todo filtrado por tipo."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from ..auth.dependencias import UsuarioActual
from ..core.bd import Conexion
from .tipo import TipoArticulo

router = APIRouter(prefix="/panorama", tags=["panorama"])


class Estado(StrEnum):
    PENDIENTE = "PENDIENTE"
    POR_VALIDAR = "POR_VALIDAR"
    RECHAZADO = "RECHAZADO"
    VALIDADO = "VALIDADO"
    SINCRONIZADO = "SINCRONIZADO"


class AtributoFicha(BaseModel):
    paid: int
    etiqueta: str
    confirmados: int
    sugeridos: int   # precargados desde SAP u otra fuente, aún sin confirmar
    faltan: int


class Ficha(BaseModel):
    completos: int   # artículos con todos los atributos obligatorios confirmados
    atributos: list[AtributoFicha]


class Cobertura(BaseModel):
    con_foto: int
    fotos: int
    emparejados: int
    con_aplicacion: int


class Atencion(BaseModel):
    rechazados: int
    verificaciones_abiertas: int
    hallazgos_sap: int
    reservados: int
    reservas_por_vencer: int   # vencen en los próximos 5 minutos


class Productividad(BaseModel):
    usuario_id: int
    nombre: str
    enviados: int
    validados: int
    rechazados: int


class ClaseVenta(BaseModel):
    clase: str
    articulos: int
    participacion: Decimal


class Prioridad(BaseModel):
    articulo_id: int
    item_code: str
    descripcion: str | None
    estado: Estado
    clase: str
    participacion: Decimal
    top_pct: Decimal
    tendencia: Decimal | None


class VentasResumen(BaseModel):
    disponible: bool
    actualizado_en: datetime | None
    meses: int
    por_clase: list[ClaseVenta]
    sin_venta: int
    prioridad: list[Prioridad]   # los que más venden y aún no están validados


class Panorama(BaseModel):
    activos: int
    por_estado: dict[Estado, int]
    ficha: Ficha
    cobertura: Cobertura
    atencion: Atencion
    productividad: list[Productividad]
    ventas: VentasResumen


@router.get("", response_model=Panorama, summary="Panorama del tipo de artículo (filtro global)")
def obtener_panorama(_: UsuarioActual, tipo: TipoArticulo, c: Conexion) -> Panorama:
    p = {"cat": tipo.categoria_id, "linea": tipo.linea.value}
    del_tipo = "a.activo and a.categoria_id = :cat and a.linea = cast(:linea as app.linea)"

    estados = dict(c.execute(text(f"select a.estado::text, count(*) from app.articulo a where {del_tipo} group by 1"), p).tuples().all())
    por_estado = {e: estados.get(e.value, 0) for e in Estado}

    atributos = c.execute(text(f"""
        select r.paid, coalesce(r.etiqueta, r.nombre) as etiqueta,
               count(t.id) filter (where t.confirmado_por is not null) as confirmados,
               count(t.id) filter (where t.confirmado_por is null) as sugeridos,
               count(*) filter (where t.id is null) as faltan
        from app.articulo a
        join meta.atributo_config r on r.part_terminology_id = a.part_terminology_id and r.habilitado and r.obligatorio
        left join app.articulo_atributo t on t.articulo_id = a.id and t.paid = r.paid
        where {del_tipo}
        group by r.paid, r.etiqueta, r.nombre, r.orden order by r.orden nulls last, r.paid
    """), p).all()
    completos = c.execute(text(f"""
        select count(*) from app.articulo a where {del_tipo} and not exists (
          select 1 from meta.atributo_config r
          where r.part_terminology_id = a.part_terminology_id and r.habilitado and r.obligatorio
            and not exists (select 1 from app.articulo_atributo t
                            where t.articulo_id = a.id and t.paid = r.paid and t.confirmado_por is not null))
    """), p).scalar_one()

    cob = c.execute(text(f"""
        select count(*) filter (where exists (select 1 from app.articulo_imagen i
                                              where i.articulo_id = a.id and i.origen = 'PROPIA')) as con_foto,
               (select count(*) from app.articulo_imagen i join app.articulo a on a.id = i.articulo_id
                where {del_tipo} and i.origen = 'PROPIA') as fotos,
               count(*) filter (where exists (select 1 from app.articulo_parte x where x.articulo_id = a.id)) as emparejados,
               count(*) filter (where exists (select 1 from app.articulo_aplicacion x
                                              where x.articulo_id = a.id and x.confirmado_por is not null)) as con_aplicacion
        from app.articulo a where {del_tipo}
    """), p).one()

    aten = c.execute(text(f"""
        select count(*) filter (where a.estado = 'RECHAZADO') as rechazados,
               (select count(*) from app.tarea_verificacion t join app.articulo a on a.id = t.articulo_id
                where {del_tipo} and t.estado = 'ABIERTA') as verificaciones_abiertas,
               (select count(*) from app.hallazgo_calidad_sap h join app.articulo a on a.id = h.articulo_id
                where a.categoria_id = :cat and a.linea = cast(:linea as app.linea) and h.corregido_en is null) as hallazgos_sap,
               count(*) filter (where a.asignado_hasta > now()) as reservados,
               count(*) filter (where a.asignado_hasta > now() and a.asignado_hasta < now() + interval '5 minutes') as reservas_por_vencer
        from app.articulo a where {del_tipo}
    """), p).one()

    productividad = c.execute(text(f"""
        select u.id as usuario_id, u.nombre,
               count(*) filter (where b.estado_destino = 'POR_VALIDAR') as enviados,
               count(*) filter (where b.estado_destino = 'VALIDADO') as validados,
               count(*) filter (where b.estado_destino = 'RECHAZADO') as rechazados
        from audit.bitacora_articulo b
        join app.articulo a on a.id = b.articulo_id
        join app.usuario u on b.actor_tipo = 'USUARIO' and u.id::text = b.actor
        where {del_tipo} and b.tipo = 'TRANSICION' and b.creado_en > now() - interval '7 days'
        group by u.id, u.nombre order by count(*) desc, u.nombre
    """), p).all()

    carga = c.execute(text("select max(ejecutada_en) from meta.carga_ventas")).scalar_one()
    meses = c.execute(text("select valor::int from meta.parametro where clave = 'ventas.meses_periodo'")).scalar_one()
    # Indicadores del tipo en una sola pasada por la vista (clases, artículos sin venta y prioridad)
    ventas = c.execute(text("""
        with v as (
          select v.*, a.descripcion, a.estado::text as estado
          from app.v_indicador_venta v join app.articulo a on a.id = v.articulo_id
          where v.categoria_id = :cat and v.linea = cast(:linea as app.linea)
        )
        select
          coalesce((select json_agg(json_build_object('clase', clase, 'articulos', n, 'participacion', part) order by clase)
                    from (select clase, count(*) as n, sum(participacion) as part from v where clase is not null group by clase) x), '[]')
            as por_clase,
          (select count(*) from v where clase is null) as sin_venta,
          coalesce((select json_agg(x order by x.participacion desc) from (
             select articulo_id, item_code, descripcion, estado, clase, participacion, top_pct, tendencia from v
             where clase is not null and estado in ('PENDIENTE', 'RECHAZADO', 'POR_VALIDAR')
             order by participacion desc limit 10) x), '[]') as prioridad
    """), p).one()

    return Panorama(
        activos=sum(por_estado.values()),
        por_estado=por_estado,
        ficha=Ficha(completos=completos, atributos=[AtributoFicha(**f._mapping) for f in atributos]),
        cobertura=Cobertura(**cob._mapping),
        atencion=Atencion(**aten._mapping),
        productividad=[Productividad(**f._mapping) for f in productividad],
        ventas=VentasResumen(disponible=carga is not None, actualizado_en=carga, meses=meses,
                             por_clase=[ClaseVenta(**x) for x in ventas.por_clase], sin_venta=ventas.sin_venta,
                             prioridad=[Prioridad(**x) for x in ventas.prioridad]),
    )
