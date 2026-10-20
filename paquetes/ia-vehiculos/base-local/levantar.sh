#!/usr/bin/env bash
# Crea (o recrea) MercadoExterno LOCAL con las migraciones reales y la referencia de AutoCare.
# Nunca apunta a un servidor: siempre al contenedor `postgres`.
set -euo pipefail
cd "$(dirname "$0")/.."
ADMIN="host=postgres user=postgres password=postgres"
psql "$ADMIN dbname=postgres" -q -c "drop database if exists mercado_externo with (force)" -c "create database mercado_externo"
uv run db/aplicar.py mercado_externo --dsn "$ADMIN dbname=mercado_externo"
if [ -n "${AUTOCARE_HOST:-}" ]; then
  echo "Referencia real desde AutoCare"
  uv run db/ref/cargar_ref.py mercado_externo --destino "$ADMIN dbname=mercado_externo"
else
  echo "Sin AUTOCARE_*: referencia mínima de pruebas (IDs sintéticos)"
  psql "$ADMIN dbname=mercado_externo" -q -v ON_ERROR_STOP=1 -f db/pruebas/ref_minimo_mercado.sql
fi
psql "$ADMIN dbname=mercado_externo" -c "select count(*) as vehiculos_base_de_referencia from ref.base_vehicle"
