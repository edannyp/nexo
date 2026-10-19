"""Comprueba la conexión a ClickHouse y lista sus bases."""

import clickhouse_connect

from common.config import clickhouse


def main() -> None:
    params = clickhouse()
    if params is None:
        print("[--] ClickHouse: sin configurar")
        return
    try:
        client = clickhouse_connect.get_client(**params)
        version = client.command("select version()")
        bases = [r[0] for r in client.query("show databases").result_rows]
        print(f"[ok] ClickHouse {version}: {', '.join(bases)}")
    except Exception as exc:  # noqa: BLE001
        print(f"[x ] ClickHouse: {exc}")


if __name__ == "__main__":
    main()
