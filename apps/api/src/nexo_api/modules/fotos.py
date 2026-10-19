"""Fotos del artículo (propuesta UX §6.4 "Pestaña Fotos" y §6.9, ADR 0013): propias en MinIO y de proveedor por URL.

El encargado de fotos (rol FOTOS) o un administrador las sube desde la APP: se convierten a WebP y se guardan con la convención
`imagenes_inventario/{cat}_{NOMBRE}/{ItemCode}/{ItemCode}_{n}.webp`. Si el artículo ya está validado, la base crea la tarea de
verificación NUEVA_FOTO (trigger `tarea_por_foto`). No requiere reservar el artículo: subir fotos no edita la ficha.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import Connection, text

from ..adapters.minio import PREFIJO
from ..auth.dependencias import Rol, Usuario, UsuarioActual, requiere_rol
from ..auth.registro import fijar_actor
from ..core.bd import Conexion
from ..core.errores import Problema
from .emparejamiento import Maestro
from .imagenes import AlmacenOpcional, FirmadorOpcional, a_webp
from .tipo import TipoArticulo

router = APIRouter(tags=["fotos"])

ROLES_FOTOS = {Rol.FOTOS, Rol.ADMINISTRADOR}
SubeFotos = Annotated[Usuario, Depends(requiere_rol(*ROLES_FOTOS))]
MAX_ARCHIVOS = 10
MAX_BYTES = 20 * 1024 * 1024


class FotoPropia(BaseModel):
    id: int
    url: str | None                         # None si la API no tiene MINIO_* para firmar
    orden: int
    subida_por: str | None
    subida_en: str
    validada: bool
    validada_por: str | None


class FotoProveedor(BaseModel):
    parte_id: int
    tipo: str
    url: str


class FotosArticulo(BaseModel):
    item_code: str
    puede_subir: bool                       # rol FOTOS o ADMINISTRADOR y artículo activo
    subida_disponible: bool                 # la API tiene la llave de escritura de MinIO
    propias: list[FotoPropia]
    proveedor: list[FotoProveedor]
    subidas: int = 0


class OrdenFotos(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)


class SinFoto(BaseModel):
    item_code: str
    descripcion: str | None
    estado: str
    clase: str | None


def carpeta(codigo_categoria: str, nombre_categoria: str, item_code: str) -> str:
    """'25', 'RADIADORES', 'RAD00188' → imagenes_inventario/25_RADIADORES/RAD00188/ (la convención de las carpetas existentes)."""
    return f"{PREFIJO}{codigo_categoria}_{nombre_categoria.strip().upper().replace(' ', '_')}/{item_code}/"


def _articulo(c: Connection, item_code: str, bloquear: bool = False):
    a = c.execute(text(f"""
        select a.id, a.item_code, a.activo, cat.codigo_sap, cat.nombre as categoria
        from app.articulo a join app.categoria cat on cat.id = a.categoria_id
        where a.item_code = upper(:ic) {'for update of a' if bloquear else ''}
    """), {"ic": item_code}).one_or_none()
    if a is None:
        raise Problema(404, "El artículo no existe")
    return a


def cargar_fotos(c: Connection, item_code: str, usuario: Usuario, firmador, almacen, m, subidas: int = 0) -> FotosArticulo:
    a = _articulo(c, item_code)
    filas = c.execute(text("""
        select i.id, i.minio_bucket, i.minio_objeto, i.orden, s.nombre as subida_por, i.subida_en, i.validada, v.nombre as validada_por
        from app.articulo_imagen i left join app.usuario s on s.id = i.subida_por left join app.usuario v on v.id = i.validada_por
        where i.articulo_id = :a and i.origen = 'PROPIA' order by i.orden, i.id
    """), {"a": a.id}).all()
    partes = c.execute(text("select parte_id from app.articulo_parte where articulo_id = :a order by es_principal desc, confirmado_en"),
                       {"a": a.id}).scalars().all()
    c.rollback()

    proveedor = []
    if m is not None:
        for parte_id in partes:
            try:
                d = m.detalle(parte_id)
            except Problema:
                break
            for i in d.imagenes if d else []:
                url = i.url or (firmador.firmar(i.minio_objeto, i.minio_bucket) if firmador and i.minio_objeto else None)
                if url:
                    proveedor.append(FotoProveedor(parte_id=parte_id, tipo=i.tipo, url=url))
    return FotosArticulo(
        item_code=a.item_code, puede_subir=bool(usuario.roles & ROLES_FOTOS) and a.activo, subida_disponible=almacen is not None,
        propias=[FotoPropia(id=f.id, url=firmador.firmar(f.minio_objeto, f.minio_bucket) if firmador else None, orden=f.orden,
                            subida_por=f.subida_por, subida_en=f.subida_en.isoformat(), validada=f.validada,
                            validada_por=f.validada_por) for f in filas],
        proveedor=proveedor, subidas=subidas)


@router.get("/articulos/{item_code}/fotos", response_model=FotosArticulo, summary="Fotos propias (MinIO) y del catálogo (URL)")
def listar_fotos(item_code: str, usuario: UsuarioActual, c: Conexion, firmador: FirmadorOpcional, almacen: AlmacenOpcional,
                 m: Maestro) -> FotosArticulo:
    return cargar_fotos(c, item_code, usuario, firmador, almacen, m)


@router.post("/articulos/{item_code}/fotos", response_model=FotosArticulo, status_code=201,
             summary="Subir fotos propias (se convierten a WebP con la convención de MinIO)",
             responses={403: {"description": "Rol FOTOS o ADMINISTRADOR"}, 409: {"description": "Artículo inactivo"},
                        422: {"description": "No es una imagen"}, 503: {"description": "Sin llave de escritura de MinIO"}})
def subir_fotos(item_code: str, usuario: SubeFotos, c: Conexion, firmador: FirmadorOpcional, almacen: AlmacenOpcional, m: Maestro,
                archivos: Annotated[list[UploadFile], File(description="JPG, PNG o WebP")]) -> FotosArticulo:
    if almacen is None:
        raise Problema(503, "Subida de fotos no configurada", "Falta la llave de escritura de MinIO (MINIO_FOTOS_*) en la API.")
    if not archivos or len(archivos) > MAX_ARCHIVOS:
        raise Problema(422, "Elige entre 1 y 10 fotos")
    # Todo se convierte antes de subir nada: si un archivo no sirve, no queda una subida a medias
    convertidas = []
    for f in archivos:
        datos = f.file.read(MAX_BYTES + 1)
        if len(datos) > MAX_BYTES:
            raise Problema(422, "Foto demasiado grande", f"{f.filename} pesa más de 20 MB.")
        convertidas.append(a_webp(datos, f.filename or ""))
    for webp in convertidas:
        with c.begin():
            fijar_actor(c, usuario.id)
            a = _articulo(c, item_code, bloquear=True)          # serializa las subidas del mismo artículo
            if not a.activo:
                raise Problema(409, "El artículo está inactivo", "No se suben fotos de artículos inactivos.")
            n, orden = c.execute(text(r"""
                select coalesce(max((regexp_match(minio_objeto, '_(\d+)\.[A-Za-z]+$'))[1]::int), 0) + 1, coalesce(max(orden), 0) + 1
                from app.articulo_imagen where articulo_id = :a and origen = 'PROPIA'
            """), {"a": a.id}).one()
            objeto = f"{carpeta(a.codigo_sap, a.categoria, a.item_code)}{a.item_code}_{n}.webp"
            almacen.subir(objeto, webp)
            c.execute(text("""insert into app.articulo_imagen (articulo_id, origen, minio_bucket, minio_objeto, orden, subida_por)
                              values (:a, 'PROPIA', :b, :o, :n, :u)"""),
                      {"a": a.id, "b": almacen.bucket, "o": objeto, "n": orden, "u": usuario.id})
    return cargar_fotos(c, item_code, usuario, firmador, almacen, m, subidas=len(convertidas))


@router.put("/articulos/{item_code}/fotos/orden", response_model=FotosArticulo, summary="Ordenar las fotos propias")
def ordenar_fotos(item_code: str, datos: OrdenFotos, usuario: SubeFotos, c: Conexion, firmador: FirmadorOpcional, almacen: AlmacenOpcional,
                  m: Maestro) -> FotosArticulo:
    with c.begin():
        fijar_actor(c, usuario.id)
        a = _articulo(c, item_code, bloquear=True)
        actuales = set(c.execute(text("select id from app.articulo_imagen where articulo_id = :a and origen = 'PROPIA'"),
                                 {"a": a.id}).scalars())
        if set(datos.ids) != actuales or len(datos.ids) != len(actuales):
            raise Problema(422, "La lista de fotos no coincide", "Recarga: alguien subió o cambió fotos.")
        for i, foto_id in enumerate(datos.ids, start=1):
            c.execute(text("update app.articulo_imagen set orden = :o where id = :i and orden <> :o"), {"o": i, "i": foto_id})
    return cargar_fotos(c, item_code, usuario, firmador, almacen, m)


@router.get("/fotos/pendientes", response_model=list[SinFoto], summary="Artículos activos sin foto propia, primero los que más venden")
def listar_sin_foto(_: SubeFotos, tipo: TipoArticulo, c: Conexion, limite: Annotated[int, Query(ge=1, le=200)] = 50) -> list[SinFoto]:
    filas = c.execute(text("""
        select a.item_code, a.descripcion, a.estado::text as estado, v.clase
        from app.articulo a
        left join app.v_indicador_venta v on v.articulo_id = a.id and v.categoria_id = a.categoria_id and v.linea = a.linea
        where a.activo and a.categoria_id = :cat and a.linea = cast(:linea as app.linea)
          and not exists (select 1 from app.articulo_imagen i where i.articulo_id = a.id and i.origen = 'PROPIA')
        order by coalesce(v.clase, 'Z'), v.participacion desc nulls last, a.item_code
        limit :lim
    """), {"cat": tipo.categoria_id, "linea": tipo.linea.value, "lim": limite}).all()
    return [SinFoto(item_code=f.item_code, descripcion=f.descripcion, estado=f.estado, clase=f.clase) for f in filas]
