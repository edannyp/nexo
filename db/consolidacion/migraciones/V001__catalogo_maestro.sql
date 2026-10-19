-- Consolidación (articulos_consolidacion) — catálogo maestro de piezas del mercado.
-- Contrato: db/consolidacion/README.md · Diseño: architecture/datos/modelo-consolidacion.md · ADR 0009, 0011, 0014.
-- Este esquema GOBIERNA: el proceso de carga se adapta a él.

create extension if not exists pg_trgm;

create schema if not exists ref;       -- copia de referencia de AutoCare (la llena db/ref/cargar_ref.py)
create schema if not exists catalogo;  -- catálogo maestro
create schema if not exists carga;     -- control de corridas del proceso de carga

-- Límite entre IDs de AutoCare y de MercadoExterno (ADR 0014).
create function ref.es_id_mercado_externo(id integer) returns boolean
  language sql immutable as $$ select id >= 1000000000 $$;

-- Normalización de números de parte: mayúsculas, solo [A-Z0-9].
create function catalogo.normalizar_numero(txt text) returns text
  language sql immutable as $$ select nullif(regexp_replace(upper(coalesce(txt, '')), '[^A-Z0-9]', '', 'g'), '') $$;

------------------------------------------------------------------------------------------
-- ref: copia de AutoCare
------------------------------------------------------------------------------------------
create table ref.version (
  base             text primary key,          -- VCdb, PCdb, PAdb
  version          text not null,
  publicacion      date,
  cargado_en       timestamptz not null default now()
);

create table ref.part_terminology (
  part_terminology_id integer primary key,
  nombre              text not null
);

create table ref.atributo_permitido (           -- PAdb part_attribute_assignment
  part_terminology_id integer not null references ref.part_terminology,
  paid                integer not null,
  nombre              text not null,
  requiere_uom        boolean not null default false,  -- PAdb le asigna unidades (meta_uom_code_assignment)
  primary key (part_terminology_id, paid)
);

create table ref.valor_permitido (              -- PAdb valid_value_assignment
  part_terminology_id integer not null,
  paid                integer not null,
  valid_value_id      integer not null,
  valor               text not null,
  primary key (part_terminology_id, paid, valid_value_id),
  foreign key (part_terminology_id, paid) references ref.atributo_permitido
);

create table ref.uom (
  uom_code text primary key,
  nombre   text
);

create table ref.make       (make_id integer primary key, make_name text not null);
create table ref.model      (model_id integer primary key, model_name text not null);
create table ref.sub_model  (sub_model_id integer primary key, sub_model_name text not null);
create table ref.region     (region_id integer primary key, region_abbr text, region_name text);
create table ref.base_vehicle (
  base_vehicle_id integer primary key,
  year_id         integer not null,
  make_id         integer not null,
  model_id        integer not null
);
create index on ref.base_vehicle (make_id, model_id, year_id);
create table ref.engine_config  (engine_config_id integer primary key);
create table ref.transmission   (transmission_id integer primary key);
create table ref.equipment_base (equipment_base_id integer primary key);
create table ref.position       (position_id integer primary key, nombre text);

------------------------------------------------------------------------------------------
-- Tipos
------------------------------------------------------------------------------------------
create type catalogo.tipo_fuente        as enum ('CATALOGO_PROPIO', 'SCRAPING', 'LISTA_PROVEEDOR', 'MANUAL');
create type catalogo.tipo_marca         as enum ('OEM', 'AFTERMARKET');
create type catalogo.estado_parte       as enum ('ACTIVA', 'FUSIONADA', 'DESCARTADA');
create type catalogo.vinculo_metodo     as enum ('NUMERO', 'MEDIDAS_APLICACION', 'MANUAL');
create type catalogo.tipo_numero        as enum ('OEM', 'DPI', 'PROVEEDOR', 'INTERCAMBIO', 'REEMPLAZADO');
create type catalogo.motivo_sin_homologar as enum ('MARCA_DESCONOCIDA', 'MODELO_DESCONOCIDO', 'ANIOS_FALTANTES', 'AMBIGUO');
create type catalogo.tipo_imagen        as enum ('FOTO', 'DIAGRAMA', 'DIBUJO_TECNICO');
create type catalogo.tipo_conflicto     as enum ('NUMERO_DUPLICADO', 'ATRIBUTO_DISCREPA', 'APLICACION_DISCREPA', 'POSIBLE_FUSION');
create type catalogo.estado_conflicto   as enum ('ABIERTO', 'RESUELTO', 'DESCARTADO');
create type carga.estado_corrida        as enum ('EN_PROCESO', 'COMPLETA', 'FALLIDA');

