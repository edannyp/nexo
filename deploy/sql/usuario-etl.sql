-- Usuario del ETL de entrada (SAP → staging de Nexo), con permisos mínimos (ADR 0017).
-- Ejecutar UNA vez en la base nexo, como superusuario (o un rol con CREATEROLE), DESPUÉS de que la API haya migrado a 0010:
--   psql -h <servidor> -U postgres -d nexo -v clave='<contraseña larga>' -f deploy/sql/usuario-etl.sql
-- La contraseña se pasa al ejecutar: nunca se guarda en el repositorio.

create role etl_entrada login password :'clave';
grant connect on database nexo to etl_entrada;

-- Solo staging: leer e insertar (una fila por artículo y lote, migración 0013). No actualiza ni borra.
grant usage on schema staging to etl_entrada;
grant select, insert on all tables in schema staging to etl_entrada;
grant usage, select on all sequences in schema staging to etl_entrada;

-- Y procesar el lote. La función corre con los permisos de su dueño: el ETL no necesita nada en app.
grant usage on schema app to etl_entrada;
grant execute on function app.fn_procesar_staging(bigint), app.fn_articulos_conocidos() to etl_entrada;

-- Tablas de staging que agreguen migraciones futuras (las crea el dueño de la base, nexo_app)
alter default privileges for role nexo_app in schema staging grant select, insert on tables to etl_entrada;
alter default privileges for role nexo_app in schema staging grant usage, select on sequences to etl_entrada;
