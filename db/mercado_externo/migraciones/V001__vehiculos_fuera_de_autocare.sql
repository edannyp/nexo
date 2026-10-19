-- MercadoExterno (mercado_externo) — vehículos, marcas y equipos del mercado que NO están en AutoCare (ADR 0014).
-- Espejo de VCdb: mismos nombres de columna; IDs propios >= 1 000 000 000.
-- Contrato: db/mercado_externo/README.md · Diseño: architecture/datos/modelo-mercado-externo.md.
-- Escritores: la APP y la IA con búsqueda web, SOLO vía vcdb.fn_registrar_vehiculo / vcdb.fn_registrar_equipo.

create schema if not exists ref;   -- copia de referencia de AutoCare (la llena db/ref/cargar_ref.py)
create schema if not exists vcdb;  -- extensión propia

create function ref.normalizar_nombre(txt text) returns text
  language sql immutable as $$ select nullif(regexp_replace(upper(coalesce(txt, '')), '[^A-Z0-9]', '', 'g'), '') $$;

create function ref.es_id_mercado_externo(id integer) returns boolean
  language sql immutable as $$ select id >= 1000000000 $$;

------------------------------------------------------------------------------------------
-- ref: copia de AutoCare (VCdb)
------------------------------------------------------------------------------------------
create table ref.version (
  base        text primary key,
  version     text not null,
  publicacion date,
  cargado_en  timestamptz not null default now()
);
create table ref.make (
  make_id        integer primary key,
  make_name      text not null,
  make_name_norm text generated always as (ref.normalizar_nombre(make_name)) stored
);
create index on ref.make (make_name_norm);
create table ref.model (
  model_id        integer primary key,
  model_name      text not null,
  model_name_norm text generated always as (ref.normalizar_nombre(model_name)) stored
);
create index on ref.model (model_name_norm);
create table ref.base_vehicle (
  base_vehicle_id integer primary key,
  year_id         integer not null,
  make_id         integer not null,
  model_id        integer not null,
  unique (year_id, make_id, model_id)
);
create index on ref.base_vehicle (make_id, model_id);
create table ref.sub_model (
  sub_model_id        integer primary key,
  sub_model_name      text not null,
  sub_model_name_norm text generated always as (ref.normalizar_nombre(sub_model_name)) stored
);
create table ref.region (region_id integer primary key, region_abbr text not null unique, region_name text not null);
create table ref.mfr (
  mfr_id        integer primary key,
  mfr_name      text not null,
  mfr_name_norm text generated always as (ref.normalizar_nombre(mfr_name)) stored
);
create index on ref.mfr (mfr_name_norm);
create table ref.equipment_model (
  equipment_model_id        integer primary key,
  equipment_model_name      text not null,
  equipment_model_name_norm text generated always as (ref.normalizar_nombre(equipment_model_name)) stored
);
create table ref.equipment_base (
  equipment_base_id  integer primary key,
  mfr_id             integer not null,
  equipment_model_id integer not null
);
create index on ref.equipment_base (mfr_id, equipment_model_id);
create table ref.vehicle_type (vehicle_type_id integer primary key, vehicle_type_name text not null);

------------------------------------------------------------------------------------------
-- Tipos y columnas comunes
------------------------------------------------------------------------------------------
create type vcdb.origen as enum ('IA_WEB', 'APP');
create type vcdb.estado as enum ('ACTIVO', 'REEMPLAZADO', 'DESCARTADO');
create type vcdb.tipo_transmision as enum ('AUTOMATICA', 'MANUAL', 'CVT', 'AUTOMATIZADA');

-- Cada tabla propia lleva: origen, creado_por, creado_en, evidencia (lista de URLs/fichas), confianza, estado, reemplazado_por_id.
-- reemplazado_por_id apunta al ID oficial de AutoCare cuando una versión nueva de VCdb incluye el registro.

create sequence vcdb.id_seq start with 1000000000 minvalue 1000000000;

