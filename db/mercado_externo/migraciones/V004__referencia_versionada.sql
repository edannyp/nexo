-- MercadoExterno V004 · Copia de AutoCare versionada (ADR 0024 de Nexo, 2026-10-21)
-- db/ref/cargar_ref.py compara cada carga con la anterior: marca como obsoleto lo que AutoCare quitó (nunca lo borra) y guarda el
-- historial. Las funciones de registro siguen viendo lo obsoleto como "existe en AutoCare" para no duplicarlo.

do $$
declare t text;
begin
  foreach t in array array['make', 'model', 'sub_model', 'region', 'base_vehicle', 'vehicle_type', 'mfr', 'equipment_model',
                           'equipment_base'] loop
    execute format('alter table ref.%I add column obsoleto_en timestamptz', t);
  end loop;
end $$;

create table ref.historial_carga (
  id          bigint generated always as identity primary key,
  cargado_en  timestamptz not null default now(),
  versiones   jsonb not null,
  tabla       text not null,
  altas       integer not null,
  cambios     integer not null,
  bajas       integer not null,
  reactivados integer not null,
  detalle     jsonb not null default '{}',
  impacto     jsonb not null default '{}'      -- lo obsoleto que ya usan los registros de MercadoExterno
);
comment on table ref.historial_carga is 'Cada carga de AutoCare: qué cambió respecto a la anterior y su impacto en MercadoExterno.';
grant select on ref.historial_carga to grp_mercado_registro, grp_app_lectura, grp_exploracion;
