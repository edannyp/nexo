"""Registro de accesos y actor de auditoría."""

import ipaddress

from fastapi import Request
from sqlalchemy import Connection, text


def fijar_actor(c: Connection, usuario_id: int) -> None:
    """Quién hace los cambios de esta transacción (lo leen los triggers de auditoría)."""
    c.execute(text("select set_config('app.usuario_id', :id, true)"), {"id": str(usuario_id)})


def _ip(request: Request | None) -> str | None:
    """IP del cliente si es válida (Caddy la informa con X-Forwarded-For); con un socket o un cliente de pruebas no hay IP."""
    host = request.client.host if request and request.client else None
    try:
        return str(ipaddress.ip_address(host)) if host else None
    except ValueError:
        return None


def evento(c: Connection, request: Request | None, tipo: str, usuario: str, usuario_id: int | None,
           actor_id: int | None = None) -> None:
    c.execute(text("""
        insert into audit.evento_acceso (usuario_id, usuario, tipo, actor_id, ip, agente)
        values (:usuario_id, :usuario, :tipo, :actor_id, cast(:ip as inet), :agente)
    """), {
        "usuario_id": usuario_id, "usuario": usuario, "tipo": tipo, "actor_id": actor_id,
        "ip": _ip(request),
        "agente": (request.headers.get("user-agent") or "")[:300] if request else None,
    })
