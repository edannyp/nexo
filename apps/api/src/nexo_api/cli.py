"""Tareas de administración por línea de comandos.

En el servidor: `docker compose exec api python -m nexo_api.cli <tarea>`.
- crear-admin <usuario> "<nombre>": primer administrador, con contraseña temporal que se cambia en el primer inicio.
- actualizar-ventas: refresca la copia de apoyo de ventas desde ClickHouse (programarla a diario; ADR 0022).
- importar-fotos: importación inicial de las fotos propias que ya están en MinIO (repetible; ADR 0013).
"""

import argparse
import sys

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .auth import contrasenas
from .core.bd import obtener_motor
from .core.config import config


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
    sub.add_parser("actualizar-ventas", help="Refresca las ventas de apoyo desde ClickHouse")
    sub.add_parser("importar-fotos", help="Importa las fotos propias que ya están en MinIO")
    a = p.parse_args()

    if a.tarea == "crear-admin":
        try:
            temporal = crear_admin(a.usuario, a.nombre)
        except IntegrityError:
            sys.exit(f"Ya existe un usuario llamado «{a.usuario}».")
        print(f"Administrador «{a.usuario}» creado. Contraseña temporal (se pide cambiarla al entrar): {temporal}")

    elif a.tarea == "actualizar-ventas":
        from .adapters.clickhouse import VentasClickHouse
        from .tareas.ventas import actualizar_ventas

        with obtener_motor().connect() as c:
            r = actualizar_ventas(c, VentasClickHouse(config()))
        print(f"Ventas desde {r.desde:%Y-%m}: {r.filas} filas de {r.articulos} artículos; {r.referencias} clasificaciones de referencia.")

    elif a.tarea == "importar-fotos":
        from .adapters.minio import FotosMinio
        from .tareas.fotos import importar_fotos

        with obtener_motor().connect() as c:
            r = importar_fotos(c, FotosMinio(config()))
        print(f"Fotos importadas: {r.importadas} (ya estaban: {r.ya_estaban}) de {r.articulos} artículos.")
        if r.carpetas_sin_articulo:
            print(f"Carpetas que no son un artículo de Nexo ({len(r.carpetas_sin_articulo)}), no se asociaron:",
                  ", ".join(r.carpetas_sin_articulo[:20]), "…" if len(r.carpetas_sin_articulo) > 20 else "")
        if r.no_son_imagen:
            print(f"Archivos fuera de la convención o que no son imagen ({len(r.no_son_imagen)}):", ", ".join(r.no_son_imagen[:10]))


if __name__ == "__main__":
    main()
