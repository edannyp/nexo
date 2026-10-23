# /// script
# requires-python = ">=3.12"
# ///
"""Arma los paquetes de arranque para los procesos que no son de Nexo (contratos en architecture/datos/contratos.md).

Cada paquete es un repositorio inicial: CLAUDE.md, devcontainer con la memoria de Claude persistente, el contexto de gobernanza que
le toca (copiado de este repositorio, así nunca queda desactualizado) y una base local igual a la real para probar sin servidores.

Uso:
    uv run paquetes/armar.py                 # todos
    uv run paquetes/armar.py etl-sap         # uno
Salida: entregables/<paquete>/ y entregables/<paquete>.zip (entregables/ no se versiona).
"""

import shutil
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PAQ = RAIZ / "paquetes"
SALIDA = RAIZ / "entregables"

# Lo que todo proceso debe conocer: el negocio, el alcance y los contratos con Nexo
COMUN = {
    "contexto/negocio.md": "context/negocio.md",
    "contexto/glosario.md": "context/glosario.md",
    "contexto/alcance-de-nexo.md": "context/alcance.md",
    "contexto/arquitectura/contratos.md": "architecture/datos/contratos.md",
    "contexto/arquitectura/adr/0002-etl-fuera-de-alcance.md": "architecture/adr/0002-etl-fuera-de-alcance.md",
    "contexto/arquitectura/adr/0007-nomenclatura-canonica.md": "architecture/adr/0007-nomenclatura-canonica.md",
    "contexto/arquitectura/adr/0017-usuarios-de-base-por-proceso.md": "architecture/adr/0017-usuarios-de-base-por-proceso.md",
}
ADR = "architecture/adr/"
NEXO_SQL = "apps/api/alembic/sql/"
# Base nexo local idéntica a producción: las migraciones reales (cada paquete agrega el script de su usuario)
NEXO_LOCAL = {f"base-local/sql/{p.name}": NEXO_SQL + p.name for p in sorted((RAIZ / NEXO_SQL).glob("0*.sql"))}
DB = {"db/README.md": "db/README.md", "db/aplicar.py": "db/aplicar.py", "db/ref/cargar_ref.py": "db/ref/cargar_ref.py",
      "db/consolidacion": "db/consolidacion", "db/mercado_externo": "db/mercado_externo", "db/pruebas": "db/pruebas"}

PAQUETES: dict[str, dict] = {
    "etl-sap": {
        "titulo": "ETL de entrada: SAP Business One → staging de Nexo",
        "postgres": "postgres:18",      # el servidor de nexo (10.10.60.6) es PostgreSQL 18
        "deps": ["psycopg[binary]>=3.2", "python-dotenv>=1.0", "hdbcli>=2.20", "pytest>=8"],
        "copiar": {
            "contexto/categorias.md": "context/categorias.md",
            "contexto/workflow-estados.md": "context/workflow-estados.md",
            "contexto/fuentes/sap-hana.md": "context/fuentes/sap-hana.md",
            "contexto/arquitectura/mapeo-fuentes.md": "architecture/datos/mapeo-fuentes.md",
            "contexto/arquitectura/modelo-nexo.md": "architecture/datos/modelo-nexo.md",
            **{f"contexto/arquitectura/adr/{n}": ADR + n for n in (
                "0006-etl-escribe-solo-staging.md", "0008-articulos-inactivos.md", "0010-filtro-global-tipo-articulo.md")},
            # Base local: las migraciones reales de Nexo y el usuario del ETL tal como se crea en el servidor
            **NEXO_LOCAL,
            "base-local/sql/usuario-etl.sql": "deploy/sql/usuario-etl.sql",
            # Referencia: la lectura de SAP que se usó para verificar Nexo (NO es el ETL)
            "referencia/lote_sap_local.py": "connections/exploration/lote_sap_local.py",
            "referencia/config.py": "connections/common/config.py",
            "referencia/sap_explorar.sql": "connections/sap/hana/explorar.sql",
        },
    },
    "catalogo-maestro": {
        "titulo": "Carga del catálogo maestro: diagramas y scraping → Consolidación",
        "postgres": "postgres:18",      # Consolidación vive en 10.10.60.6, PostgreSQL 18
        "deps": ["psycopg[binary]>=3.2", "python-dotenv>=1.0", "pytest>=8"],
        "copiar": {
            "contexto/categorias.md": "context/categorias.md",
            **{f"contexto/fuentes/{n}": f"context/fuentes/{n}" for n in (
                "consolidacion.md", "diagrams.md", "scraping.md", "autocare.md", "minio.md")},
            "contexto/arquitectura/modelo-consolidacion.md": "architecture/datos/modelo-consolidacion.md",
            **{f"contexto/arquitectura/adr/{n}": ADR + n for n in (
                "0009-esquemas-consolidacion-y-mercado-externo.md", "0011-consolidacion-catalogo-maestro.md",
                "0019-catalogo-configurable-atributos.md", "0024-copia-autocare-versionada.md",
                "0026-carga-catalogo-maestro.md")},
            **DB,
        },
    },
    "ia-vehiculos": {
        "titulo": "IA con búsqueda web: vehículos fuera de AutoCare → MercadoExterno",
        "postgres": "postgres:18",
        "deps": ["psycopg[binary]>=3.2", "python-dotenv>=1.0", "pytest>=8"],
        "copiar": {
            **{f"contexto/fuentes/{n}": f"context/fuentes/{n}" for n in ("mercado-externo.md", "autocare.md")},
            "contexto/arquitectura/modelo-mercado-externo.md": "architecture/datos/modelo-mercado-externo.md",
            **{f"contexto/arquitectura/adr/{n}": ADR + n for n in (
                "0009-esquemas-consolidacion-y-mercado-externo.md", "0014-extension-vcdb-vehiculos-custom.md",
                "0024-copia-autocare-versionada.md")},
            **DB,
        },
    },
    "agente-revision-catalogo": {
        "titulo": "Agente de revisión del catálogo: Consolidación → verificaciones de Nexo",
        "postgres": "postgres:18",
        "deps": ["psycopg[binary]>=3.2", "python-dotenv>=1.0", "anthropic", "pytest>=8"],
        "copiar": {
            "contexto/workflow-estados.md": "context/workflow-estados.md",
            "contexto/fuentes/consolidacion.md": "context/fuentes/consolidacion.md",
            "contexto/arquitectura/modelo-consolidacion.md": "architecture/datos/modelo-consolidacion.md",
            **{f"contexto/arquitectura/adr/{n}": ADR + n for n in (
                "0011-consolidacion-catalogo-maestro.md", "0012-doble-control-y-verificacion.md")},
            **NEXO_LOCAL,
            "base-local/sql/usuario-agente-revision-catalogo.sql": "deploy/sql/usuario-agente-revision-catalogo.sql",
            # Consolidación local (solo para leer estados de partes en las pruebas)
            "db/aplicar.py": "db/aplicar.py",
            "db/consolidacion": "db/consolidacion",
            "db/pruebas/ref_minimo_consolidacion.sql": "db/pruebas/ref_minimo_consolidacion.sql",
            "contexto/arquitectura/adr/0007-nomenclatura-canonica.md": ADR + "0007-nomenclatura-canonica.md",
        },
    },
}


