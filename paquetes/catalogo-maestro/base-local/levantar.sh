#!/usr/bin/env bash
# Crea (o recrea) Consolidación y MercadoExterno LOCALES con las migraciones reales y la referencia de AutoCare, y carga el ejemplo.
# Nunca apunta a un servidor: siempre al contenedor `postgres`.
set -euo pipefail
cd "$(dirname "$0")/.."
ADMIN="host=postgres user=postgres password=postgres"
for base in articulos_consolidacion mercado_externo; do
  psql "$ADMIN dbname=postgres" -q -c "drop database if exists $base with (force)" -c "create database $base"
done
uv run db/aplicar.py consolidacion --dsn "$ADMIN dbname=articulos_consolidacion"
uv run db/aplicar.py mercado_externo --dsn "$ADMIN dbname=mercado_externo"
if [ -n "${AUTOCARE_HOST:-}" ]; then
  echo "Referencia real desde AutoCare"
  uv run db/ref/cargar_ref.py consolidacion --destino "$ADMIN dbname=articulos_consolidacion"
  uv run db/ref/cargar_ref.py mercado_externo --destino "$ADMIN dbname=mercado_externo"
else
  echo "Sin AUTOCARE_*: referencia mínima de pruebas (IDs sintéticos)"
  psql "$ADMIN dbname=articulos_consolidacion" -q -v ON_ERROR_STOP=1 -f db/pruebas/ref_minimo_consolidacion.sql
  psql "$ADMIN dbname=mercado_externo" -q -v ON_ERROR_STOP=1 -f db/pruebas/ref_minimo_mercado.sql
fi
psql "$ADMIN dbname=articulos_consolidacion" -q -v ON_ERROR_STOP=1 -f db/consolidacion/ejemplos/ejemplo_carga.sql
psql "$ADMIN dbname=articulos_consolidacion" -c "select parte_id, descripcion, panal_alto_mm, panal_largo_mm, panal_ancho_mm, numeros from catalogo.v_parte_busqueda"