create table vcdb.make (
  make_id            integer primary key default nextval('vcdb.id_seq'),
  make_name          text not null,
  make_name_norm     text not null unique generated always as (ref.normalizar_nombre(make_name)) stored,
  origen             vcdb.origen not null,
  creado_por         text not null,
  creado_en          timestamptz not null default now(),
  evidencia          jsonb not null default '[]' check (jsonb_typeof(evidencia) = 'array'),
  confianza          numeric(4,3) not null check (confianza between 0 and 1),
  estado             vcdb.estado not null default 'ACTIVO',
  reemplazado_por_id integer,
  check ((estado = 'REEMPLAZADO') = (reemplazado_por_id is not null))
);

create table vcdb.model (
  model_id           integer primary key default nextval('vcdb.id_seq'),
  model_name         text not null,
  model_name_norm    text not null generated always as (ref.normalizar_nombre(model_name)) stored,
  make_id            integer not null,           -- de AutoCare (< 1e9) o propio
  vehicle_type_id    integer references ref.vehicle_type,
  origen             vcdb.origen not null,
  creado_por         text not null,
  creado_en          timestamptz not null default now(),
  evidencia          jsonb not null default '[]' check (jsonb_typeof(evidencia) = 'array'),
  confianza          numeric(4,3) not null check (confianza between 0 and 1),
  estado             vcdb.estado not null default 'ACTIVO',
  reemplazado_por_id integer,
  unique (make_id, model_name_norm),
  check ((estado = 'REEMPLAZADO') = (reemplazado_por_id is not null))
);

create table vcdb.base_vehicle (
  base_vehicle_id    integer primary key default nextval('vcdb.id_seq'),
  year_id            integer not null check (year_id between 1900 and 2100),
  make_id            integer not null,
  model_id           integer not null,
  origen             vcdb.origen not null,
  creado_por         text not null,
  creado_en          timestamptz not null default now(),
  evidencia          jsonb not null default '[]' check (jsonb_typeof(evidencia) = 'array'),
  confianza          numeric(4,3) not null check (confianza between 0 and 1),
  estado             vcdb.estado not null default 'ACTIVO',
  reemplazado_por_id integer,
  unique (year_id, make_id, model_id),
  check ((estado = 'REEMPLAZADO') = (reemplazado_por_id is not null))
);

create table vcdb.sub_model (
  sub_model_id        integer primary key default nextval('vcdb.id_seq'),
  sub_model_name      text not null,
  sub_model_name_norm text not null unique generated always as (ref.normalizar_nombre(sub_model_name)) stored,
  origen              vcdb.origen not null,
  creado_por          text not null,
  creado_en           timestamptz not null default now()
);

-- Localización: en qué regiones se vende un base vehicle (de AutoCare o propio) y con qué nombre comercial.
create table vcdb.base_vehicle_region (
  base_vehicle_id integer not null,
  region_id       integer not null references ref.region,
  nombre_mercado  text,
  origen          vcdb.origen not null,
  creado_por      text not null,
  creado_en       timestamptz not null default now(),
  evidencia       jsonb not null default '[]' check (jsonb_typeof(evidencia) = 'array'),
  primary key (base_vehicle_id, region_id)
);

create table vcdb.engine_config (
  engine_config_id   integer primary key default nextval('vcdb.id_seq'),
  liter              numeric(4,1),
  cc                 integer,
  cylinders          smallint,
  fuel_type          text,
  aspiration         text,
  engine_designation text,
  origen             vcdb.origen not null,
  creado_por         text not null,
  creado_en          timestamptz not null default now(),
  evidencia          jsonb not null default '[]' check (jsonb_typeof(evidencia) = 'array'),
  check (num_nonnulls(liter, cc, engine_designation) > 0)
);
create unique index engine_config_unico on vcdb.engine_config
  (coalesce(liter, 0), coalesce(cc, 0), coalesce(cylinders, 0), coalesce(upper(fuel_type), ''),
   coalesce(upper(aspiration), ''), coalesce(ref.normalizar_nombre(engine_designation), ''));

create table vcdb.base_vehicle_engine (
  base_vehicle_id  integer not null,
  engine_config_id integer not null references vcdb.engine_config,
  primary key (base_vehicle_id, engine_config_id)
);

create table vcdb.transmission (
  transmission_id integer primary key default nextval('vcdb.id_seq'),
  tipo            vcdb.tipo_transmision not null,
  velocidades     smallint check (velocidades between 1 and 12),
  unique (tipo, velocidades)
);

