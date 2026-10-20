"""El ETL de entrada con permisos mínimos (ADR 0017): con lo que da deploy/sql/usuario-etl.sql puede cargar staging y procesar el lote,
pero no leer ni escribir en app, ni borrar staging; nadie más puede ejecutar fn_procesar_staging."""

import secrets
from pathlib import Path

import psycopg
import pytest

from .apoyo import articulo, cargar

SCRIPT = Path(__file__).resolve().parents[4] / "deploy" / "sql" / "usuario-etl.sql"


@pytest.fixture(scope="module")
def roles(bd):
    etl, otro = f"etl_prueba_{secrets.token_hex(3)}", f"otro_prueba_{secrets.token_hex(3)}"
    with psycopg.connect(bd, autocommit=True) as c:
        c.execute("do $$ begin if not exists (select 1 from pg_roles where rolname = 'nexo_app') then create role nexo_app nologin; end if; end $$")
        sql = SCRIPT.read_text().replace(":'clave'", "'x'").replace("etl_entrada", etl)
        c.execute(sql)
        c.execute(f"create role {otro} nologin")
        c.execute(f"grant usage on schema app, staging to {otro}")
    return etl, otro


def como(bd, rol):
    c = psycopg.connect(bd, autocommit=True)
    c.execute(f"set role {rol}")
    return c


def test_carga_y_procesa_un_lote_solo_con_staging(bd, roles):
    etl, _ = roles
    with como(bd, etl) as c:
        r = cargar(c, [articulo("RAD00188"), articulo("RAD00156")])
        assert r["nuevos"] == 2
        r = cargar(c, [articulo("RAD00188", descripcion="CAMBIADO")])                # segundo lote: upsert
        assert r["actualizados"] == 1
    with psycopg.connect(bd) as c:                                                    # quedó en app, auditado como ETL
        assert c.execute("select descripcion from app.articulo where item_code = 'RAD00188'").fetchone()[0] == "CAMBIADO"


def test_no_toca_app_ni_borra_staging(bd, roles):
    etl, _ = roles
    with como(bd, etl) as c:
        for sql in ("select count(*) from app.articulo", "update app.articulo set descripcion = 'x'",
                    "delete from staging.articulo_sap", "select app.fn_transicionar(1, 'VALIDADO', 'USUARIO', '1')"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                c.execute(sql)


def test_nadie_mas_procesa_lotes(bd, roles):
    _, otro = roles
    with como(bd, otro) as c, pytest.raises(psycopg.errors.InsufficientPrivilege):
        c.execute("select app.fn_procesar_staging(1)")
