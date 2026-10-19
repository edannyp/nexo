"""Tareas de administración por línea de comandos.

Crear el primer administrador (en el servidor: `docker compose exec api python -m nexo_api.cli crear-admin <usuario> "<nombre>"`).
Imprime una contraseña temporal que se cambia en el primer inicio.
"""

import argparse
import sys

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .auth import contrasenas
from .core.bd import obtener_motor


def crear_admin(usuario: str, nombre: str) -> str:
    temporal = contrasenas.temporal()
    with obtener_motor().begin() as c:
        nuevo_id = c.execute(text("""
            insert into app.usuario (usuario, nombre, password_hash, debe_cambiar_password)
            values (:u, :n, :h, true) returning id
        """), {"u": usuario, "n": nombre, "h": contrasenas.hashear(temporal)}).scalar_one()
        c.execute(text("insert into app.usuario_rol values (:id, 'ADMINISTRADOR')"), {"id": nuevo_id})
        c.execute(text("""insert into audit.evento_acceso (usuario_id, usuario, tipo, agente)
                          values (:id, :u, 'ALTA', 'nexo_api.cli crear-admin')"""), {"id": nuevo_id, "u": usuario})
    return temporal


def main() -> None:
    p = argparse.ArgumentParser(prog="nexo_api.cli")
    sub = p.add_subparsers(dest="tarea", required=True)
    alta = sub.add_parser("crear-admin", help="Crea un usuario ADMINISTRADOR con contraseña temporal")
    alta.add_argument("usuario")
    alta.add_argument("nombre")
    a = p.parse_args()
    try:
        temporal = crear_admin(a.usuario, a.nombre)
    except IntegrityError:
        sys.exit(f"Ya existe un usuario llamado «{a.usuario}».")
    print(f"Administrador «{a.usuario}» creado. Contraseña temporal (se pide cambiarla al entrar): {temporal}")


if __name__ == "__main__":
    main()