------------------------------------------------------------------------------------------
-- Catálogos
------------------------------------------------------------------------------------------
create table catalogo.fuente (
  id         smallint generated always as identity primary key,
  codigo     text not null unique check (codigo ~ '^[A-Z0-9_]+$'),
  nombre     text not null,
  tipo       catalogo.tipo_fuente not null,
  url_base   text,
  prioridad  smallint not null default 5 check (prioridad between 1 and 9),
  activa     boolean not null default true
);

create table catalogo.marca_pieza (
  id           integer generated always as identity primary key,
  nombre       text not null,
  nombre_norm  text not null unique generated always as (catalogo.normalizar_numero(nombre)) stored,
  tipo         catalogo.tipo_marca not null,
  brand_aaiaid text unique
);

------------------------------------------------------------------------------------------
-- Corridas de carga
------------------------------------------------------------------------------------------
create table carga.corrida (
  id               bigint generated always as identity primary key,
  fuente_id        smallint not null references catalogo.fuente,
  iniciada_en      timestamptz not null default now(),
  terminada_en     timestamptz,
  estado           carga.estado_corrida not null default 'EN_PROCESO',
  version_proceso  text not null,
  leidos           integer not null default 0,
  insertados       integer not null default 0,
  actualizados     integer not null default 0,
  sin_cambios      integer not null default 0,
  errores          integer not null default 0,
  notas            text,
  check ((estado = 'EN_PROCESO') = (terminada_en is null))
);

------------------------------------------------------------------------------------------
-- Partes consolidadas y registros por fuente
------------------------------------------------------------------------------------------
create table catalogo.parte (
  id                  bigint generated always as identity primary key,
  part_terminology_id integer not null references ref.part_terminology,
  descripcion         text,
  estado              catalogo.estado_parte not null default 'ACTIVA',
  fusionada_en_id     bigint references catalogo.parte,
  creado_en           timestamptz not null default now(),
  actualizado_en      timestamptz not null default now(),
  check ((estado = 'FUSIONADA') = (fusionada_en_id is not null)),
  check (fusionada_en_id is distinct from id)
);
create index on catalogo.parte (part_terminology_id) where estado = 'ACTIVA';

create table catalogo.registro_fuente (
  id                   bigint generated always as identity primary key,
  fuente_id            smallint not null references catalogo.fuente,
  id_en_fuente         text not null,
  url                  text,
  descripcion_original text,
  datos_crudos         jsonb not null,
  hash_contenido       text not null,
  parte_id             bigint references catalogo.parte,
  vinculo_metodo       catalogo.vinculo_metodo,
  vinculo_confianza    numeric(4,3) check (vinculo_confianza between 0 and 1),
  vigente              boolean not null default true,
  corrida_id           bigint not null references carga.corrida,
  capturado_en         timestamptz not null default now(),
  actualizado_en       timestamptz not null default now(),
  unique (fuente_id, id_en_fuente),
  check ((parte_id is null) = (vinculo_metodo is null))
);
create index on catalogo.registro_fuente (parte_id);

------------------------------------------------------------------------------------------
-- Datos de la parte (cada fila sabe de qué registro_fuente salió)
------------------------------------------------------------------------------------------
create table catalogo.parte_numero (
  id                 bigint generated always as identity primary key,
  parte_id           bigint not null references catalogo.parte,
  registro_fuente_id bigint not null references catalogo.registro_fuente,
  tipo               catalogo.tipo_numero not null,
  marca_pieza_id     integer references catalogo.marca_pieza,
  numero             text not null,
  numero_norm        text not null generated always as (catalogo.normalizar_numero(numero)) stored,
  confianza          numeric(4,3) not null default 0.5 check (confianza between 0 and 1),
  check (numero_norm is not null),
  check (tipo = 'DPI' or marca_pieza_id is not null)
);
create unique index parte_numero_unico on catalogo.parte_numero
  (parte_id, tipo, coalesce(marca_pieza_id, 0), numero_norm, registro_fuente_id);
create index on catalogo.parte_numero (numero_norm);
create index on catalogo.parte_numero using gin (numero_norm gin_trgm_ops);

create table catalogo.parte_atributo (
  id                 bigint generated always as identity primary key,
  parte_id           bigint not null references catalogo.parte,
  registro_fuente_id bigint not null references catalogo.registro_fuente,
  paid               integer not null,
  valor_num          numeric,
  uom_code           text references ref.uom,
  valid_value_id     integer,
  valor_texto        text,
  valor_original     text,
  check (num_nonnulls(valor_num, valid_value_id, valor_texto) = 1),
  check (uom_code is null or valor_num is not null)
);
create index on catalogo.parte_atributo (parte_id, paid);
create index on catalogo.parte_atributo (paid, valor_num);

