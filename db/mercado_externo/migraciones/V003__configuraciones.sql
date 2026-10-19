-- MercadoExterno V003 · Configuraciones: vehículo base + submodelo + motor
-- Es lo que AutoCare modela con vehicle (base + submodelo) y vehicle_to_engine_config. Nexo exige submodelo y motor para confirmar
-- una aplicación de vehículo (decisión UX 4), así que un vehículo fuera de AutoCare también debe poder registrarlos.
-- El vehículo base puede ser de AutoCare (< 1e9) o propio; el submodelo, de AutoCare si ya existe con ese nombre.

create table vcdb.configuracion (
  base_vehicle_id  integer not null,
  sub_model_id     integer not null,
  engine_config_id integer not null references vcdb.engine_config,
  origen           vcdb.origen not null,
  creado_por       text not null,
  creado_en        timestamptz not null default now(),
  evidencia        jsonb not null default '[]' check (jsonb_typeof(evidencia) = 'array'),
  primary key (base_vehicle_id, sub_model_id, engine_config_id)
);
comment on table vcdb.configuracion is 'Vehículo base + submodelo + motor fuera de AutoCare (equivale a vehicle + vehicle_to_engine_config).';

create trigger no_delete before delete on vcdb.configuracion for each row execute function vcdb.prohibir_delete();

-- Registra (o encuentra) una configuración. Idempotente: llamar dos veces con lo mismo no duplica.
create function vcdb.fn_registrar_configuracion(
  p_base_vehicle_id integer,
  p_submodelo       text,
  p_litros          numeric,
  p_cilindros       smallint,
  p_combustible     text,
  p_origen          vcdb.origen,
  p_creado_por      text,
  p_aspiracion      text default null,
  p_designacion     text default null,
  p_evidencia       jsonb default '[]'
) returns table (sub_model_id integer, engine_config_id integer, nueva boolean)
language plpgsql security definer set search_path = vcdb, ref, pg_temp as $$
#variable_conflict use_column
declare
  v_sub  integer;
  v_eng  integer;
  v_norm text := ref.normalizar_nombre(p_submodelo);
begin
  if not vcdb.existe_base_vehicle(p_base_vehicle_id) then
    raise exception 'CONTRATO: base_vehicle_id % no existe', p_base_vehicle_id using errcode = 'P0001';
  end if;
  if v_norm is null then
    raise exception 'CONTRATO: el submodelo es obligatorio (usar «Base» si no tiene otro nombre)' using errcode = 'P0001';
  end if;
  if p_litros is null and p_designacion is null then
    raise exception 'CONTRATO: el motor necesita al menos los litros o su designación' using errcode = 'P0001';
  end if;

  -- Submodelo: AutoCare → propio → nuevo
  select s.sub_model_id into v_sub from ref.sub_model s where s.sub_model_name_norm = v_norm order by s.sub_model_id limit 1;
  if v_sub is null then
    insert into vcdb.sub_model (sub_model_name, origen, creado_por) values (initcap(trim(p_submodelo)), p_origen, p_creado_por)
    on conflict (sub_model_name_norm) do nothing;
    select s.sub_model_id into v_sub from vcdb.sub_model s where s.sub_model_name_norm = v_norm;
  end if;

  -- Motor: propio con los mismos datos → nuevo
  insert into vcdb.engine_config (liter, cylinders, fuel_type, aspiration, engine_designation, origen, creado_por, evidencia)
  values (p_litros, p_cilindros, upper(nullif(trim(p_combustible), '')), nullif(trim(p_aspiracion), ''), nullif(trim(p_designacion), ''),
          p_origen, p_creado_por, coalesce(p_evidencia, '[]'))
  on conflict do nothing;
  select e.engine_config_id into v_eng from vcdb.engine_config e
  where coalesce(e.liter, 0) = coalesce(p_litros, 0) and coalesce(e.cylinders, 0) = coalesce(p_cilindros, 0)
    and coalesce(upper(e.fuel_type), '') = coalesce(upper(nullif(trim(p_combustible), '')), '')
    and coalesce(upper(e.aspiration), '') = coalesce(upper(nullif(trim(p_aspiracion), '')), '')
    and coalesce(ref.normalizar_nombre(e.engine_designation), '') = coalesce(ref.normalizar_nombre(nullif(trim(p_designacion), '')), '');

  insert into vcdb.configuracion (base_vehicle_id, sub_model_id, engine_config_id, origen, creado_por, evidencia)
  values (p_base_vehicle_id, v_sub, v_eng, p_origen, p_creado_por, coalesce(p_evidencia, '[]'))
  on conflict do nothing;
  sub_model_id := v_sub; engine_config_id := v_eng; nueva := found;
  return next;
end $$;

revoke all on function vcdb.fn_registrar_configuracion from public;
grant execute on function vcdb.fn_registrar_configuracion to grp_mercado_registro;
grant select on vcdb.configuracion to grp_mercado_registro, grp_app_lectura, grp_exploracion;
