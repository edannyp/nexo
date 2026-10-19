"""Administración de usuarios (solo ADMINISTRADOR): alta con contraseña temporal, roles, permisos, bloqueo y sesiones."""

from datetime import datetime

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy import Connection, text
from sqlalchemy.exc import IntegrityError

from ..core.bd import Conexion
from ..core.errores import Problema
from . import contrasenas
from .dependencias import Administrador, Permiso, Rol, Sesiones
from .registro import evento, fijar_actor

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class UsuarioAdmin(BaseModel):
    id: int
    usuario: str
    nombre: str
    correo: str | None
    roles: list[Rol]
    permisos: list[Permiso]
    activo: bool
    debe_cambiar_password: bool
    bloqueado_hasta: datetime | None
    ultimo_acceso_en: datetime | None


class NuevoUsuario(BaseModel):
    usuario: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
    nombre: str = Field(min_length=1, max_length=120)
    correo: str | None = Field(None, max_length=200)
    roles: list[Rol] = Field(min_length=1)
    permisos: list[Permiso] = []


class CambiosUsuario(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=120)
    correo: str | None = Field(None, max_length=200)
    roles: list[Rol] | None = Field(None, min_length=1)
    permisos: list[Permiso] | None = None
    activo: bool | None = None


class UsuarioCreado(BaseModel):
    usuario: UsuarioAdmin
    password_temporal: str = Field(description="Se muestra una sola vez; el usuario debe cambiarla al entrar")


class PasswordTemporal(BaseModel):
    password_temporal: str


_CONSULTA = """
    select u.id, u.usuario::text as usuario, u.nombre, u.correo::text as correo, u.activo, u.debe_cambiar_password,
           u.bloqueado_hasta, u.ultimo_acceso_en,
           coalesce((select array_agg(r.rol::text order by r.rol::text) from app.usuario_rol r where r.usuario_id = u.id), '{}') as roles,
           coalesce((select array_agg(p.permiso::text order by p.permiso::text) from app.usuario_permiso p where p.usuario_id = u.id), '{}')
             as permisos
    from app.usuario u
"""


def _leer(c: Connection, usuario_id: int) -> UsuarioAdmin:
    fila = c.execute(text(_CONSULTA + " where u.id = :id"), {"id": usuario_id}).one_or_none()
    if fila is None:
        raise Problema(404, "Usuario no encontrado")
    return UsuarioAdmin(**fila._mapping)


def _poner_roles_permisos(c: Connection, usuario_id: int, actor_id: int, roles: list[Rol] | None, permisos: list[Permiso] | None) -> None:
    if roles is not None:
        c.execute(text("delete from app.usuario_rol where usuario_id = :id and not (rol::text = any(:roles))"),
                  {"id": usuario_id, "roles": [r.value for r in roles]})
        for r in set(roles):
            c.execute(text("insert into app.usuario_rol values (:id, cast(:r as app.rol)) on conflict do nothing"),
                      {"id": usuario_id, "r": r.value})
    if permisos is not None:
        c.execute(text("delete from app.usuario_permiso where usuario_id = :id and not (permiso::text = any(:p))"),
                  {"id": usuario_id, "p": [p.value for p in permisos]})
        for p in set(permisos):
            c.execute(text("""insert into app.usuario_permiso (usuario_id, permiso, otorgado_por)
                              values (:id, cast(:p as app.permiso), :actor) on conflict do nothing"""),
                      {"id": usuario_id, "p": p.value, "actor": actor_id})


@router.get("", response_model=list[UsuarioAdmin], summary="Listar usuarios")
def listar_usuarios(_: Administrador, c: Conexion) -> list[UsuarioAdmin]:
    return [UsuarioAdmin(**f._mapping) for f in c.execute(text(_CONSULTA + " order by u.activo desc, u.nombre"))]


@router.post("", response_model=UsuarioCreado, status_code=201, summary="Dar de alta un usuario con contraseña temporal",
             responses={409: {"description": "El usuario ya existe"}})
