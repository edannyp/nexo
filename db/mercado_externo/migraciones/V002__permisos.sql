-- Permisos por proceso (ADR 0017). Roles de grupo sin login; ver nota en db/README.md.
-- Nadie inserta directo: la APP y la IA solo ejecutan las funciones de registro (security definer).

do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'grp_mercado_registro') then create role grp_mercado_registro nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'grp_app_lectura') then create role grp_app_lectura nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'grp_exploracion') then create role grp_exploracion nologin; end if;
end $$;

revoke all on function vcdb.fn_registrar_vehiculo, vcdb.fn_registrar_equipo from public;

-- IA con búsqueda web y APP: leen y registran por función.
grant usage on schema ref, vcdb to grp_mercado_registro;
grant select on all tables in schema ref, vcdb to grp_mercado_registro;
grant execute on function vcdb.fn_registrar_vehiculo, vcdb.fn_registrar_equipo to grp_mercado_registro;

-- Lectura.
grant usage on schema ref, vcdb to grp_app_lectura, grp_exploracion;
grant select on all tables in schema ref, vcdb to grp_app_lectura, grp_exploracion;
