"""Quién hace la petición: sesión (cookie), CSRF, usuario activo, roles y permisos (ADR 0015, 0022)."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from typing import Annotated

import redis
from fastapi import Depends, HTTPException, Request
from sqlalchemy import Connection, text

from ..core.bd import Conexion
from ..core.config import config
from .sesiones import AlmacenSesiones, Sesion, SesionesRedis

COOKIE = "nexo_sesion"
CABECERA_CSRF = "X-CSRF-Token"
METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}


class Rol(StrEnum):
    OPERADOR = "OPERADOR"
    SUPERVISOR = "SUPERVISOR"
    ADMINISTRADOR = "ADMINISTRADOR"
    FOTOS = "FOTOS"


class Permiso(StrEnum):
    VER_ANALISIS_VENTAS = "VER_ANALISIS_VENTAS"


@dataclass(frozen=True)
class Usuario:
    id: int
    usuario: str
    nombre: str
    correo: str | None
    roles: frozenset[Rol]
    permisos: frozenset[Permiso]
    debe_cambiar_password: bool


@dataclass(frozen=True)
class Identidad:
    """Usuario autenticado y su sesión (token y CSRF)."""

    usuario: Usuario
    sesion: Sesion
    token: str


@lru_cache
def _sesiones_redis() -> SesionesRedis:
    return SesionesRedis(redis.Redis.from_url(config().redis_url), config().horas_sesion * 3600)


def obtener_sesiones() -> AlmacenSesiones:
    """Dependencia sustituible en pruebas (`app.dependency_overrides[obtener_sesiones]`)."""
    return _sesiones_redis()


Sesiones = Annotated[AlmacenSesiones, Depends(obtener_sesiones)]


def cargar_usuario(c: Connection, usuario_id: int) -> Usuario | None:
    fila = c.execute(text("""
        select u.id, u.usuario::text as usuario, u.nombre, u.correo::text as correo, u.debe_cambiar_password,
               coalesce((select array_agg(r.rol::text) from app.usuario_rol r where r.usuario_id = u.id), '{}') as roles,
               coalesce((select array_agg(p.permiso::text) from app.usuario_permiso p where p.usuario_id = u.id), '{}') as permisos
        from app.usuario u where u.id = :id and u.activo
    """), {"id": usuario_id}).one_or_none()
    if fila is None:
        return None
    return Usuario(id=fila.id, usuario=fila.usuario, nombre=fila.nombre, correo=fila.correo,
                   roles=frozenset(Rol(r) for r in fila.roles), permisos=frozenset(Permiso(p) for p in fila.permisos),
                   debe_cambiar_password=fila.debe_cambiar_password)


def identidad(request: Request, sesiones: Sesiones, c: Conexion) -> Identidad:
    """Sesión válida y usuario activo. En métodos que escriben, exige el token CSRF de la sesión en la cabecera."""
    token = request.cookies.get(COOKIE)
    sesion = sesiones.obtener(token) if token else None
    if token is None or sesion is None:
        raise HTTPException(401, "Sesión no iniciada o vencida")
    if request.method not in METODOS_SEGUROS and request.headers.get(CABECERA_CSRF) != sesion.csrf:
        raise HTTPException(403, "Falta o no coincide el token CSRF")
    usuario = cargar_usuario(c, sesion.usuario_id)
    c.rollback()                                         # cierra la lectura: el endpoint abre sus propias transacciones
    if usuario is None:                                  # desactivado mientras tenía sesión
        sesiones.eliminar(token)
        raise HTTPException(401, "Sesión no iniciada o vencida")
    return Identidad(usuario=usuario, sesion=sesion, token=token)


IdentidadActual = Annotated[Identidad, Depends(identidad)]


def usuario_actual(ident: IdentidadActual) -> Usuario:
    """Usuario listo para trabajar: si tiene la contraseña temporal, solo puede cambiarla."""
    if ident.usuario.debe_cambiar_password:
        raise HTTPException(403, "Debes cambiar tu contraseña antes de continuar")
    return ident.usuario


UsuarioActual = Annotated[Usuario, Depends(usuario_actual)]


def requiere_rol(*roles: Rol) -> Callable[[Usuario], Usuario]:
    def verificar(usuario: UsuarioActual) -> Usuario:
        if not usuario.roles & set(roles):
            raise HTTPException(403, "No tienes el rol necesario para esta acción")
        return usuario

    return verificar


def requiere_permiso(permiso: Permiso) -> Callable[[Usuario], Usuario]:
    def verificar(usuario: UsuarioActual) -> Usuario:
        if permiso not in usuario.permisos:
            raise HTTPException(403, "No tienes permiso para ver esta información")
        return usuario

    return verificar


Administrador = Annotated[Usuario, Depends(requiere_rol(Rol.ADMINISTRADOR))]
