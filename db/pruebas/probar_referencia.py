# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2", "python-dotenv>=1.0"]
# ///
"""Pruebas de la copia de AutoCare versionada (db/ref/cargar_ref.py, ADR 0024) contra un AutoCare MÍNIMO local
(db/pruebas/autocare_minimo.sql) y Consolidación / MercadoExterno locales con sus migraciones reales. Nunca contra servidores.

Uso: uv run db/pruebas/probar_referencia.py [--host postgres]
"""

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import psycopg

DB = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cargar_ref", DB / "ref" / "cargar_ref.py")
cargar_ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cargar_ref)

fallas = 0


def check(ok: bool, nombre: str) -> None:
    global fallas
    print(f"  {'✔' if ok else '✘'} {nombre}")
    fallas += not ok


def base_nueva(host: str, nombre: str) -> str:
    with psycopg.connect(f"host={host} dbname=postgres user=postgres password=postgres", autocommit=True) as c:
        c.execute(f"drop database if exists {nombre} with (force)")
        c.execute(f"create database {nombre}")
    return f"host={host} dbname={nombre} user=postgres password=postgres"


def cargar(*args, **kw) -> str:
    """Corre la carga y devuelve lo que imprimió (o el motivo si se detuvo)."""
    import contextlib
    import io
    salida = io.StringIO()
    try:
        with contextlib.redirect_stdout(salida):
            cargar_ref.cargar(*args, **kw)
    except SystemExit as e:
        return f"{salida.getvalue()}SALIDA: {e}"
    return salida.getvalue()


