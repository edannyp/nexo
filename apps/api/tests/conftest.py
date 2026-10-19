"""Pruebas de integración contra bases LOCALES desechables (nexo_prueba_*). Nunca contra servidores."""

import os
import subprocess
from pathlib import Path

import psycopg
import pytest

HOST = os.getenv("PRUEBAS_PG_HOST", "postgres")
ADMIN = f"host={HOST} dbname=postgres user=postgres password=postgres"
API = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bd(request) -> str:
    """Una base desechable por módulo de pruebas: cada escenario parte de cero."""
    nombre = "nexo_prueba_" + request.module.__name__.rsplit(".", 1)[-1].removeprefix("test_")
    with psycopg.connect(ADMIN, autocommit=True) as c:
        c.execute(f"drop database if exists {nombre} with (force)")
        c.execute(f"create database {nombre}")
    url = f"postgresql+psycopg://postgres:postgres@{HOST}:5432/{nombre}"
    subprocess.run(["uv", "run", "-q", "alembic", "-x", f"url={url}", "upgrade", "head"], cwd=API, check=True)
    return f"host={HOST} dbname={nombre} user=postgres password=postgres"


@pytest.fixture
def conn(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        yield c