create table vcdb.base_vehicle_transmission (
  base_vehicle_id integer not null,
  transmission_id integer not null references vcdb.transmission,
  primary key (base_vehicle_id, transmission_id)
);

create table vcdb.mfr (
  mfr_id        integer primary key default nextval('vcdb.id_seq'),
  mfr_name      text not null,
  mfr_name_norm text not null unique generated always as (ref.normalizar_nombre(mfr_name)) stored,
  origen        vcdb.origen not null,
  creado_por    text not null,
  creado_en     timestamptz not null default now(),
  evidencia     jsonb not null default '[]' check (jsonb_typeof(evidencia) = 'array')
);

create table vcdb.equipment_model (
  equipment_model_id        integer primary key default nextval('vcdb.id_seq'),
  equipment_model_name      text not null,
  equipment_model_name_norm text not null unique generated always as (ref.normalizar_nombre(equipment_model_name)) stored,
  origen                    vcdb.origen not null,
  creado_por                text not null,
  creado_en                 timestamptz not null default now()
);

create table vcdb.equipment_base (
  equipment_base_id  integer primary key default nextval('vcdb.id_seq'),
  mfr_id             integer not null,
  equipment_model_id integer not null,
  vehicle_type_id    integer references ref.vehicle_type,
  origen             vcdb.origen not null,
  creado_por         text not null,
  creado_en          timestamptz not null default now(),
  evidencia          jsonb not null default '[]' check (jsonb_typeof(evidencia) = 'array'),
  confianza          numeric(4,3) not null check (confianza between 0 and 1),
  estado             vcdb.estado not null default 'ACTIVO',
  reemplazado_por_id integer,
  unique (mfr_id, equipment_model_id),
  check ((estado = 'REEMPLAZADO') = (reemplazado_por_id is not null))
);

------------------------------------------------------------------------------------------
-- Reglas: nada que ya exista en AutoCare; referencias válidas; nunca DELETE
------------------------------------------------------------------------------------------
create function vcdb.existe_make(id integer) returns boolean language sql stable as $$
  select exists (select 1 from ref.make where make_id = id) or exists (select 1 from vcdb.make where make_id = id) $$;
create function vcdb.existe_model(id integer) returns boolean language sql stable as $$
  select exists (select 1 from ref.model where model_id = id) or exists (select 1 from vcdb.model where model_id = id) $$;
create function vcdb.existe_base_vehicle(id integer) returns boolean language sql stable as $$
  select exists (select 1 from ref.base_vehicle where base_vehicle_id = id) or exists (select 1 from vcdb.base_vehicle where base_vehicle_id = id) $$;
create function vcdb.existe_mfr(id integer) returns boolean language sql stable as $$
  select exists (select 1 from ref.mfr where mfr_id = id) or exists (select 1 from vcdb.mfr where mfr_id = id) $$;
create function vcdb.existe_equipment_model(id integer) returns boolean language sql stable as $$
  select exists (select 1 from ref.equipment_model where equipment_model_id = id) or exists (select 1 from vcdb.equipment_model where equipment_model_id = id) $$;