create table catalogo.parte_aplicacion (
  id                 bigint generated always as identity primary key,
  parte_id           bigint not null references catalogo.parte,
  registro_fuente_id bigint not null references catalogo.registro_fuente,
  base_vehicle_id    integer,
  equipment_base_id  integer,
  sub_model_id       integer,
  engine_config_id   integer,
  transmission_id    integer,
  posicion_id        integer references ref.position,
  cantidad           smallint check (cantidad > 0),
  notas              text,
  vcdb_version       text not null,
  confianza          numeric(4,3) not null default 0.5 check (confianza between 0 and 1),
  check (num_nonnulls(base_vehicle_id, equipment_base_id) = 1),
  check (equipment_base_id is null or (sub_model_id is null and engine_config_id is null and transmission_id is null))
);
create index on catalogo.parte_aplicacion (base_vehicle_id);
create index on catalogo.parte_aplicacion (equipment_base_id);
create index on catalogo.parte_aplicacion (parte_id);

create table catalogo.parte_aplicacion_region (
  parte_aplicacion_id bigint  not null references catalogo.parte_aplicacion,
  region_id           integer not null references ref.region,
  registro_fuente_id  bigint  not null references catalogo.registro_fuente,
  primary key (parte_aplicacion_id, region_id, registro_fuente_id)
);

create table catalogo.aplicacion_sin_homologar (
  id                 bigint generated always as identity primary key,
  parte_id           bigint not null references catalogo.parte,
  registro_fuente_id bigint not null references catalogo.registro_fuente,
  marca_texto        text,
  modelo_texto       text,
  anio_desde         smallint,
  anio_hasta         smallint,
  motor_texto        text,
  otros_texto        text,
  motivo             catalogo.motivo_sin_homologar not null,
  check (num_nonnulls(marca_texto, modelo_texto, motor_texto, otros_texto) > 0)
);

create table catalogo.parte_imagen (
  id                 bigint generated always as identity primary key,
  parte_id           bigint not null references catalogo.parte,
  registro_fuente_id bigint not null references catalogo.registro_fuente,
  tipo               catalogo.tipo_imagen not null,
  url                text,
  minio_bucket       text,
  minio_objeto       text,
  orden              smallint not null default 1,
  check (url is not null or (minio_bucket is not null and minio_objeto is not null))
);

create table catalogo.conflicto (
  id           bigint generated always as identity primary key,
  parte_id     bigint not null references catalogo.parte,
  tipo         catalogo.tipo_conflicto not null,
  detalle      jsonb not null,
  estado       catalogo.estado_conflicto not null default 'ABIERTO',
  detectado_en timestamptz not null default now(),
  resuelto_en  timestamptz,
  resolucion   text,
  check ((estado = 'ABIERTO') = (resuelto_en is null))
);

------------------------------------------------------------------------------------------
-- Reglas que hacen cumplir el contrato
------------------------------------------------------------------------------------------

-- 1. Nunca DELETE: se marca vigente = false o la parte se FUSIONA / DESCARTA.
create function catalogo.prohibir_delete() returns trigger language plpgsql as $$
begin
  raise exception 'CONTRATO: no se borra en %.% (usar vigente=false o estado FUSIONADA/DESCARTADA)', tg_table_schema, tg_table_name
    using errcode = 'P0001';
end $$;

do $$
declare t text;
begin
  foreach t in array array['fuente','marca_pieza','parte','registro_fuente','parte_numero','parte_atributo',
                           'parte_aplicacion','parte_aplicacion_region','aplicacion_sin_homologar','parte_imagen','conflicto']
  loop
    execute format('create trigger %I before delete on catalogo.%I for each row execute function catalogo.prohibir_delete()',
                   'no_delete_' || t, t);
  end loop;
end $$;

-- 2. actualizado_en automático.
create function catalogo.tocar_actualizado_en() returns trigger language plpgsql as $$
begin new.actualizado_en := now(); return new; end $$;
create trigger tocar before update on catalogo.parte for each row execute function catalogo.tocar_actualizado_en();
create trigger tocar before update on catalogo.registro_fuente for each row execute function catalogo.tocar_actualizado_en();

-- 3. Atributos: el paid debe estar asignado al tipo de parte; el valor de lista debe ser válido; numéricos con unidad.
create function catalogo.validar_atributo() returns trigger language plpgsql as $$
declare pt integer; req_uom boolean;
begin
  select part_terminology_id into pt from catalogo.parte where id = new.parte_id;
  select requiere_uom into req_uom from ref.atributo_permitido where part_terminology_id = pt and paid = new.paid;
  if not found then
    raise exception 'CONTRATO: el atributo PAdb % no aplica al tipo de parte %', new.paid, pt using errcode = 'P0001';
  end if;
  if new.valid_value_id is not null and not exists (
       select 1 from ref.valor_permitido where part_terminology_id = pt and paid = new.paid and valid_value_id = new.valid_value_id) then
    raise exception 'CONTRATO: valid_value_id % no es válido para atributo % del tipo %', new.valid_value_id, new.paid, pt using errcode = 'P0001';
  end if;
  if new.valor_num is not null and req_uom and new.uom_code is null then
    raise exception 'CONTRATO: el valor numérico del atributo % requiere uom_code', new.paid using errcode = 'P0001';
  end if;
  return new;
