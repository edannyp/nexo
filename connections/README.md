# connections/ — Clientes y pruebas de conexión

Scripts para comprobar acceso a cada sistema y **explorar sus datos antes de diseñar el DDL**.
Es un proyecto Python independiente (no es código de producción).

```bash
cd connections
uv sync                                  # instala drivers (psycopg, hdbcli, clickhouse-connect)
uv run python -m postgres.smoke_test     # Nexo, AutoCare, MercadoExterno, Consolidación
uv run python -m sap.hana.smoke_test     # SAP HANA (requiere red/VPN)
uv run python -m clickhouse.smoke_test   # ClickHouse
uv run python -m exploration.perfilar --conexion autocare --tabla public.vehicle
PYTHONPATH=. uv run python -m exploration.lote_sap_local   # lote real SAP → nexo_real local (verificación)
```

Las credenciales salen de `../.env` (copiar desde `.env.example`). Nunca se escriben en estos archivos.

### Si el contenedor no llega a `10.x` (pero el host sí)
La VPN es IPsec (tabla de rutas 220, IP virtual `192.168.250.x`) y solo cifra lo que sale con esa IP; Docker
enmascara el tráfico del contenedor con la IP del Wi‑Fi y se pierde. En el **host** (dura hasta reiniciar):

```bash
ip -4 addr | grep 192.168.250          # IP virtual actual de la VPN
sudo iptables -t nat -I POSTROUTING -s 172.16.0.0/12 -d 10.0.0.0/8 -j SNAT --to-source <IP virtual>
```

| Carpeta | Contenido |
|---|---|
| `common/` | Lectura de configuración desde `.env` |
| `postgres/` | Smoke test de todas las bases Postgres + consultas de exploración |
| `sap/hana/` | Smoke test y consultas de exploración de OITM y tablas relacionadas |
| `clickhouse/` | Smoke test |
| `exploration/` | Perfilador genérico de tablas: conteos, nulos, distintos, ejemplos. Escribe en `data/perfiles/` |

Service Layer de SAP (escritura) no está aquí: lo usa el proyecto de ETL.