create function vcdb.validar() returns trigger language plpgsql as $$
begin
  case tg_table_name
  when 'make' then
    if exists (select 1 from ref.make where make_name_norm = ref.normalizar_nombre(new.make_name)) then  -- columnas generadas aún no calculadas en BEFORE
      raise exception 'CONTRATO: la marca "%" ya existe en AutoCare', new.make_name using errcode = 'P0001';
    end if;
  when 'model' then
    if not vcdb.existe_make(new.make_id) then
      raise exception 'CONTRATO: make_id % no existe', new.make_id using errcode = 'P0001';
    end if;
    if exists (select 1 from ref.base_vehicle bv join ref.model m using (model_id)
               where bv.make_id = new.make_id and m.model_name_norm = ref.normalizar_nombre(new.model_name)) then
      raise exception 'CONTRATO: el modelo "%" ya existe en AutoCare para make_id %', new.model_name, new.make_id using errcode = 'P0001';
    end if;
  when 'base_vehicle' then
    if not vcdb.existe_make(new.make_id) or not vcdb.existe_model(new.model_id) then
      raise exception 'CONTRATO: make_id % o model_id % no existe', new.make_id, new.model_id using errcode = 'P0001';
    end if;
    if exists (select 1 from ref.base_vehicle where year_id = new.year_id and make_id = new.make_id and model_id = new.model_id) then
      raise exception 'CONTRATO: el base vehicle % % % ya existe en AutoCare', new.year_id, new.make_id, new.model_id using errcode = 'P0001';
    end if;
  when 'base_vehicle_region', 'base_vehicle_engine', 'base_vehicle_transmission' then
    if not vcdb.existe_base_vehicle(new.base_vehicle_id) then
      raise exception 'CONTRATO: base_vehicle_id % no existe', new.base_vehicle_id using errcode = 'P0001';
    end if;
  when 'mfr' then
    if exists (select 1 from ref.mfr where mfr_name_norm = ref.normalizar_nombre(new.mfr_name)) then
      raise exception 'CONTRATO: el fabricante "%" ya existe en AutoCare', new.mfr_name using errcode = 'P0001';
    end if;
  when 'equipment_base' then
    if not vcdb.existe_mfr(new.mfr_id) or not vcdb.existe_equipment_model(new.equipment_model_id) then
      raise exception 'CONTRATO: mfr_id % o equipment_model_id % no existe', new.mfr_id, new.equipment_model_id using errcode = 'P0001';
    end if;
    if exists (select 1 from ref.equipment_base where mfr_id = new.mfr_id and equipment_model_id = new.equipment_model_id) then
      raise exception 'CONTRATO: el equipo ya existe en AutoCare' using errcode = 'P0001';
    end if;
  else null;
  end case;
  return new;
end $$;

create function vcdb.prohibir_delete() returns trigger language plpgsql as $$
begin
  raise exception 'CONTRATO: no se borra en vcdb.% (usar estado REEMPLAZADO/DESCARTADO)', tg_table_name using errcode = 'P0001';
end $$;

do $$
declare t text;
begin
  foreach t in array array['make','model','base_vehicle','base_vehicle_region','base_vehicle_engine','base_vehicle_transmission','mfr','equipment_base']
  loop
    execute format('create trigger validar before insert on vcdb.%I for each row execute function vcdb.validar()', t);
  end loop;
  foreach t in array array['make','model','base_vehicle','sub_model','base_vehicle_region','engine_config','base_vehicle_engine',
                           'transmission','base_vehicle_transmission','mfr','equipment_model','equipment_base']
  loop
    execute format('create trigger no_delete before delete on vcdb.%I for each row execute function vcdb.prohibir_delete()', t);
  end loop;
end $$;

------------------------------------------------------------------------------------------
-- Vista unificada (AutoCare + propio) para buscadores
------------------------------------------------------------------------------------------
create view vcdb.v_base_vehicle as
select bv.base_vehicle_id, bv.year_id, bv.make_id, mk.make_name, bv.model_id, md.model_name, 'AUTOCARE'::text as origen_catalogo
from ref.base_vehicle bv join ref.make mk using (make_id) join ref.model md using (model_id)
union all
select bv.base_vehicle_id, bv.year_id, bv.make_id, coalesce(rm.make_name, vm.make_name), bv.model_id, vmo.model_name, 'MERCADO_EXTERNO'
from vcdb.base_vehicle bv
join vcdb.model vmo using (model_id)
left join ref.make rm on rm.make_id = bv.make_id
left join vcdb.make vm on vm.make_id = bv.make_id
where bv.estado = 'ACTIVO';

------------------------------------------------------------------------------------------
-- Única puerta de entrada: verifica en AutoCare y aquí; inserta solo lo que falta.
------------------------------------------------------------------------------------------
create function vcdb.fn_registrar_vehiculo(
  p_marca          text,
  p_modelo         text,
  p_anio_desde     integer,
  p_anio_hasta     integer,
  p_origen         vcdb.origen,
  p_creado_por     text,
  p_evidencia      jsonb,
  p_confianza      numeric,
  p_regiones       text[] default null,   -- abreviaturas VCdb: {'GTM','SLV'}
  p_nombre_mercado text default null
) returns table (anio integer, base_vehicle_id integer, catalogo text, nuevo boolean)
language plpgsql security definer set search_path = vcdb, ref, pg_temp as $$
#variable_conflict use_column
declare
  v_marca_norm  text := ref.normalizar_nombre(p_marca);
  v_modelo_norm text := ref.normalizar_nombre(p_modelo);
  v_make  integer;
  v_model integer;
  v_bv    integer;
  v_anio  integer;
  v_region text;
