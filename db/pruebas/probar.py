# /// script
# requires-python = ">=3.12"
# dependencies = ["psycopg[binary]>=3.2"]
# ///
"""Pruebas del contrato de Consolidación y MercadoExterno sobre bases LOCALES desechables.

Crea `consolidacion_prueba` y `mercado_externo_prueba` en el Postgres local, aplica migraciones,
carga la referencia mínima y comprueba que lo válido entra y lo que viola el contrato se rechaza.

Uso:  uv run db/pruebas/probar.py [--host postgres]
"""

import argparse
import subprocess
import sys
from pathlib import Path

import psycopg

DB = Path(__file__).resolve().parents[1]
resultados: list[tuple[bool, str]] = []


def check(ok: bool, nombre: str) -> None:
    resultados.append((ok, nombre))
    print(f"  {'✔' if ok else '✘'} {nombre}")


def rechaza(conn: psycopg.Connection, nombre: str, sql: str, params=None, contiene: str = "") -> None:
    """La sentencia debe fallar (y el mensaje contener `contiene`)."""
    try:
        with conn.transaction():
            conn.execute(sql, params)
        check(False, f"{nombre} (se aceptó y debía rechazarse)")
    except psycopg.Error as e:
        msg = str(e).split("\n")[0]
        check(contiene.lower() in msg.lower(), f"{nombre} → {msg[:110]}")


def preparar(host: str, base: str, fixture: str) -> str:
    nombre = f"{base}_prueba"
    with psycopg.connect(f"host={host} dbname=postgres user=postgres password=postgres", autocommit=True) as c:
        c.execute(f"drop database if exists {nombre} with (force)")
        c.execute(f"create database {nombre}")
    dsn = f"host={host} dbname={nombre} user=postgres password=postgres"
    subprocess.run(["uv", "run", "-q", str(DB / "aplicar.py"), base, "--dsn", dsn], check=True)
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute((DB / "pruebas" / fixture).read_text())
    return dsn


def probar_consolidacion(dsn: str) -> None:
    print("\n== Consolidación")
    with psycopg.connect(dsn, autocommit=True) as c:
        c.execute((DB / "consolidacion" / "ejemplos" / "ejemplo_carga.sql").read_text())
        partes = c.execute("select count(*) from catalogo.parte").fetchone()[0]
        check(partes == 3, f"ejemplo: 3 partes cargadas ({partes})")
        norm = c.execute("select numero_norm from catalogo.parte_numero where numero = '568.770.38'").fetchone()[0]
        check(norm == "56877038", f"numero_norm calculado: 568.770.38 → {norm}")
        apps = c.execute("select count(*) from catalogo.parte_aplicacion").fetchone()[0]
        check(apps == 11, f"Grand Vitara 2005-2015 → 11 aplicaciones ACES ({apps})")
        sin = c.execute("select count(*) from catalogo.aplicacion_sin_homologar").fetchone()[0]
        check(sin == 1, f"Hyundai sin modelo → 1 aplicación sin homologar ({sin})")
        fila = c.execute("select panal_alto_mm, panal_largo_mm, panal_ancho_mm from catalogo.v_parte_busqueda where descripcion like '%Ford%'").fetchone()
        check(fila == (770, 588, 36), f"vista de búsqueda con medidas {fila}")
        corrida = c.execute("select estado from carga.corrida").fetchone()[0]
        check(corrida == "COMPLETA", "corrida cerrada")

        parte = c.execute("select id from catalogo.parte order by id limit 1").fetchone()[0]
        reg = c.execute("select id from catalogo.registro_fuente order by id limit 1").fetchone()[0]

        print("  -- el contrato rechaza:")
        rechaza(c, "DELETE de una parte", "delete from catalogo.parte where id = %s", (parte,), "no se borra")
        rechaza(c, "registro fuera de una corrida abierta",
                "insert into catalogo.registro_fuente (fuente_id, id_en_fuente, datos_crudos, hash_contenido, corrida_id) "
                "select fuente_id, 'X1', '{}', 'h', id from carga.corrida", None, "no está EN_PROCESO")
        rechaza(c, "mismo id_en_fuente dos veces",
                "insert into carga.corrida (fuente_id, version_proceso) select id, 't' from catalogo.fuente;"
                "insert into catalogo.registro_fuente (fuente_id, id_en_fuente, datos_crudos, hash_contenido, corrida_id) "
                "select fuente_id, '905096', '{}', 'h', (select max(id) from carga.corrida) from catalogo.registro_fuente limit 1",
                None, "duplicate key")
        rechaza(c, "atributo PAdb que no aplica al tipo de parte",
                "insert into catalogo.parte_atributo (parte_id, registro_fuente_id, paid, valor_texto) values (%s, %s, 9999, 'x')",
                (parte, reg), "no aplica")
        rechaza(c, "valor de lista inválido",
                "insert into catalogo.parte_atributo (parte_id, registro_fuente_id, paid, valid_value_id) values (%s, %s, 302, 123)",
                (parte, reg), "no es válido")
        rechaza(c, "medida sin unidad",
                "insert into catalogo.parte_atributo (parte_id, registro_fuente_id, paid, valor_num) values (%s, %s, 267, 300)",
                (parte, reg), "requiere uom_code")
        rechaza(c, "atributo con dos valores a la vez",
                "insert into catalogo.parte_atributo (parte_id, registro_fuente_id, paid, valor_num, valor_texto, uom_code) values (%s, %s, 267, 300, 'x', 'MM')",
                (parte, reg), "check")
        rechaza(c, "base_vehicle que no existe en AutoCare",
                "insert into catalogo.parte_aplicacion (parte_id, registro_fuente_id, base_vehicle_id, vcdb_version) values (%s, %s, 123, '2.0')",
                (parte, reg), "no existe en AutoCare")
        rechaza(c, "aplicación con vehículo y equipo a la vez",
                "insert into catalogo.parte_aplicacion (parte_id, registro_fuente_id, base_vehicle_id, equipment_base_id, vcdb_version) values (%s, %s, 802010, 700001, '2.0')",
                (parte, reg), "check")
        rechaza(c, "parte FUSIONADA sin destino",
                "update catalogo.parte set estado = 'FUSIONADA' where id = %s", (parte,), "check")
        rechaza(c, "tipo de parte inexistente en PCdb",
                "insert into catalogo.parte (part_terminology_id) values (1)", None, "foreign key")

        print("  -- el contrato acepta:")
        c.execute("insert into catalogo.parte_aplicacion (parte_id, registro_fuente_id, base_vehicle_id, vcdb_version) "
                  "values (%s, %s, 1000000005, '2.0')", (parte, reg))
        check(True, "aplicación a vehículo de MercadoExterno (ID ≥ 1 000 000 000)")
        c.execute("insert into catalogo.parte_atributo (parte_id, registro_fuente_id, paid, valor_num) values (%s, %s, 5061, 2)", (parte, reg))
        check(True, "atributo numérico sin unidad cuando PAdb no la exige (Core Row Quantity)")
        otra = c.execute("select id from catalogo.parte order by id desc limit 1").fetchone()[0]
        c.execute("update catalogo.parte set estado = 'FUSIONADA', fusionada_en_id = %s where id = %s", (otra, parte))
        check(True, "fusionar una parte en otra (sin borrar)")