end $$;
create trigger validar before insert or update on catalogo.parte_atributo for each row execute function catalogo.validar_atributo();

-- 4. Aplicaciones: los IDs de AutoCare deben existir; los >= 1 000 000 000 son de MercadoExterno (los valida su propia base).
create function catalogo.validar_aplicacion() returns trigger language plpgsql as $$
begin
  if new.base_vehicle_id is not null and not ref.es_id_mercado_externo(new.base_vehicle_id)
     and not exists (select 1 from ref.base_vehicle where base_vehicle_id = new.base_vehicle_id) then
    raise exception 'CONTRATO: base_vehicle_id % no existe en AutoCare', new.base_vehicle_id using errcode = 'P0001';
  end if;
  if new.equipment_base_id is not null and not ref.es_id_mercado_externo(new.equipment_base_id)
     and not exists (select 1 from ref.equipment_base where equipment_base_id = new.equipment_base_id) then
    raise exception 'CONTRATO: equipment_base_id % no existe en AutoCare', new.equipment_base_id using errcode = 'P0001';
  end if;
  if new.sub_model_id is not null and not ref.es_id_mercado_externo(new.sub_model_id)
     and not exists (select 1 from ref.sub_model where sub_model_id = new.sub_model_id) then
    raise exception 'CONTRATO: sub_model_id % no existe en AutoCare', new.sub_model_id using errcode = 'P0001';
  end if;
  if new.engine_config_id is not null and not ref.es_id_mercado_externo(new.engine_config_id)
     and not exists (select 1 from ref.engine_config where engine_config_id = new.engine_config_id) then
    raise exception 'CONTRATO: engine_config_id % no existe en AutoCare', new.engine_config_id using errcode = 'P0001';
  end if;
  if new.transmission_id is not null and not ref.es_id_mercado_externo(new.transmission_id)
     and not exists (select 1 from ref.transmission where transmission_id = new.transmission_id) then
    raise exception 'CONTRATO: transmission_id % no existe en AutoCare', new.transmission_id using errcode = 'P0001';
  end if;
  return new;
end $$;
create trigger validar before insert or update on catalogo.parte_aplicacion for each row execute function catalogo.validar_aplicacion();

-- 5. Solo se escribe dentro de una corrida abierta.
create function carga.validar_corrida_abierta() returns trigger language plpgsql as $$
begin
  if not exists (select 1 from carga.corrida where id = new.corrida_id and estado = 'EN_PROCESO') then
    raise exception 'CONTRATO: la corrida % no está EN_PROCESO', new.corrida_id using errcode = 'P0001';
  end if;
  return new;
end $$;
create trigger validar_corrida before insert or update on catalogo.registro_fuente
  for each row execute function carga.validar_corrida_abierta();

------------------------------------------------------------------------------------------
-- Vista para el buscador de emparejamiento de la APP
------------------------------------------------------------------------------------------
create view catalogo.v_parte_busqueda as
select p.id as parte_id,
       p.part_terminology_id,
       pt.nombre as tipo_parte,
       p.descripcion,
       (select string_agg(distinct n.numero, ' ' order by n.numero) from catalogo.parte_numero n where n.parte_id = p.id) as numeros,
       (select max(a.valor_num) filter (where a.paid = 267) from catalogo.parte_atributo a where a.parte_id = p.id) as panal_alto_mm,
       (select max(a.valor_num) filter (where a.paid = 269) from catalogo.parte_atributo a where a.parte_id = p.id) as panal_largo_mm,
       (select max(a.valor_num) filter (where a.paid = 268) from catalogo.parte_atributo a where a.parte_id = p.id) as panal_ancho_mm,
       (select count(*) from catalogo.parte_aplicacion ap where ap.parte_id = p.id) as n_aplicaciones,
       (select count(distinct r.fuente_id) from catalogo.registro_fuente r where r.parte_id = p.id and r.vigente) as n_fuentes,
       (select i.url from catalogo.parte_imagen i where i.parte_id = p.id order by i.orden limit 1) as imagen_url
from catalogo.parte p
join ref.part_terminology pt using (part_terminology_id)
where p.estado = 'ACTIVA';

comment on schema catalogo is 'Catálogo maestro de piezas del mercado (ADR 0011). Esquema gobernado por el proyecto de Integración.';
comment on table catalogo.registro_fuente is 'Pieza tal como viene de su fuente. Upsert por (fuente_id, id_en_fuente). Nunca se borra.';
comment on table catalogo.parte is 'Pieza consolidada (golden record). ID estable: Nexo lo referencia.';