begin
  if v_marca_norm is null or v_modelo_norm is null then
    raise exception 'CONTRATO: marca y modelo son obligatorios' using errcode = 'P0001';
  end if;
  if p_anio_desde is null or p_anio_hasta is null or p_anio_hasta < p_anio_desde or p_anio_hasta - p_anio_desde > 40 then
    raise exception 'CONTRATO: rango de años inválido (% - %)', p_anio_desde, p_anio_hasta using errcode = 'P0001';
  end if;
  if p_evidencia is null or jsonb_typeof(p_evidencia) <> 'array' or jsonb_array_length(p_evidencia) = 0 then
    raise exception 'CONTRATO: se requiere evidencia (lista JSON con al menos una URL o ficha)' using errcode = 'P0001';
  end if;

  -- Marca: AutoCare → propia → nueva
  select m.make_id into v_make from ref.make m where m.make_name_norm = v_marca_norm order by m.make_id limit 1;
  if v_make is null then
    select m.make_id into v_make from vcdb.make m where m.make_name_norm = v_marca_norm;
  end if;
  if v_make is null then
    insert into vcdb.make (make_name, origen, creado_por, evidencia, confianza)
    values (p_marca, p_origen, p_creado_por, p_evidencia, p_confianza)
    on conflict (make_name_norm) do nothing;
    select m.make_id into v_make from vcdb.make m where m.make_name_norm = v_marca_norm;
  end if;

  -- Modelo: AutoCare (para esa marca) → propio → nuevo
  select md.model_id into v_model
  from ref.model md join ref.base_vehicle bv using (model_id)
  where bv.make_id = v_make and md.model_name_norm = v_modelo_norm
  order by md.model_id limit 1;
  if v_model is null then
    select md.model_id into v_model from vcdb.model md where md.make_id = v_make and md.model_name_norm = v_modelo_norm;
  end if;
  if v_model is null then
    insert into vcdb.model (model_name, make_id, origen, creado_por, evidencia, confianza)
    values (p_modelo, v_make, p_origen, p_creado_por, p_evidencia, p_confianza)
    on conflict (make_id, model_name_norm) do nothing;
    select md.model_id into v_model from vcdb.model md where md.make_id = v_make and md.model_name_norm = v_modelo_norm;
  end if;

  -- Un base vehicle por año
  for v_anio in p_anio_desde .. p_anio_hasta loop
    anio := v_anio;
    select b.base_vehicle_id into v_bv from ref.base_vehicle b
    where b.year_id = v_anio and b.make_id = v_make and b.model_id = v_model;
    if v_bv is not null then
      base_vehicle_id := v_bv; catalogo := 'AUTOCARE'; nuevo := false;
    else
      select b.base_vehicle_id into v_bv from vcdb.base_vehicle b
      where b.year_id = v_anio and b.make_id = v_make and b.model_id = v_model;
      if v_bv is not null then
        base_vehicle_id := v_bv; catalogo := 'MERCADO_EXTERNO'; nuevo := false;
      else
        insert into vcdb.base_vehicle (year_id, make_id, model_id, origen, creado_por, evidencia, confianza)
        values (v_anio, v_make, v_model, p_origen, p_creado_por, p_evidencia, p_confianza)
        on conflict (year_id, make_id, model_id) do nothing
        returning vcdb.base_vehicle.base_vehicle_id into v_bv;
        nuevo := v_bv is not null;
        if v_bv is null then  -- otro proceso lo insertó al mismo tiempo
          select b.base_vehicle_id into v_bv from vcdb.base_vehicle b
          where b.year_id = v_anio and b.make_id = v_make and b.model_id = v_model;
        end if;
        base_vehicle_id := v_bv; catalogo := 'MERCADO_EXTERNO';
      end if;
    end if;

    if p_regiones is not null then
      foreach v_region in array p_regiones loop
        insert into vcdb.base_vehicle_region (base_vehicle_id, region_id, nombre_mercado, origen, creado_por, evidencia)
        select v_bv, r.region_id, p_nombre_mercado, p_origen, p_creado_por, p_evidencia
        from ref.region r where r.region_abbr = upper(v_region)
        on conflict do nothing;
        if not found and not exists (select 1 from ref.region r where r.region_abbr = upper(v_region)) then
          raise exception 'CONTRATO: región "%" no existe en VCdb', v_region using errcode = 'P0001';
        end if;
      end loop;
    end if;

    v_bv := null;
    return next;
  end loop;
