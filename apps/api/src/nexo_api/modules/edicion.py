"""Regla común de edición de un artículo (ficha, aplicaciones…): solo quien lo tiene reservado, activo, en Pendiente o Rechazado
(context/workflow-estados.md regla 8). Las escrituras suben la versión del artículo (control optimista)."""

from sqlalchemy import Connection, text

from ..auth.dependencias import Rol, Usuario
from ..core.errores import Problema

ESTADOS_EDITABLES = {"PENDIENTE", "RECHAZADO"}
ROLES_TRABAJO = {Rol.OPERADOR, Rol.SUPERVISOR}       # quienes toman y trabajan artículos (bandeja de trabajo)


def articulo(c: Connection, item_code: str, bloquear: bool = False):
    a = c.execute(text(f"""
        select a.*, a.estado::text as estado, coalesce(a.asignado_hasta > now(), false) as reservado, u.nombre as reservado_por
        from app.articulo a left join app.usuario u on u.id = a.asignado_a
        where a.item_code = upper(:ic) {'for update of a' if bloquear else ''}
    """), {"ic": item_code}).one_or_none()
    if a is None:
        raise Problema(404, "El artículo no existe")
    return a


def razon_no_editable(a, usuario: Usuario) -> str | None:
    """None si el usuario puede editar; si no, la razón para mostrarla."""
    if not a.activo:
        return "El artículo está inactivo."
    if a.estado not in ESTADOS_EDITABLES:
        return "Solo se edita en Pendiente o Rechazado."
    if not usuario.roles & ROLES_TRABAJO:
        return ("Tu usuario no tiene el rol Operador ni Supervisor: pide a un administrador que te lo asigne "
                "(Administración → Usuarios).")
    if not (a.asignado_a == usuario.id and a.reservado):
        return "Toma el artículo para editarlo." if not a.reservado else f"{a.reservado_por} lo está trabajando."
    return None


def puede_tomar(a, usuario: Usuario) -> bool:
    """Lo puede tomar ahora para editarlo: solo le falta reservarlo."""
    return razon_no_editable(a, usuario) == "Toma el artículo para editarlo."


def bloquear_para_editar(c: Connection, item_code: str, usuario: Usuario, version: int):
    """Dentro de una transacción: bloquea el artículo y verifica reserva, estado y versión. Devuelve la fila."""
    a = articulo(c, item_code, bloquear=True)
    razon = razon_no_editable(a, usuario)
    if razon:
        raise Problema(409, "No puedes editar el artículo ahora", razon)
    if a.version != version:
        raise Problema(409, "Otro usuario cambió este artículo", "Recarga para ver los cambios antes de guardar.")
    return a


def subir_version(c: Connection, articulo_id: int) -> None:
    c.execute(text("update app.articulo set version = version + 1, actualizado_en = now() where id = :a"), {"a": articulo_id})
