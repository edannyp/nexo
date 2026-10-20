#!/usr/bin/env bash
# Crea (o recrea) las bases LOCALES `nexo` y `articulos_consolidacion` con sus migraciones reales:
# - Consolidación con tres partes de ejemplo (1, 2 y 3);
# - Nexo con el usuario agente_revision_catalogo (clave "agente") y tres artículos validados emparejados con esas partes.
# Nunca apunta a un servidor: siempre al contenedor `postgres`.
set -euo pipefail
cd "$(dirname "$0")"
ADMIN="host=postgres user=postgres password=postgres"
psql "$ADMIN dbname=postgres" -q -v ON_ERROR_STOP=1 <<'SQL'
drop database if exists nexo with (force);
drop database if exists articulos_consolidacion with (force);
create database nexo;
create database articulos_consolidacion;
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'nexo_app') then create role nexo_app nologin; end if;
  if exists (select 1 from pg_roles where rolname = 'agente_revision_catalogo') then drop role agente_revision_catalogo; end if;
end $$;
SQL
echo "== Consolidación"
(cd .. && uv run db/aplicar.py consolidacion --dsn "$ADMIN dbname=articulos_consolidacion")
psql "$ADMIN dbname=articulos_consolidacion" -q -v ON_ERROR_STOP=1 -f ../db/pruebas/ref_minimo_consolidacion.sql
psql "$ADMIN dbname=articulos_consolidacion" -q -v ON_ERROR_STOP=1 -f ../db/consolidacion/ejemplos/ejemplo_carga.sql
echo "== Nexo"
for f in sql/0*.sql; do
  echo "migración ${f#sql/}"
  psql "$ADMIN dbname=nexo" -q -v ON_ERROR_STOP=1 -f "$f"
done
psql "$ADMIN dbname=nexo" -q -v ON_ERROR_STOP=1 -v clave='agente' -f sql/usuario-agente-revision-catalogo.sql
psql "$ADMIN dbname=nexo" -q -v ON_ERROR_STOP=1 -f datos-ejemplo.sql
echo "Bases locales listas: nexo (agente_revision_catalogo / agente) y articulos_consolidacion"
