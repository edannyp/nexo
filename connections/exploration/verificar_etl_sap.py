"""Verificación de una carga del ETL de SAP (proceso externo): compara la base a revisar con una base de REFERENCIA cargada desde la
misma SAP con exploration/lote_sap_local.py. Solo lectura en las dos.

Nexo calcula la huella (`hash_control`) de cada artículo con sus valores normalizados. Si el ETL mapea bien, las huellas coinciden
artículo por artículo; si no, aquí se ve qué campos difieren y en cuántos artículos. Conviene cargar la referencia justo después de la
corrida del ETL, para que SAP no haya cambiado entre las dos.

Uso (desde connections/):
    PYTHONPATH=. uv run python -m exploration.verificar_etl_sap --referencia "<dsn local>" --revisar "<dsn de la base a revisar>"
"""

import argparse
import sys
from collections import Counter

import psycopg

EJEMPLOS = 5


def leer(dsn: str):
    c = psycopg.connect(dsn)
    c.execute("set transaction read only")
    return c


def articulos(c, columnas: list[str]) -> dict[str, dict]:
    sql = f"select item_code, hash_control, activo, motivo_inactivo::text, linea::text, categoria_codigo, {', '.join(columnas)} from app.articulo"
    nombres = ["item_code", "hash_control", "activo", "motivo_inactivo", "linea", "categoria_codigo", *columnas]
    return {f[0]: dict(zip(nombres, f, strict=True)) for f in c.execute(sql)}


def resumen(arts: dict[str, dict]) -> Counter:
    return Counter((a["categoria_codigo"], a["linea"], "activo" if a["activo"] else f"inactivo:{a['motivo_inactivo']}") for a in arts.values())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--referencia", required=True, help="DSN de la base cargada con lote_sap_local.py")
    p.add_argument("--revisar", required=True, help="DSN de la base cargada por el ETL")
    a = p.parse_args()

    with leer(a.referencia) as ref, leer(a.revisar) as rev:
        columnas = [r[0] for r in ref.execute(
            "select columna from meta.diccionario_campo where esquema = 'app' and tabla = 'articulo' and en_hash order by columna")]
        r_arts, v_arts = articulos(ref, columnas), articulos(rev, columnas)
        hallazgos = {n: dict(c.execute("select tipo::text, count(*) from app.hallazgo_calidad_sap where corregido_en is null group by 1"))
                     for n, c in (("referencia", ref), ("revisar", rev))}
        lotes = rev.execute("""select lote_id, iniciado_en, procesado_en, (to_jsonb(l) ->> 'completo')::boolean, resultado
                               from staging.lote l order by lote_id desc limit 5""").fetchall()

    problemas = 0
    print("== Artículos por categoría, línea y estado (referencia → revisar)")
    r_res, v_res = resumen(r_arts), resumen(v_arts)
    for clave in sorted(set(r_res) | set(v_res)):
        marca = "" if r_res[clave] == v_res[clave] else "  ⚠"
        print(f"  {' · '.join(str(x) for x in clave):45} {r_res[clave]:6} → {v_res[clave]:6}{marca}")

    solo_ref, solo_rev = sorted(set(r_arts) - set(v_arts)), sorted(set(v_arts) - set(r_arts))
    print(f"\n== Solo en la referencia (el ETL no los envió): {len(solo_ref)}  {solo_ref[:EJEMPLOS]}")
    print(f"== Solo en la base revisada (no están en SAP hoy): {len(solo_rev)}  {solo_rev[:EJEMPLOS]}")
    problemas += len(solo_ref)

    distintos = [ic for ic in set(r_arts) & set(v_arts) if r_arts[ic]["hash_control"] != v_arts[ic]["hash_control"]]
    por_campo: Counter = Counter()
    ejemplos: dict[str, list] = {}
    for ic in distintos:
        for col in columnas:
            if r_arts[ic][col] != v_arts[ic][col]:
                por_campo[col] += 1
                ejemplos.setdefault(col, [])
                if len(ejemplos[col]) < EJEMPLOS:
                    ejemplos[col].append(f"{ic}: {r_arts[ic][col]!r} → {v_arts[ic][col]!r}")
    print(f"\n== Huellas distintas: {len(distintos)} de {len(set(r_arts) & set(v_arts))} artículos en común")
    for col, n in por_campo.most_common():
        print(f"  {col}: {n} artículos")
        for e in ejemplos[col]:
            print(f"      {e}")
    problemas += len(distintos)

    print("\n== Hallazgos de calidad abiertos (referencia → revisar)")
    for tipo in sorted(set(hallazgos["referencia"]) | set(hallazgos["revisar"])):
        r, v = hallazgos["referencia"].get(tipo, 0), hallazgos["revisar"].get(tipo, 0)
        print(f"  {tipo:32} {r:6} → {v:6}{'' if r == v else '  ⚠'}")

    print("\n== Últimos lotes de la base revisada")
    for lote_id, inicio, fin, completo, res in lotes:
        estado = "procesado" if fin else "SIN PROCESAR"
        print(f"  {lote_id}: {inicio:%Y-%m-%d %H:%M} {estado}, {'completo' if completo else 'parcial'}  {res or ''}")

    print("\n" + ("VERIFICACIÓN OK: misma SAP, mismo resultado." if not problemas else
                  f"REVISAR: {problemas} diferencias. Si SAP cambió entre las dos cargas, recarga la referencia y repite."))
    sys.exit(0 if not problemas else 1)


if __name__ == "__main__":
    main()