def compose(nombre: str, postgres: str | None) -> str:
    base = """      - path: ../.env
        required: false
""" + ("""    depends_on:
      postgres:
        condition: service_healthy
""" if postgres else "")
    texto = f"""# Ambiente de desarrollo de {nombre}. La memoria y el historial de Claude Code viven en el volumen claude-config:
# sobreviven a "Rebuild Container" y solo se pierden con `docker volume rm`.
name: {nombre}

services:
  workspace:
    build: .
    command: sleep infinity
    volumes:
      - ..:/workspace:cached
      - claude-config:/home/vscode/.claude
      - commandhistory:/home/vscode/.commandhistory
    environment:
      CLAUDE_CONFIG_DIR: /home/vscode/.claude
    env_file:
{base}"""
    if postgres:
        texto += f"""
  # Base local desechable, de la misma versión que el servidor. Las pruebas corren aquí, nunca contra servidores.
  postgres:
    image: {postgres}
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - pgdata:/var/lib/postgresql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 10
"""
    texto += "\nvolumes:\n  claude-config:\n  commandhistory:\n" + ("  pgdata:\n" if postgres else "")
    return texto


def pyproject(nombre: str, titulo: str, deps: list[str]) -> str:
    lista = "\n".join(f'  "{d}",' for d in deps)
    return f"""[project]
name = "{nombre}"
version = "0.1.0"
description = "{titulo}"
requires-python = ">=3.13"
dependencies = [
{lista}
]

[tool.uv]
package = false
"""


def copiar(origen: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if origen.is_dir():
        shutil.copytree(origen, destino, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)
    else:
        shutil.copy2(origen, destino)


def armar(nombre: str) -> Path:
    p = PAQUETES[nombre]
    destino = SALIDA / nombre
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(PAQ / "_plantilla", destino)
    for d, o in {**COMUN, **p["copiar"]}.items():
        copiar(RAIZ / o, destino / d)
    shutil.copytree(PAQ / nombre, destino, dirs_exist_ok=True)       # lo propio del paquete (CLAUDE.md, README…) al final
    (destino / ".devcontainer/devcontainer.json").write_text(
        (destino / ".devcontainer/devcontainer.json").read_text().replace("{{NOMBRE}}", nombre))
    (destino / ".devcontainer/docker-compose.yml").write_text(compose(nombre, p["postgres"]))
    (destino / "pyproject.toml").write_text(pyproject(nombre, p["titulo"], p["deps"]))
    (destino / "contexto/LEEME.md").write_text(
        "# Contexto copiado de Nexo\n\nEstos documentos vienen del repositorio de Nexo (gobernanza del artículo) y se regeneran con\n"
        "`paquetes/armar.py`. **No se editan aquí**: si algo no cuadra, se pide el cambio al equipo de Nexo. Algunos enlaces internos\n"
        "apuntan a archivos de Nexo que no vienen en este paquete.\n")
    for sh in destino.rglob("*.sh"):
        sh.chmod(0o755)
    archivo = SALIDA / f"{nombre}.zip"
    with zipfile.ZipFile(archivo, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(destino.rglob("*")):
            if f.is_file():
                z.write(f, Path(nombre) / f.relative_to(destino))
    return archivo


def main() -> None:
    nombres = sys.argv[1:] or list(PAQUETES)
    for n in nombres:
        if n not in PAQUETES:
            sys.exit(f"Paquete desconocido: {n}. Opciones: {', '.join(PAQUETES)}")
    SALIDA.mkdir(exist_ok=True)
    for n in nombres:
        z = armar(n)
        print(f"{n}: {z.relative_to(RAIZ)} ({z.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
