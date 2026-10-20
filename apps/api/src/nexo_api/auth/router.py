"""Sesión: entrar, quién soy, cambiar contraseña y salir (architecture/api/convenciones.md, ADR 0015)."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..core.bd import Conexion
from ..core.config import config
from ..core.errores import Problema
from . import contrasenas
from .dependencias import COOKIE, IdentidadActual, Permiso, Rol, Sesiones, Usuario, cargar_usuario
from .registro import evento, fijar_actor

router = APIRouter(prefix="/sesion", tags=["sesion"])

CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos"


class Credenciales(BaseModel):
    usuario: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class CambioPassword(BaseModel):
    actual: str = Field(min_length=1, max_length=200)
    nueva: str = Field(min_length=1, max_length=200)


class UsuarioSesion(BaseModel):
    id: int
    usuario: str
    nombre: str
    correo: str | None
    roles: list[Rol]
    permisos: list[Permiso]
    debe_cambiar_password: bool


class SesionInfo(BaseModel):
    usuario: UsuarioSesion
    csrf: str = Field(description="Enviar en la cabecera X-CSRF-Token en los métodos que escriben")


def _info(u: Usuario, csrf: str) -> SesionInfo:
    return SesionInfo(usuario=UsuarioSesion(id=u.id, usuario=u.usuario, nombre=u.nombre, correo=u.correo,
                                            roles=sorted(u.roles), permisos=sorted(u.permisos),
                                            debe_cambiar_password=u.debe_cambiar_password), csrf=csrf)


def _poner_cookie(request: Request, response: Response, token: str) -> None:
    # Secure cuando la petición llegó por HTTPS (Caddy informa el esquema con X-Forwarded-Proto).
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=request.url.scheme == "https", path="/")


@router.post("", response_model=SesionInfo, summary="Iniciar sesión",
             responses={401: {"description": "Credenciales incorrectas"}, 429: {"description": "Cuenta bloqueada temporalmente"}})
def iniciar_sesion(datos: Credenciales, request: Request, response: Response, sesiones: Sesiones, c: Conexion) -> SesionInfo:
    cfg = config()
    with c.begin():
        u = c.execute(text("""
            select id, usuario::text as usuario, password_hash, activo, intentos_fallidos, bloqueado_hasta
            from app.usuario where usuario = :u for update
        """), {"u": datos.usuario.strip()}).one_or_none()

        ahora = datetime.now(UTC)
        if u is not None and u.bloqueado_hasta and u.bloqueado_hasta > ahora:
            minutos = max(1, int((u.bloqueado_hasta - ahora).total_seconds() // 60) + 1)
            raise Problema(429, "Cuenta bloqueada temporalmente", f"Demasiados intentos fallidos. Intenta de nuevo en {minutos} min.",
                           headers={"Retry-After": str(minutos * 60)})

        correcta = contrasenas.verificar(u.password_hash if u else None, datos.password)
        if u is None or not correcta or not u.activo:
            if u is not None:
                intentos = u.intentos_fallidos + 1
                bloquear = intentos >= cfg.intentos_maximos
                c.execute(text("update app.usuario set intentos_fallidos = :i, bloqueado_hasta = :b where id = :id"),
                          {"i": 0 if bloquear else intentos, "id": u.id,
                           "b": ahora + timedelta(minutes=cfg.minutos_bloqueo) if bloquear else None})
                if bloquear:
                    evento(c, request, "BLOQUEO", u.usuario, u.id)
            evento(c, request, "ENTRADA_FALLIDA", datos.usuario.strip()[:100], u.id if u else None)
            fallo = True
        else:
            nuevo_hash = contrasenas.hashear(datos.password) if contrasenas.requiere_rehash(u.password_hash) else u.password_hash
            c.execute(text("""update app.usuario set intentos_fallidos = 0, bloqueado_hasta = null, ultimo_acceso_en = now(),
                              password_hash = :h where id = :id"""), {"id": u.id, "h": nuevo_hash})
            evento(c, request, "ENTRADA", u.usuario, u.id)
            fallo = False
    if fallo:                                            # el intento fallido queda registrado antes de responder
        raise Problema(401, CREDENCIALES_INVALIDAS)

    usuario = cargar_usuario(c, u.id)
    assert usuario is not None
    token, sesion = sesiones.crear(u.id)
    _poner_cookie(request, response, token)
    return _info(usuario, sesion.csrf)


@router.get("", response_model=SesionInfo, summary="Sesión actual", responses={401: {"description": "Sin sesión"}})
def obtener_sesion(ident: IdentidadActual) -> SesionInfo:
    return _info(ident.usuario, ident.sesion.csrf)


@router.delete("", status_code=204, summary="Cerrar sesión")
def cerrar_sesion(ident: IdentidadActual, request: Request, response: Response, sesiones: Sesiones, c: Conexion) -> None:
    sesiones.eliminar(ident.token)
    with c.begin():
        evento(c, request, "SALIDA", ident.usuario.usuario, ident.usuario.id)
    response.delete_cookie(COOKIE, path="/")


@router.post("/password", response_model=SesionInfo, summary="Cambiar la contraseña propia",
             responses={422: {"description": "La nueva contraseña no cumple la política"}})
def cambiar_password(datos: CambioPassword, ident: IdentidadActual, request: Request, response: Response,
                     sesiones: Sesiones, c: Conexion) -> SesionInfo:
    u = ident.usuario
    hash_actual = c.execute(text("select password_hash from app.usuario where id = :id"), {"id": u.id}).scalar_one()
    c.rollback()
    if not contrasenas.verificar(hash_actual, datos.actual):
        raise Problema(422, "Contraseña no válida", errors=[{"campo": "actual", "mensaje": "La contraseña actual no es correcta."}])
    problemas = contrasenas.problemas_politica(datos.nueva, u.usuario)
    if datos.nueva == datos.actual:
        problemas.append("Debe ser distinta de la actual.")
    if problemas:
        raise Problema(422, "Contraseña no válida", errors=[{"campo": "nueva", "mensaje": p} for p in problemas])

    with c.begin():
        fijar_actor(c, u.id)
        c.execute(text("update app.usuario set password_hash = :h, debe_cambiar_password = false where id = :id"),
                  {"h": contrasenas.hashear(datos.nueva), "id": u.id})
        evento(c, request, "CAMBIO_PASSWORD", u.usuario, u.id)
    # Cierra las demás sesiones del usuario y abre una nueva para este navegador
    sesiones.eliminar_de_usuario(u.id)
    token, sesion = sesiones.crear(u.id)
    _poner_cookie(request, response, token)
    actualizado = cargar_usuario(c, u.id)
    assert actualizado is not None
    return _info(actualizado, sesion.csrf)