def probar_mercado(dsn: str) -> None:
    print("\n== MercadoExterno")
    ev = '["https://ejemplo.com/ficha"]'
    with psycopg.connect(dsn, autocommit=True) as c:
        f = "select * from vcdb.fn_registrar_vehiculo(%s::text, %s::text, %s::int, %s::int, %s::vcdb.origen, %s::text, %s::jsonb, %s::numeric, %s::text[])"

        r = c.execute(f, ("SUZUKI", "Grand Vitara", 2010, 2011, "IA_WEB", "ia-busqueda-web", ev, 0.9, None)).fetchall()
        check(all(x[2] == "AUTOCARE" and not x[3] for x in r), f"vehículo que ya está en AutoCare → devuelve su ID, no inserta {r}")

        r = c.execute(f, ("Changan", "CS35 Plus", 2021, 2023, "IA_WEB", "ia-busqueda-web", ev, 0.8, ["GTM"])).fetchall()
        check(len(r) == 3 and all(x[1] >= 1_000_000_000 and x[3] for x in r),
              f"modelo nuevo de marca existente (Changan) → 3 base vehicles ≥ 1e9 {[x[1] for x in r]}")
        mk = c.execute("select count(*) from vcdb.make").fetchone()[0]
        check(mk == 0, "no duplica la marca Changan (reutiliza make_id de AutoCare)")
        reg = c.execute("select count(*) from vcdb.base_vehicle_region").fetchone()[0]
        check(reg == 3, f"región GTM registrada por año ({reg})")

        r2 = c.execute(f, ("CHANGAN", "cs-35 plus", 2021, 2023, "APP", "usuario.operador", ev, 0.9, None)).fetchall()
        check([x[1] for x in r2] == [x[1] for x in r] and not any(x[3] for x in r2),
              "la APP pide lo mismo con otra escritura → mismos IDs, nada nuevo")

        r = c.execute(f, ("Great Wall", "Wingle 5", 2015, 2015, "IA_WEB", "ia-busqueda-web", ev, 0.7, ["GTM", "SLV"])).fetchall()
        mk = c.execute("select make_id, make_name from vcdb.make").fetchone()
        check(mk[0] >= 1_000_000_000 and r[0][3], f"marca nueva (Great Wall) → make propio {mk}")

        r = c.execute("select * from vcdb.fn_registrar_equipo('Perkins Engines Company Ltd', '1104C-44T', 'APP'::vcdb.origen, 'op', %s::jsonb, 0.9)", (ev,)).fetchone()
        check(r[1] == "AUTOCARE" and not r[2], f"equipo que ya está en AutoCare {r}")
        r = c.execute("select * from vcdb.fn_registrar_equipo('Generac', 'SD150', 'APP'::vcdb.origen, 'op', %s::jsonb, 0.9)", (ev,)).fetchone()
        check(r[0] >= 1_000_000_000 and r[2], f"equipo nuevo (Generac SD150) {r}")

        n = c.execute("select count(*) from vcdb.v_base_vehicle where make_name = 'Changan'").fetchone()[0]
        check(n == 7, f"vista unificada: Changan = 4 AutoCare + 3 propios ({n})")

        print("  -- el contrato rechaza:")
        rechaza(c, "registrar sin evidencia", f, ("Tata", "Xenon", 2015, 2015, "IA_WEB", "ia", "[]", 0.5, None), "evidencia")
        rechaza(c, "rango de años invertido", f, ("Tata", "Xenon", 2016, 2015, "IA_WEB", "ia", ev, 0.5, None), "rango de años")
        rechaza(c, "región inexistente", f, ("Tata", "Xenon", 2015, 2015, "IA_WEB", "ia", ev, 0.5, ["XXX"]), "región")
        rechaza(c, "insertar directo una marca que ya está en AutoCare",
                "insert into vcdb.make (make_name, origen, creado_por, confianza) values ('SUZUKI', 'APP', 'x', 1)", None, "ya existe en AutoCare")
        rechaza(c, "insertar directo un modelo que ya está en AutoCare para esa marca",
                "insert into vcdb.model (model_name, make_id, origen, creado_por, confianza) values ('grand-vitara', 901, 'APP', 'x', 1)",
                None, "ya existe en AutoCare")
        rechaza(c, "insertar directo un fabricante de equipos que ya está en AutoCare",
                "insert into vcdb.mfr (mfr_name, origen, creado_por) values ('CUMMINS', 'APP', 'x')", None, "ya existe en AutoCare")
        rechaza(c, "insertar directo un base vehicle que ya está en AutoCare",
                "insert into vcdb.base_vehicle (year_id, make_id, model_id, origen, creado_por, confianza) values (2010, 901, 9101, 'APP', 'x', 1)",
                None, "ya existe en AutoCare")
        rechaza(c, "DELETE", "delete from vcdb.base_vehicle", None, "no se borra")

        print("  -- configuraciones (vehículo base + submodelo + motor):")
        g = ("select * from vcdb.fn_registrar_configuracion(%s::int, %s::text, %s::numeric, %s::smallint, %s::text, "
             "'APP'::vcdb.origen, 'op'::text, %s::text, %s::text)")
        bv = c.execute("select base_vehicle_id from vcdb.v_base_vehicle where make_name = 'Changan' and base_vehicle_id >= 1000000000 "
                       "order by base_vehicle_id limit 1").fetchone()[0]
        r1 = c.execute(g, (bv, "Comfort", 1.6, 4, "gas", None, "JL478QEE")).fetchone()
        check(r1[0] >= 1_000_000_000 and r1[1] >= 1_000_000_000 and r1[2], f"configuración nueva en vehículo propio {r1}")
        r2 = c.execute(g, (bv, "  comfort ", 1.6, 4, "GAS", None, "jl478qee")).fetchone()
        check(r2 == (r1[0], r1[1], False), "repetir (mayúsculas, espacios) no duplica submodelo, motor ni configuración")
        r3 = c.execute(g, (802010, "Base", 2.4, 4, "GAS", None, None)).fetchone()
        check(r3[2], f"configuración sobre un vehículo de AutoCare (sin tocar AutoCare) {r3}")
        rechaza(c, "configuración sin submodelo", g, (bv, " ", 1.6, 4, "GAS", None, None), "submodelo es obligatorio")
        rechaza(c, "configuración sin motor", g, (bv, "Base", None, None, "GAS", None, None), "motor necesita")
        rechaza(c, "configuración de un vehículo inexistente", g, (123, "Base", 1.6, 4, "GAS", None, None), "no existe")
        rechaza(c, "DELETE de una configuración", "delete from vcdb.configuracion", None, "no se borra")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="postgres")
    a = p.parse_args()
    probar_consolidacion(preparar(a.host, "consolidacion", "ref_minimo_consolidacion.sql"))
    probar_mercado(preparar(a.host, "mercado_externo", "ref_minimo_mercado.sql"))
    fallos = [n for ok, n in resultados if not ok]
    print(f"\n{len(resultados) - len(fallos)}/{len(resultados)} pruebas OK")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