def historial(dsn: str, tabla: str) -> tuple:
    with psycopg.connect(dsn) as c:
        return c.execute("""select altas, cambios, bajas, reactivados, impacto from ref.historial_carga where tabla = %s
                            order by id desc limit 1""", (tabla,)).fetchone()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="postgres")
    host = p.parse_args().host
    origen = base_nueva(host, "autocare_prueba")
    with psycopg.connect(origen, autocommit=True) as c:
        c.execute((DB / "pruebas" / "autocare_minimo.sql").read_text())
    cons = base_nueva(host, "consolidacion_ref_prueba")
    subprocess.run(["uv", "run", "-q", str(DB / "aplicar.py"), "consolidacion", "--dsn", cons], check=True, capture_output=True)

    print("== Consolidación: primera carga, solo nuestros tipos de parte")
    salida = cargar("consolidacion", cons, origen)
    with psycopg.connect(cons) as c:
        pts = [r[0] for r in c.execute("select part_terminology_id from ref.part_terminology order by 1")]
        check(pts == [2172, 6708], f"PCdb solo de nuestros tipos: {pts}")
        check(c.execute("select count(*) from ref.valor_permitido where valid_value_id = 777").fetchone()[0] == 0,
              "PAdb de otros tipos no se copia")
        check(c.execute("select count(*) from ref.base_vehicle").fetchone()[0] == 15, "VCdb completo (15 vehículos)")
        check(c.execute("select versiones ->> 'VCdb' from ref.historial_carga limit 1").fetchone()[0] is not None,
              "el historial guarda las versiones de AutoCare")
    check("+15 altas" in salida, "informa las altas")

    print("== Una parte del catálogo usa el valor 444 (Down Flow) y el vehículo 802006")
    with psycopg.connect(cons, autocommit=True) as c:
        c.execute("insert into catalogo.fuente (codigo, nombre, tipo, prioridad) values ('PRUEBA', 'Prueba', 'MANUAL', 5)")
        corrida = c.execute("""insert into carga.corrida (fuente_id, version_proceso) select id, 'prueba' from catalogo.fuente
                               where codigo = 'PRUEBA' returning id""").fetchone()[0]
        parte = c.execute("insert into catalogo.parte (part_terminology_id, descripcion) values (2172, 'Radiador de prueba') returning id").fetchone()[0]
        reg = c.execute("""insert into catalogo.registro_fuente (fuente_id, id_en_fuente, datos_crudos, hash_contenido, parte_id, vinculo_metodo,
                           vinculo_confianza, corrida_id) select id, 'P1', '{}', 'h', %s, 'MANUAL', 1, %s from catalogo.fuente where codigo = 'PRUEBA'
                           returning id""", (parte, corrida)).fetchone()[0]
        c.execute("insert into catalogo.parte_atributo (parte_id, registro_fuente_id, paid, valid_value_id) values (%s, %s, 7448, 444)",
                  (parte, reg))
        c.execute("""insert into catalogo.parte_aplicacion (parte_id, registro_fuente_id, base_vehicle_id, vcdb_version)
                     values (%s, %s, 802006, '1.0')""", (parte, reg))

    print("== AutoCare publica la versión 2: quita 444 y el vehículo 802006, renombra 391, agrega un vehículo")
    with psycopg.connect(origen, autocommit=True) as c:
        c.execute("delete from padb_config.valid_value_assignment where valid_value_id = 444")
        c.execute("update padb_base.valid_value set valid_value = 'Crossflow' where valid_value_id = 391")
        c.execute("delete from vcdb_base.base_vehicle where base_vehicle_id = 802006")
        c.execute("insert into vcdb_base.base_vehicle values (812021, 2021, 903, 9102)")
        c.execute("update vcdb_parts.db_version set version = '2.0'")
    salida = cargar("consolidacion", cons, origen)
    altas, cambios, bajas, react, imp = historial(cons, "ref.valor_permitido")
    check((cambios, bajas) == (1, 1), f"valores: 1 cambio (391) y 1 baja (444): {cambios}, {bajas}")
    check("atributos de partes del catálogo con ese valor" in imp, f"impacto: la parte que usa 444: {json.dumps(imp)[:90]}")
    altas, cambios, bajas, react, imp = historial(cons, "ref.base_vehicle")
    check((altas, bajas) == (1, 1), f"vehículos: 1 alta y 1 baja: {altas}, {bajas}")
    check("aplicaciones del catálogo con ese vehículo" in imp, "impacto: la aplicación con 802006")
    check("⚠ impacto" in salida, "el impacto se muestra al cargar")
    with psycopg.connect(cons) as c:
        check(c.execute("select obsoleto_en is not null from ref.valor_permitido where valid_value_id = 444").fetchone()[0],
              "444 queda obsoleto, no se borra")
        check(c.execute("select valor from ref.valor_permitido where valid_value_id = 391").fetchone()[0] == "Crossflow", "391 renombrado")

    print("== Lo obsoleto no se asigna de nuevo; lo que ya estaba se conserva")
    with psycopg.connect(cons, autocommit=True) as c:
        try:
            c.execute("""insert into catalogo.parte_atributo (parte_id, registro_fuente_id, paid, valid_value_id)
                         select parte_id, registro_fuente_id, 7448, 444 from catalogo.parte_atributo limit 1""")
            check(False, "rechaza 444 en un atributo nuevo")
        except psycopg.errors.RaiseException as e:
            check("unique" not in str(e), f"rechaza 444 en un atributo nuevo ({str(e).splitlines()[0][:60]})")
        except psycopg.errors.UniqueViolation:
            c.execute("update catalogo.parte_atributo set valor_original = 'x' where valid_value_id = 444")
            check(True, "la fila existente con 444 se puede actualizar")
        try:
            c.execute("""insert into catalogo.parte_aplicacion (parte_id, registro_fuente_id, base_vehicle_id, vcdb_version)
                         select parte_id, registro_fuente_id, 802006, '2.0' from catalogo.parte_aplicacion limit 1""")
            check(False, "rechaza el vehículo obsoleto en una aplicación nueva")
        except psycopg.errors.RaiseException:
            check(True, "rechaza el vehículo obsoleto en una aplicación nueva")
        c.execute("update catalogo.parte_aplicacion set notas = 'revisar' where base_vehicle_id = 802006")
        check(True, "la aplicación existente con 802006 se puede actualizar")

    print("== Si AutoCare vuelve a publicarlo, se reactiva")
    with psycopg.connect(origen, autocommit=True) as c:
        c.execute("insert into padb_config.valid_value_assignment values (4, 444)")
    cargar("consolidacion", cons, origen)
    _, _, _, react, _ = historial(cons, "ref.valor_permitido")
    with psycopg.connect(cons) as c:
        check(react == 1 and c.execute("select obsoleto_en is null from ref.valor_permitido where valid_value_id = 444").fetchone()[0],
              "444 reactivado")

    print("== Defensa: un origen que perdió más del 20 % (y más de 10 filas) no se aplica")
    with psycopg.connect(origen, autocommit=True) as c:
        c.execute("delete from vcdb_base.base_vehicle")                          # p. ej. una consulta que vino vacía
    salida = cargar("consolidacion", cons, origen)
    with psycopg.connect(cons) as c:
        obsoletos = c.execute("select count(*) from ref.base_vehicle where obsoleto_en is not null").fetchone()[0]
    check("[alto] ref.base_vehicle" in salida and obsoletos == 1, f"se detiene y no toca nada ({obsoletos} obsoleto, el de antes)")
    salida = cargar("consolidacion", cons, origen, forzar=True)
    with psycopg.connect(cons) as c:
        obsoletos = c.execute("select count(*) from ref.base_vehicle where obsoleto_en is not null").fetchone()[0]
    check(obsoletos == 16, f"con --forzar sí se aplica ({obsoletos} obsoletos)")

    print("== MercadoExterno: la misma copia versionada")
    me = base_nueva(host, "mercado_ref_prueba")
    subprocess.run(["uv", "run", "-q", str(DB / "aplicar.py"), "mercado_externo", "--dsn", me], check=True, capture_output=True)
    cargar("mercado_externo", me, origen)
    with psycopg.connect(origen, autocommit=True) as c:
        c.execute("insert into vcdb_base.base_vehicle select 800000 + y, y, 901, 9101 from generate_series(2005, 2015) y")
        c.execute("insert into vcdb_base.base_vehicle values (812021, 2021, 903, 9102)")
    cargar("mercado_externo", me, origen)
    with psycopg.connect(origen, autocommit=True) as c:
        c.execute("delete from vcdb_base.base_vehicle where base_vehicle_id = 812021")
    cargar("mercado_externo", me, origen)
    altas, cambios, bajas, react, imp = historial(me, "ref.base_vehicle")
    check(bajas == 1, f"MercadoExterno marca la baja del vehículo ({bajas})")

    print(f"\n{'Todas las pruebas OK' if not fallas else f'{fallas} FALLAS'}")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
