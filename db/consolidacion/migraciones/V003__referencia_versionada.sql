-- Consolidación V003 · Copia de AutoCare versionada (ADR 0024 de Nexo, 2026-10-21)
-- db/ref/cargar_ref.py compara cada carga con la anterior: marca como obsoleto lo que AutoCare quitó (nunca lo borra: lo pueden
-- referenciar partes ya cargadas) y guarda el historial. Lo obsoleto no se asigna de nuevo; lo que ya estaba se conserva.

do $$
declare t text;
begin
  foreach t in array array['make', 'model', 'sub_model', 'region', 'base_vehicle', 'part_terminology', 'atributo_permitido',
                           'valor_permitido', 'uom', 'engine_config', 'transmission', 'equipment_base', 'position'] loop
    execute format('alter table ref.%I add column obsoleto_en timestamptz', t);
  end loop;
end $$;

create table ref.historial_carga (
  id          bigint generated always as identity primary key,
  cargado_en  timestamptz not null default now(),
  versiones   jsonb not null,                  -- VCdb / PCdb / PAdb de AutoCare en esa carga
  tabla       text not null,
  altas       integer not null,
  cambios     integer not null,
  bajas       integer not null,                -- marcadas como obsoletas
  reactivados integer not null,                -- obsoletas que AutoCare volvió a publicar
  detalle     jsonb not null default '{}',     -- ejemplos por tipo de cambio
  impacto     jsonb not null default '{}'      -- lo obsoleto que ya usan las partes del catálogo
);
comment on table ref.historial_carga is 'Cada carga de AutoCare: qué cambió respecto a la anterior y su impacto en el catálogo.';
grant select on ref.historial_carga to grp_consolidacion_carga, grp_app_lectura, grp_exploracion;

-- Una parte nueva no puede ser de un tipo que AutoCare ya no publica
create function catalogo.validar_tipo_parte() returns trigger language plpgsql as $$
begin
  if (tg_op = 'INSERT' or new.part_terminology_id is distinct from old.part_terminology_id)
     and exists (select 1 from ref.part_terminology where part_terminology_id = new.part_terminology_id and obsoleto_en is not null) then
    raise exception 'CONTRATO: el tipo de parte % ya no está en AutoCare (obsoleto)', new.part_terminology_id using errcode = 'P0001';
  end if;
  return new;
end $$;
create trigger validar_tipo before insert or update of part_terminology_id on catalogo.parte
  for each row execute function catalogo.validar_tipo_parte();

create or replace function catalogo.validar_atributo() returns trigger language plpgsql as $$
declare pt integer; req_uom boolean; obs timestamptz;
  nuevo boolean := tg_op = 'INSERT';
begin
  select part_terminology_id into pt from catalogo.parte where id = new.parte_id;
  select requiere_uom, obsoleto_en into req_uom, obs from ref.atributo_permitido where part_terminology_id = pt and paid = new.paid;
  if not found or (obs is not null and (nuevo or new.paid is distinct from old.paid)) then
    raise exception 'CONTRATO: el atributo PAdb % no aplica al tipo de parte %', new.paid, pt using errcode = 'P0001';
  end if;
  -- Lo que AutoCare quitó (obsoleto) no se asigna de nuevo; lo que ya estaba se conserva
  if new.valid_value_id is not null and (nuevo or new.valid_value_id is distinct from old.valid_value_id) and not exists (
       select 1 from ref.valor_permitido where part_terminology_id = pt and paid = new.paid and valid_value_id = new.valid_value_id
         and obsoleto_en is null) then
    raise exception 'CONTRATO: valid_value_id % no es válido para atributo % del tipo %', new.valid_value_id, new.paid, pt using errcode = 'P0001';
  end if;
  if new.valor_num is not null and req_uom and new.uom_code is null then
    raise exception 'CONTRATO: el valor numérico del atributo % requiere uom_code', new.paid using errcode = 'P0001';
  end if;
  return new;
end $$;

create or replace function catalogo.validar_aplicacion() returns trigger language plpgsql as $$
declare nuevo boolean := tg_op = 'INSERT';
begin
  if new.base_vehicle_id is not null and not ref.es_id_mercado_externo(new.base_vehicle_id)
     and (nuevo or new.base_vehicle_id is distinct from old.base_vehicle_id)
     and not exists (select 1 from ref.base_vehicle where base_vehicle_id = new.base_vehicle_id and obsoleto_en is null) then
    raise exception 'CONTRATO: base_vehicle_id % no existe en AutoCare', new.base_vehicle_id using errcode = 'P0001';
  end if;
  if new.equipment_base_id is not null and not ref.es_id_mercado_externo(new.equipment_base_id)
     and (nuevo or new.equipment_base_id is distinct from old.equipment_base_id)
     and not exists (select 1 from ref.equipment_base where equipment_base_id = new.equipment_base_id and obsoleto_en is null) then
    raise exception 'CONTRATO: equipment_base_id % no existe en AutoCare', new.equipment_base_id using errcode = 'P0001';
  end if;
  if new.sub_model_id is not null and not ref.es_id_mercado_externo(new.sub_model_id)
     and (nuevo or new.sub_model_id is distinct from old.sub_model_id)
     and not exists (select 1 from ref.sub_model where sub_model_id = new.sub_model_id and obsoleto_en is null) then
    raise exception 'CONTRATO: sub_model_id % no existe en AutoCare', new.sub_model_id using errcode = 'P0001';
  end if;
  if new.engine_config_id is not null and not ref.es_id_mercado_externo(new.engine_config_id)
     and (nuevo or new.engine_config_id is distinct from old.engine_config_id)
     and not exists (select 1 from ref.engine_config where engine_config_id = new.engine_config_id and obsoleto_en is null) then
    raise exception 'CONTRATO: engine_config_id % no existe en AutoCare', new.engine_config_id using errcode = 'P0001';
  end if;
  if new.transmission_id is not null and not ref.es_id_mercado_externo(new.transmission_id)
     and (nuevo or new.transmission_id is distinct from old.transmission_id)
     and not exists (select 1 from ref.transmission where transmission_id = new.transmission_id and obsoleto_en is null) then
    raise exception 'CONTRATO: transmission_id % no existe en AutoCare', new.transmission_id using errcode = 'P0001';
  end if;
  return new;
end $$;
