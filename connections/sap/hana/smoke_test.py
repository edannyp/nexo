"""Comprueba la conexión de lectura a SAP HANA y cuenta artículos en OITM."""

from hdbcli import dbapi

from common.config import hana, hana_schema


def main() -> None:
    params = hana()
    if params is None:
        print("[--] SAP HANA: sin configurar (SAP_HANA_HOST vacío)")
        return
    schema = hana_schema()
    try:
        conn = dbapi.connect(**params)
        cur = conn.cursor()
        cur.execute("select version from sys.m_database")
        print(f"[ok] SAP HANA {cur.fetchone()[0]}")
        if schema:
            cur.execute(f'select count(*) from "{schema}"."OITM"')
            print(f"[ok] {schema}.OITM: {cur.fetchone()[0]} artículos")
        conn.close()
    except Exception as exc:  # noqa: BLE001
        print(f"[x ] SAP HANA: {exc}")


if __name__ == "__main__":
    main()
