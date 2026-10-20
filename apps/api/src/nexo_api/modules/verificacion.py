"""Cola de verificación (propuesta UX §6.6, ADR 0012): tareas abiertas por foto nueva, muestreo, cambio en el catálogo maestro o
creadas a mano. Conforme cierra la tarea (y valida la foto); con hallazgo regresa el artículo a Pendiente con la nota
(`app.fn_resolver_verificacion`). La resuelve un supervisor o administrador.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text

from ..auth.dependencias import Administrador, Rol, Usuario, requiere_rol
from ..auth.registro import fijar_actor
from ..core.bd import Conexion
from ..core.errores import Problema
from ..core.negocio import reglas_de_negocio
from .emparejamiento import MedidasPanal, medidas_articulo
from .imagenes import FirmadorOpcional
from .tipo import TipoArticulo

router = APIRouter(prefix="/verificaciones", tags=["verificacion"])

Supervisa = Annotated[Usuario, Depends(requiere_rol(Rol.SUPERVISOR, Rol.ADMINISTRADOR))]


class OrigenTarea(StrEnum):
    NUEVA_FOTO = "NUEVA_FOTO"
    MUESTREO = "MUESTREO"
    CAMBIO_CATALOGO = "CAMBIO_CATALOGO"
    MANUAL = "MANUAL"


class ResultadoVerificacion(StrEnum):
    CONFORME = "CONFORME"
    CON_HALLAZGO = "CON_HALLAZGO"


class TareaVerificacion(BaseModel):
    id: int
    origen: OrigenTarea
    creada_en: datetime
    detalle: dict[str, Any]
    item_code: str
    descripcion: str | None
    estado_articulo: str
    medidas: MedidasPanal
    foto_url: str | None                    # NUEVA_FOTO: la foto a revisar
    fotos_validadas: int                    # para comparar con las que ya estaban


class ColaVerificacion(BaseModel):
    tareas: list[TareaVerificacion]
    por_origen: dict[str, int]


class Resolucion(BaseModel):
    resultado: ResultadoVerificacion
    nota: str | None = Field(None, max_length=1000)

    @model_validator(mode="after")
    def nota_si_hay_hallazgo(self) -> "Resolucion":
        if self.resultado == ResultadoVerificacion.CON_HALLAZGO and not (self.nota or "").strip():
            raise ValueError("Escribe qué encontraste.")
        return self


class Muestreo(BaseModel):
    cantidad: int = Field(10, ge=1, le=50)


class Creadas(BaseModel):
    creadas: int


class NuevaVerificacion(BaseModel):
    item_code: str = Field(min_length=3, max_length=30)
    nota: str = Field(min_length=3, max_length=1000, description="Qué hay que revisar")


@router.get("", response_model=ColaVerificacion, summary="Tareas de verificación abiertas del tipo de artículo elegido")
def listar_verificaciones(_: Supervisa, tipo: TipoArticulo, c: Conexion, firmador: FirmadorOpcional,
                          origen: OrigenTarea | None = None) -> ColaVerificacion:
    filas = c.execute(text("""
        select t.id as tarea_id, t.origen::text as origen, t.creada_en, t.detalle, a.*, a.estado::text as estado_txt,
               i.minio_bucket, i.minio_objeto,
               (select count(*) from app.articulo_imagen x where x.articulo_id = a.id and x.validada) as fotos_validadas
        from app.tarea_verificacion t join app.articulo a on a.id = t.articulo_id
        left join app.articulo_imagen i on i.id = (t.detalle ->> 'imagen_id')::bigint
        where t.estado = 'ABIERTA' and a.activo and a.categoria_id = :cat and a.linea = cast(:linea as app.linea)
        order by t.creada_en, t.id
        limit 200
    """), {"cat": tipo.categoria_id, "linea": tipo.linea.value}).all()
    tareas = []
    for f in filas:
        m = medidas_articulo(c, f)
        tareas.append(TareaVerificacion(
            id=f.tarea_id, origen=f.origen, creada_en=f.creada_en, detalle=f.detalle, item_code=f.item_code, descripcion=f.descripcion,
            estado_articulo=f.estado_txt, medidas=MedidasPanal(alto=m.alto, largo=m.largo, ancho=m.ancho),
            foto_url=firmador.firmar(f.minio_objeto, f.minio_bucket) if firmador and f.minio_objeto else None,
            fotos_validadas=f.fotos_validadas))
    c.rollback()
    por_origen = {o.value: 0 for o in OrigenTarea}
    for t in tareas:
        por_origen[t.origen] += 1
    return ColaVerificacion(tareas=[t for t in tareas if origen is None or t.origen == origen], por_origen=por_origen)


@router.post("/{tarea_id}/resolucion", status_code=204, summary="Resolver: conforme o con hallazgo (regresa a Pendiente)",
             responses={409: {"description": "Ya resuelta o reservado por otro"}, 422: {"description": "Falta la nota"}})
def resolver_verificacion(tarea_id: int, datos: Resolucion, usuario: Supervisa, c: Conexion) -> None:
    with c.begin():
        fijar_actor(c, usuario.id)
        reservada = c.execute(text("""
            select u.nombre from app.tarea_verificacion t join app.articulo a on a.id = t.articulo_id
            join app.usuario u on u.id = a.asignado_a
            where t.id = :t and a.asignado_hasta > now() and a.asignado_a <> :u
        """), {"t": tarea_id, "u": usuario.id}).scalar_one_or_none()
        if reservada and datos.resultado == ResultadoVerificacion.CON_HALLAZGO:
            raise Problema(409, "Está reservado por otro usuario", f"{reservada} lo está trabajando.")
        if not c.execute(text("select 1 from app.tarea_verificacion where id = :t"), {"t": tarea_id}).first():
            raise Problema(404, "La verificación no existe")
        with reglas_de_negocio():
            c.execute(text("select app.fn_resolver_verificacion(:t, :u, cast(:r as app.estado_tarea), :n)"),
                      {"t": tarea_id, "u": usuario.id, "r": datos.resultado.value, "n": datos.nota})


@router.post("/muestreo", response_model=Creadas, summary="Generar un muestreo de artículos validados al azar (administrador)")
def generar_muestreo(datos: Muestreo, usuario: Administrador, tipo: TipoArticulo, c: Conexion) -> Creadas:
    with c.begin():
        fijar_actor(c, usuario.id)
        n = c.execute(text("select app.fn_generar_muestreo(:n, cast(:cat as smallint))"),
                      {"n": datos.cantidad, "cat": tipo.categoria_id}).scalar_one()
    return Creadas(creadas=n)


@router.post("", response_model=Creadas, status_code=201, summary="Crear una verificación manual de un artículo",
             responses={409: {"description": "Ya tiene una verificación manual abierta o no está validado"}})
def crear_verificacion(datos: NuevaVerificacion, usuario: Supervisa, c: Conexion) -> Creadas:
    with c.begin():
        fijar_actor(c, usuario.id)
        a = c.execute(text("select id, activo, estado::text as estado from app.articulo where item_code = upper(:ic)"),
                      {"ic": datos.item_code.strip()}).one_or_none()
        if a is None:
            raise Problema(404, "El artículo no existe")
        if not a.activo:
            raise Problema(409, "El artículo está inactivo")
        if a.estado not in ("VALIDADO", "SINCRONIZADO"):
            raise Problema(409, "Solo se verifican artículos validados",
                           "Si está en proceso, el supervisor lo revisa al validarlo; si hace falta corregirlo, recházalo.")
        nueva = c.execute(text("""
            insert into app.tarea_verificacion (articulo_id, origen, detalle)
            values (:a, 'MANUAL', jsonb_build_object('nota', cast(:n as text), 'creada_por', cast(:quien as text)))
            on conflict do nothing returning id
        """), {"a": a.id, "n": datos.nota.strip(), "quien": usuario.nombre}).first()
        if nueva is None:
            raise Problema(409, "Ya tiene una verificación manual abierta")
    return Creadas(creadas=1)
