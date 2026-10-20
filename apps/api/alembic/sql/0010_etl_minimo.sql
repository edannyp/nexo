-- Nexo 0010 · El ETL de entrada con permisos mínimos (ADR 0006 y 0017)
-- El ETL solo escribe en staging y llama a app.fn_procesar_staging, que es quien crea y actualiza app.articulo. Para que el ETL no
-- necesite permisos sobre app, la función corre con los permisos de su dueño (SECURITY DEFINER) y nadie más puede ejecutarla salvo
-- quien reciba el permiso explícito. El usuario del ETL lo crea un administrador: deploy/sql/usuario-etl.sql.

alter function app.fn_procesar_staging(bigint)
  security definer
  set search_path = app, staging, meta, audit, public, pg_temp;

revoke execute on function app.fn_procesar_staging(bigint) from public;

comment on function app.fn_procesar_staging(bigint) is
  'Contrato del ETL de entrada (architecture/datos/contratos.md): procesa un lote de staging. SECURITY DEFINER; ejecutar solo con el usuario del ETL.';
