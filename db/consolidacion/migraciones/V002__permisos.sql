-- Permisos por proceso (ADR 0017). Roles de grupo sin login: el administrador del servidor crea los usuarios
-- con contraseña (fuera del repositorio) y los agrega al grupo, p. ej.:
--   create user scraping_consolidacion password '...' in role grp_consolidacion_carga;

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'grp_consolidacion_carga') then create role grp_consolidacion_carga nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'grp_app_lectura') then create role grp_app_lectura nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'grp_exploracion') then create role grp_exploracion nologin; end if;
end $$;

-- Proceso de carga (otro desarrollador): escribe en catalogo y carga; solo lee ref; sin DDL.
grant usage on schema ref, catalogo, carga to grp_consolidacion_carga;
grant select on all tables in schema ref to grp_consolidacion_carga;
grant select, insert, update on all tables in schema catalogo, carga to grp_consolidacion_carga;
grant usage on all sequences in schema catalogo, carga to grp_consolidacion_carga;
grant execute on all functions in schema catalogo to grp_consolidacion_carga;

-- APP y exploración: solo lectura.
grant usage on schema ref, catalogo, carga to grp_app_lectura, grp_exploracion;
grant select on all tables in schema ref, catalogo, carga to grp_app_lectura, grp_exploracion;
