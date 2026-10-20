"""Almacén de sesiones (ADR 0015): Redis en producción, memoria en pruebas.

El token viaja solo en la cookie; en el almacén se guarda su SHA-256, así una copia de Redis no sirve para suplantar a nadie.
Cada acceso renueva la expiración (cierra tras N horas sin actividad).
"""

import hashlib
import json
import secrets
import time
from dataclasses import asdict, dataclass
from typing import Protocol

import redis


@dataclass(frozen=True)
class Sesion:
    usuario_id: int
    csrf: str
    creada_en: float


def _clave(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AlmacenSesiones(Protocol):
    def crear(self, usuario_id: int) -> tuple[str, Sesion]: ...
    def obtener(self, token: str) -> Sesion | None: ...
    def eliminar(self, token: str) -> None: ...
    def eliminar_de_usuario(self, usuario_id: int) -> int: ...


def _nueva(usuario_id: int) -> tuple[str, Sesion]:
    return secrets.token_urlsafe(32), Sesion(usuario_id=usuario_id, csrf=secrets.token_urlsafe(24), creada_en=time.time())


class SesionesRedis:
    def __init__(self, cliente: redis.Redis, segundos: int):
        self.r, self.segundos = cliente, segundos

    def crear(self, usuario_id: int) -> tuple[str, Sesion]:
        token, sesion = _nueva(usuario_id)
        clave = _clave(token)
        with self.r.pipeline() as p:
            p.set(f"sesion:{clave}", json.dumps(asdict(sesion)), ex=self.segundos)
            p.sadd(f"sesiones_usuario:{usuario_id}", clave)
            p.execute()
        return token, sesion

    def obtener(self, token: str) -> Sesion | None:
        clave = f"sesion:{_clave(token)}"
        datos = self.r.getex(clave, ex=self.segundos)  # renueva la expiración en el mismo paso
        return Sesion(**json.loads(datos)) if datos else None

    def eliminar(self, token: str) -> None:
        clave = _clave(token)
        datos = self.r.getdel(f"sesion:{clave}")
        if datos:
            self.r.srem(f"sesiones_usuario:{json.loads(datos)['usuario_id']}", clave)

    def eliminar_de_usuario(self, usuario_id: int) -> int:
        indice = f"sesiones_usuario:{usuario_id}"
        claves = self.r.smembers(indice)
        n = self.r.delete(*(f"sesion:{c.decode() if isinstance(c, bytes) else c}" for c in claves)) if claves else 0
        self.r.delete(indice)
        return int(n)


class SesionesMemoria:
    """Para pruebas: mismo comportamiento, sin Redis."""

    def __init__(self, segundos: int):
        self.segundos = segundos
        self._datos: dict[str, tuple[Sesion, float]] = {}

    def crear(self, usuario_id: int) -> tuple[str, Sesion]:
        token, sesion = _nueva(usuario_id)
        self._datos[_clave(token)] = (sesion, time.time() + self.segundos)
        return token, sesion

    def obtener(self, token: str) -> Sesion | None:
        clave = _clave(token)
        sesion, vence = self._datos.get(clave, (None, 0.0))
        if sesion is None or vence < time.time():
            self._datos.pop(clave, None)
            return None
        self._datos[clave] = (sesion, time.time() + self.segundos)
        return sesion

    def eliminar(self, token: str) -> None:
        self._datos.pop(_clave(token), None)

    def eliminar_de_usuario(self, usuario_id: int) -> int:
        claves = [k for k, (s, _) in self._datos.items() if s.usuario_id == usuario_id]
        for k in claves:
            del self._datos[k]
        return len(claves)
