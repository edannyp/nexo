#!/usr/bin/env bash
# Crea (o recrea) la base `nexo` LOCAL con las mismas migraciones que producción y el usuario etl_entrada (clave "etl").
# Nunca apunta a un servidor: siempre al contenedor `postgres`.
set -euo pipefail
cd "$(dirname "$0")"
ADMIN="host=postgres user=postgres password=postgres"
psql "$ADMIN dbname=postgres" -q -v ON_ERROR_STOP=1 <<'SQL'
drop database if exists nexo with (force);
create database nexo;
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'nexo_app') then create role nexo_app nologin; end if;
  if exists (select 1 from pg_roles where rolname = 'etl_entrada') then
    execute 'drop owned by etl_entrada'; drop role etl_entrada;
  end if;
end $$;
SQL
for f in sql/0*.sql; do
  echo "migración ${f#sql/}"
  psql "$ADMIN dbname=nexo" -q -v ON_ERROR_STOP=1 -f "$f"
done
psql "$ADMIN dbname=nexo" -q -v ON_ERROR_STOP=1 -v clave='etl' -f sql/usuario-etl.sql
echo "Base local lista: nexo con etl_entrada / etl"