end $$;

create function vcdb.fn_registrar_equipo(
  p_fabricante   text,
  p_modelo       text,
  p_origen       vcdb.origen,
  p_creado_por   text,
  p_evidencia    jsonb,
  p_confianza    numeric
) returns table (equipment_base_id integer, catalogo text, nuevo boolean)
language plpgsql security definer set search_path = vcdb, ref, pg_temp as $$
#variable_conflict use_column
declare
  v_mfr_norm   text := ref.normalizar_nombre(p_fabricante);
  v_model_norm text := ref.normalizar_nombre(p_modelo);
  v_mfr integer; v_em integer; v_eb integer;
begin
  if v_mfr_norm is null or v_model_norm is null then
    raise exception 'CONTRATO: fabricante y modelo son obligatorios' using errcode = 'P0001';
  end if;
  if p_evidencia is null or jsonb_typeof(p_evidencia) <> 'array' or jsonb_array_length(p_evidencia) = 0 then
    raise exception 'CONTRATO: se requiere evidencia' using errcode = 'P0001';
  end if;

  select m.mfr_id into v_mfr from ref.mfr m where m.mfr_name_norm = v_mfr_norm order by m.mfr_id limit 1;
  if v_mfr is null then
    insert into vcdb.mfr (mfr_name, origen, creado_por, evidencia) values (p_fabricante, p_origen, p_creado_por, p_evidencia)
    on conflict (mfr_name_norm) do nothing;
    select m.mfr_id into v_mfr from vcdb.mfr m where m.mfr_name_norm = v_mfr_norm;
  end if;

  select e.equipment_model_id into v_em from ref.equipment_model e where e.equipment_model_name_norm = v_model_norm order by 1 limit 1;
  if v_em is null then
    insert into vcdb.equipment_model (equipment_model_name, origen, creado_por) values (p_modelo, p_origen, p_creado_por)
    on conflict (equipment_model_name_norm) do nothing;
    select e.equipment_model_id into v_em from vcdb.equipment_model e where e.equipment_model_name_norm = v_model_norm;
  end if;

  select e.equipment_base_id into v_eb from ref.equipment_base e where e.mfr_id = v_mfr and e.equipment_model_id = v_em;
  if v_eb is not null then
    return query select v_eb, 'AUTOCARE'::text, false; return;
  end if;
  select e.equipment_base_id into v_eb from vcdb.equipment_base e where e.mfr_id = v_mfr and e.equipment_model_id = v_em;
  if v_eb is not null then
    return query select v_eb, 'MERCADO_EXTERNO'::text, false; return;
  end if;
  insert into vcdb.equipment_base (mfr_id, equipment_model_id, origen, creado_por, evidencia, confianza)
  values (v_mfr, v_em, p_origen, p_creado_por, p_evidencia, p_confianza)
  on conflict (mfr_id, equipment_model_id) do nothing
  returning vcdb.equipment_base.equipment_base_id into v_eb;
  if v_eb is null then
    select e.equipment_base_id into v_eb from vcdb.equipment_base e where e.mfr_id = v_mfr and e.equipment_model_id = v_em;
    return query select v_eb, 'MERCADO_EXTERNO'::text, false; return;
  end if;
  return query select v_eb, 'MERCADO_EXTERNO'::text, true;
end $$;

comment on schema vcdb is 'Extensión de VCdb: solo lo que no está en AutoCare (ADR 0014). IDs >= 1 000 000 000.';
comment on function vcdb.fn_registrar_vehiculo is 'Única puerta de entrada para vehículos. Devuelve el base_vehicle_id de AutoCare si ya existe, o el propio (existente o nuevo).';
