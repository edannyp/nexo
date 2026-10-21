#!/usr/bin/env bash
# Crea (o recrea) la base `nexo` LOCAL con las mismas migraciones que producción y el usuario etl_entrada (clave "etl").
# Nunca apunta a un servidor: al contenedor `postgres` del devcontainer o, con NEXO_LOCAL_HOST, a un PostgreSQL 18 local
# levantado aparte (por ejemplo `docker run -d --name nexo-pg -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:18`).
set -euo pipefail
cd "$(dirname "$0")"
HOST="${NEXO_LOCAL_HOST:-postgres}"
case "$HOST" in
  postgres|localhost|127.0.0.1|host.docker.internal) ;;
  *) echo "NEXO_LOCAL_HOST=$HOST no es local: la base de pruebas nunca va en un servidor" >&2; exit 1 ;;
esac
ADMIN="host=$HOST user=postgres password=postgres"
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