def crear_usuario(datos: NuevoUsuario, admin: Administrador, request: Request, c: Conexion) -> UsuarioCreado:
    temporal = contrasenas.temporal()
    try:
        with c.begin():
            fijar_actor(c, admin.id)
            nuevo_id = c.execute(text("""
                insert into app.usuario (usuario, nombre, correo, password_hash, debe_cambiar_password)
                values (:usuario, :nombre, :correo, :h, true) returning id
            """), {"usuario": datos.usuario, "nombre": datos.nombre.strip(), "correo": datos.correo,
                   "h": contrasenas.hashear(temporal)}).scalar_one()
            _poner_roles_permisos(c, nuevo_id, admin.id, datos.roles, datos.permisos)
            evento(c, request, "ALTA", datos.usuario, nuevo_id, actor_id=admin.id)
    except IntegrityError as e:
        raise Problema(409, "El usuario ya existe", f"Ya hay un usuario llamado «{datos.usuario}».") from e
    return UsuarioCreado(usuario=_leer(c, nuevo_id), password_temporal=temporal)


@router.patch("/{usuario_id}", response_model=UsuarioAdmin, summary="Cambiar datos, roles, permisos o estado",
              responses={404: {"description": "No existe"}, 409: {"description": "Dejaría la APP sin administrador propio"}})
def modificar_usuario(usuario_id: int, datos: CambiosUsuario, admin: Administrador, sesiones: Sesiones, c: Conexion) -> UsuarioAdmin:
    if usuario_id == admin.id and (datos.activo is False or (datos.roles is not None and Rol.ADMINISTRADOR not in datos.roles)):
        raise Problema(409, "No puedes quitarte tu propio acceso", "Pide a otro administrador que lo haga.")
    with c.begin():
        fijar_actor(c, admin.id)
        _leer(c, usuario_id)
        campos = datos.model_dump(include={"nombre", "correo", "activo"}, exclude_unset=True)
        if campos:
            asignaciones = ", ".join(f"{k} = :{k}" for k in campos)
            c.execute(text(f"update app.usuario set {asignaciones} where id = :id"), campos | {"id": usuario_id})
        _poner_roles_permisos(c, usuario_id, admin.id, datos.roles, datos.permisos)
    if datos.activo is False:
        sesiones.eliminar_de_usuario(usuario_id)
    return _leer(c, usuario_id)


@router.post("/{usuario_id}/restablecer", response_model=PasswordTemporal, summary="Nueva contraseña temporal (cierra sus sesiones)")
def restablecer_password(usuario_id: int, admin: Administrador, request: Request, sesiones: Sesiones, c: Conexion) -> PasswordTemporal:
    temporal = contrasenas.temporal()
    with c.begin():
        fijar_actor(c, admin.id)
        u = _leer(c, usuario_id)
        c.execute(text("""update app.usuario set password_hash = :h, debe_cambiar_password = true, intentos_fallidos = 0,
                          bloqueado_hasta = null where id = :id"""), {"h": contrasenas.hashear(temporal), "id": usuario_id})
        evento(c, request, "RESTABLECER_PASSWORD", u.usuario, usuario_id, actor_id=admin.id)
    sesiones.eliminar_de_usuario(usuario_id)
    return PasswordTemporal(password_temporal=temporal)


@router.post("/{usuario_id}/desbloquear", status_code=204, summary="Quitar el bloqueo por intentos fallidos")
def desbloquear_usuario(usuario_id: int, admin: Administrador, request: Request, c: Conexion) -> None:
    with c.begin():
        fijar_actor(c, admin.id)
        u = _leer(c, usuario_id)
        c.execute(text("update app.usuario set intentos_fallidos = 0, bloqueado_hasta = null where id = :id"), {"id": usuario_id})
        evento(c, request, "DESBLOQUEO", u.usuario, usuario_id, actor_id=admin.id)


@router.delete("/{usuario_id}/sesiones", status_code=204, summary="Cerrar todas las sesiones del usuario")
def cerrar_sesiones_usuario(usuario_id: int, admin: Administrador, request: Request, sesiones: Sesiones, c: Conexion) -> None:
    with c.begin():
        u = _leer(c, usuario_id)
        evento(c, request, "SESIONES_CERRADAS", u.usuario, usuario_id, actor_id=admin.id)
    sesiones.eliminar_de_usuario(usuario_id)
