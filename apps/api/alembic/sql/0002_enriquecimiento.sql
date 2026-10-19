-- Nexo 0002 — Enriquecimiento: emparejamiento con Consolidación, aplicaciones ACES, atributos PIES, equivalencias,
-- imágenes, cola de verificación, homologación SAP ↔ AutoCare y auditoría de cambios.
-- Decisiones: ADR 0005, 0010, 0011, 0012, 0013, 0014. Requisitos para POR_VALIDAR: context/workflow-estados.md regla 4.

------------------------------------------------------------------------------------------
-- Tipos
------------------------------------------------------------------------------------------
create type app.origen_dato        as enum ('SAP', 'CONSOLIDACION', 'MANUAL', 'HEREDADO_EQUIVALENTE');
create type app.origen_imagen      as enum ('PROPIA', 'PROVEEDOR', 'CONSOLIDACION');
create type app.origen_equivalencia as enum ('MANUAL', 'IA', 'SAP_COD_ANTERIOR');
create type app.estado_sugerencia  as enum ('SUGERIDA', 'CONFIRMADA', 'DESCARTADA');
create type app.origen_tarea       as enum ('NUEVA_FOTO', 'MUESTREO', 'CAMBIO_CATALOGO', 'MANUAL');
create type app.estado_tarea       as enum ('ABIERTA', 'CONFORME', 'CON_HALLAZGO');

-- Fabricado sin Importado equivalente: se permite con justificación (regla 4).
alter table app.articulo add column justificacion_sin_equivalente text;

------------------------------------------------------------------------------------------
-- Configuración: atributos obligatorios por tipo de parte y precarga desde SAP
------------------------------------------------------------------------------------------
create table meta.atributo_requerido (
  part_terminology_id integer not null,
  paid                integer not null,
  nombre              text not null,
  primary key (part_terminology_id, paid)
);
insert into meta.atributo_requerido values
  (2172, 267, 'Core Height'), (2172, 269, 'Core Width'), (2172, 268, 'Core Thickness'),
  (2172, 5061, 'Core Row Quantity'), (2172, 302, 'Core Material'), (2172, 305, 'Tank Material'),
  (2172, 7448, 'Down Flow Or Cross Flow Type');

create table meta.atributo_desde_sap (     -- columnas numéricas de app.articulo que se precargan como atributo PAdb
  part_terminology_id integer not null,
  paid                integer not null,
  columna             text not null,
  uom_code            text,
  primary key (part_terminology_id, paid)
);
insert into meta.atributo_desde_sap values
  (2172, 267, 'panal_alto_mm', 'MM'), (2172, 269, 'panal_largo_mm', 'MM'), (2172, 268, 'panal_ancho_mm', 'MM'),
  (2172, 5061, 'filas_panal', null);

------------------------------------------------------------------------------------------
-- Emparejamiento con el catálogo maestro (ADR 0011). parte_id vive en articulos_consolidacion.
------------------------------------------------------------------------------------------
create table app.articulo_parte (
  id             bigint generated always as identity primary key,
  articulo_id    bigint not null references app.articulo,
  parte_id       bigint not null,
  es_principal   boolean not null default false,
  origen         app.origen_dato not null check (origen in ('CONSOLIDACION', 'MANUAL', 'HEREDADO_EQUIVALENTE')),
  confirmado_por bigint not null references app.usuario,
  confirmado_en  timestamptz not null default now(),
  unique (articulo_id, parte_id)
);
create unique index articulo_parte_principal on app.articulo_parte (articulo_id) where es_principal;

------------------------------------------------------------------------------------------
-- Aplicaciones vehiculares ACES (vehículo o equipo; IDs de AutoCare o de MercadoExterno ≥ 1e9)
------------------------------------------------------------------------------------------
create table app.articulo_aplicacion (
  id                bigint generated always as identity primary key,
  articulo_id       bigint not null references app.articulo,
  base_vehicle_id   integer,
  equipment_base_id integer,
  sub_model_id      integer,
  engine_config_id  integer,
  transmission_id   integer,
  notas             text,
  origen            app.origen_dato not null,
  parte_id          bigint,                          -- si se adoptó de una parte de Consolidación
  confirmado_por    bigint references app.usuario,   -- null = sugerida, aún no confirmada
  confirmado_en     timestamptz,
  check (num_nonnulls(base_vehicle_id, equipment_base_id) = 1),
  check ((confirmado_por is null) = (confirmado_en is null))
);
create unique index articulo_aplicacion_unica on app.articulo_aplicacion
  (articulo_id, coalesce(base_vehicle_id, 0), coalesce(equipment_base_id, 0), coalesce(sub_model_id, 0),
   coalesce(engine_config_id, 0), coalesce(transmission_id, 0));
create index on app.articulo_aplicacion (base_vehicle_id);

create table app.articulo_aplicacion_region (
  articulo_aplicacion_id bigint  not null references app.articulo_aplicacion on delete cascade,
  region_id              integer not null,
  confirmado_por         bigint  not null references app.usuario,
  primary key (articulo_aplicacion_id, region_id)
);

------------------------------------------------------------------------------------------
-- Atributos PIES (PAdb)
------------------------------------------------------------------------------------------
create table app.articulo_atributo (
  id             bigint generated always as identity primary key,
  articulo_id    bigint not null references app.articulo,
  paid           integer not null,
  valor_num      numeric,
  uom_code       text,
  valid_value_id integer,
  valor_texto    text,
  origen         app.origen_dato not null,
  parte_id       bigint,
  confirmado_por bigint references app.usuario,
  confirmado_en  timestamptz,
  unique (articulo_id, paid),
  check (num_nonnulls(valor_num, valid_value_id, valor_texto) = 1),
  check ((confirmado_por is null) = (confirmado_en is null))
);

-- Precarga desde SAP como SUGERENCIA (sin confirmar). No pisa lo que ya exista.
create function app.fn_precargar_atributos_sap(p_articulo_id bigint) returns integer
language plpgsql as $$
declare r record; v numeric; n integer := 0; pt integer;
begin
  select part_terminology_id into pt from app.articulo where id = p_articulo_id;
  for r in select * from meta.atributo_desde_sap where part_terminology_id = pt loop
    execute format('select %I from app.articulo where id = $1', r.columna) into v using p_articulo_id;
    if v is not null then
      insert into app.articulo_atributo (articulo_id, paid, valor_num, uom_code, origen)
      values (p_articulo_id, r.paid, v, r.uom_code, 'SAP')
      on conflict (articulo_id, paid) do nothing;
      if found then n := n + 1; end if;
    end if;
  end loop;
  return n;
end $$;

------------------------------------------------------------------------------------------
-- Equivalencia Fabricado ↔ Importado (ADR 0005): cruza línea, no categoría (ADR 0010)
------------------------------------------------------------------------------------------
create table app.articulo_equivalencia (
  id             bigint generated always as identity primary key,
  fabricado_id   bigint not null references app.articulo,
  importado_id   bigint not null references app.articulo,
  origen         app.origen_equivalencia not null,
  estado         app.estado_sugerencia not null default 'SUGERIDA',
  criterio       jsonb,                              -- qué se comparó (aplicaciones, medidas…)
  confirmado_por bigint references app.usuario,
  confirmado_en  timestamptz,
  unique (fabricado_id, importado_id),
  check ((estado = 'SUGERIDA') = (confirmado_por is null))
);

create function app.validar_equivalencia() returns trigger language plpgsql as $$
declare f app.articulo; i app.articulo;
begin
  select * into f from app.articulo where id = new.fabricado_id;
  select * into i from app.articulo where id = new.importado_id;
  if f.linea is distinct from 'FABRICADO' or i.linea is distinct from 'IMPORTADO' then
    raise exception 'EQUIVALENCIA_INVALIDA: debe ser FABRICADO → IMPORTADO (% → %)', f.linea, i.linea using errcode = 'P0001';
  end if;
  if f.categoria_id is distinct from i.categoria_id then
    raise exception 'EQUIVALENCIA_INVALIDA: categorías distintas (% vs %)', f.categoria_codigo, i.categoria_codigo using errcode = 'P0001';
  end if;
  return new;
end $$;
create trigger validar before insert or update on app.articulo_equivalencia
  for each row execute function app.validar_equivalencia();

-- El Fabricado hereda del Importado confirmado: emparejamiento principal y aplicaciones confirmadas (como sugerencias).
create function app.fn_heredar_de_equivalente(p_fabricado_id bigint, p_usuario_id bigint) returns jsonb
language plpgsql as $$
declare v_importado bigint; n_partes integer; n_apps integer;
begin
  select importado_id into v_importado from app.articulo_equivalencia
  where fabricado_id = p_fabricado_id and estado = 'CONFIRMADA' order by confirmado_en desc limit 1;
  if v_importado is null then
    raise exception 'SIN_EQUIVALENTE_CONFIRMADO: el fabricado % no tiene Importado confirmado', p_fabricado_id using errcode = 'P0001';
  end if;

  insert into app.articulo_parte (articulo_id, parte_id, es_principal, origen, confirmado_por)
  select p_fabricado_id, ap.parte_id,
         ap.es_principal and not exists (select 1 from app.articulo_parte x where x.articulo_id = p_fabricado_id and x.es_principal),
         'HEREDADO_EQUIVALENTE', p_usuario_id
  from app.articulo_parte ap where ap.articulo_id = v_importado
  on conflict (articulo_id, parte_id) do nothing;
  get diagnostics n_partes = row_count;

  insert into app.articulo_aplicacion (articulo_id, base_vehicle_id, equipment_base_id, sub_model_id, engine_config_id,
                                       transmission_id, notas, origen, parte_id)
  select p_fabricado_id, a.base_vehicle_id, a.equipment_base_id, a.sub_model_id, a.engine_config_id, a.transmission_id,
         a.notas, 'HEREDADO_EQUIVALENTE', a.parte_id
  from app.articulo_aplicacion a
  where a.articulo_id = v_importado and a.confirmado_por is not null
  on conflict do nothing;
  get diagnostics n_apps = row_count;

  return jsonb_build_object('importado_id', v_importado, 'partes', n_partes, 'aplicaciones_sugeridas', n_apps);
end $$;

------------------------------------------------------------------------------------------
-- Imágenes (ADR 0013): fotos propias en MinIO o URL de proveedor / Consolidación
------------------------------------------------------------------------------------------
create table app.articulo_imagen (
  id            bigint generated always as identity primary key,
  articulo_id   bigint not null references app.articulo,
  origen        app.origen_imagen not null,
  url           text,
  minio_bucket  text,
  minio_objeto  text,
  orden         smallint not null default 1,
  subida_por    bigint references app.usuario,
  subida_en     timestamptz not null default now(),
  validada      boolean not null default false,
  validada_por  bigint references app.usuario,
  validada_en   timestamptz,
  check (url is not null or (minio_bucket is not null and minio_objeto is not null)),
  check (origen <> 'PROPIA' or minio_objeto is not null),
  check (validada = (validada_por is not null))
);
create unique index articulo_imagen_objeto on app.articulo_imagen (minio_bucket, minio_objeto) where minio_objeto is not null;

------------------------------------------------------------------------------------------
-- Cola de verificación (ADR 0012)
------------------------------------------------------------------------------------------
create table app.tarea_verificacion (
  id          bigint generated always as identity primary key,
  articulo_id bigint not null references app.articulo,
  origen      app.origen_tarea not null,
  detalle     jsonb not null default '{}',
  estado      app.estado_tarea not null default 'ABIERTA',
  creada_en   timestamptz not null default now(),
  asignado_a  bigint references app.usuario,
  resuelto_por bigint references app.usuario,
  resuelto_en timestamptz,
  nota        text,
  check ((estado = 'ABIERTA') = (resuelto_por is null)),
  check (estado <> 'CON_HALLAZGO' or nota is not null)
);
create unique index tarea_abierta_unica on app.tarea_verificacion
  (articulo_id, origen, coalesce(detalle ->> 'imagen_id', '')) where estado = 'ABIERTA';

-- Foto propia nueva en un artículo ya validado → tarea NUEVA_FOTO (si está en proceso, se valida en el flujo normal).
create function app.tarea_por_foto_nueva() returns trigger language plpgsql as $$
begin
  if new.origen = 'PROPIA' and exists (select 1 from app.articulo a where a.id = new.articulo_id
                                       and a.estado in ('VALIDADO', 'SINCRONIZADO') and a.activo) then
    insert into app.tarea_verificacion (articulo_id, origen, detalle)
    values (new.articulo_id, 'NUEVA_FOTO', jsonb_build_object('imagen_id', new.id, 'objeto', new.minio_objeto))
    on conflict do nothing;
  end if;
  return new;
end $$;
create trigger tarea_por_foto after insert on app.articulo_imagen for each row execute function app.tarea_por_foto_nueva();

-- Muestreo aleatorio de artículos validados para control de calidad.
create function app.fn_generar_muestreo(p_cantidad integer, p_categoria_id smallint default null) returns integer
language sql as $$
  with elegidos as (
    select a.id from app.articulo a
    where a.activo and a.estado in ('VALIDADO', 'SINCRONIZADO')
      and (p_categoria_id is null or a.categoria_id = p_categoria_id)
      and not exists (select 1 from app.tarea_verificacion t where t.articulo_id = a.id and t.estado = 'ABIERTA')
    order by random() limit p_cantidad
  ), ins as (
    insert into app.tarea_verificacion (articulo_id, origen) select id, 'MUESTREO' from elegidos returning 1
  )
  select count(*)::integer from ins
$$;

create function app.fn_resolver_verificacion(p_tarea_id bigint, p_usuario_id bigint, p_resultado app.estado_tarea, p_nota text default null)
returns app.tarea_verificacion
language plpgsql as $$
declare t app.tarea_verificacion;
begin
  if p_resultado = 'ABIERTA' then
    raise exception 'RESULTADO_INVALIDO: use CONFORME o CON_HALLAZGO' using errcode = 'P0001';
  end if;
  if not exists (select 1 from app.usuario_rol where usuario_id = p_usuario_id and rol in ('SUPERVISOR', 'ADMINISTRADOR')) then
    raise exception 'ROL_INSUFICIENTE: la verificación la resuelve un supervisor o administrador' using errcode = '42501';
  end if;
  update app.tarea_verificacion
  set estado = p_resultado, resuelto_por = p_usuario_id, resuelto_en = now(), nota = meta.limpiar(p_nota)
  where id = p_tarea_id and estado = 'ABIERTA'
  returning * into t;
  if not found then
    raise exception 'TAREA_NO_ABIERTA: %', p_tarea_id using errcode = 'P0001';
  end if;

  if p_resultado = 'CONFORME' and t.origen = 'NUEVA_FOTO' then
    update app.articulo_imagen set validada = true, validada_por = p_usuario_id, validada_en = now()
    where id = (t.detalle ->> 'imagen_id')::bigint;
  elsif p_resultado = 'CON_HALLAZGO' then
    perform app.fn_transicionar(t.articulo_id, 'PENDIENTE', 'USUARIO', p_usuario_id::text, 'VERIFICACION',
                                jsonb_build_object('tarea_id', t.id, 'origen', t.origen, 'nota', t.nota));
  end if;
  return t;
end $$;

------------------------------------------------------------------------------------------
-- Homologación SAP ↔ AutoCare / MercadoExterno (para precargar búsquedas por vehículo)
------------------------------------------------------------------------------------------
create table app.homologacion_marca (
  marca_codigo_sap text primary key,                -- @IGT_MARCAS.Code
  make_id          integer not null,                -- AutoCare o MercadoExterno (≥ 1e9)
  estado           app.estado_sugerencia not null default 'SUGERIDA',
  confirmado_por   bigint references app.usuario,
  confirmado_en    timestamptz,
  check ((estado = 'SUGERIDA') = (confirmado_por is null))
);
create table app.homologacion_modelo (
  marca_codigo_sap  text not null,
  modelo_codigo_sap integer not null,                -- @IGT_LINEA.LineId
  model_id          integer not null,
  estado            app.estado_sugerencia not null default 'SUGERIDA',
  confirmado_por    bigint references app.usuario,
  confirmado_en     timestamptz,
  primary key (marca_codigo_sap, modelo_codigo_sap),
  check ((estado = 'SUGERIDA') = (confirmado_por is null))
);

------------------------------------------------------------------------------------------
-- Requisitos completos para enviar a POR_VALIDAR (reemplaza la versión de 0001)
------------------------------------------------------------------------------------------
create or replace function app.fn_requisitos_por_validar(p_articulo_id bigint) returns text[]
language sql stable as $$
  select array_remove(
    array[
      case when a.part_terminology_id is null then 'TIPO_DE_PARTE' end,
      case when not exists (select 1 from app.articulo_aplicacion x where x.articulo_id = a.id and x.confirmado_por is not null)
            and not exists (select 1 from app.articulo_parte x where x.articulo_id = a.id)
           then 'APLICACION_O_EMPAREJAMIENTO' end,
      case when a.linea = 'FABRICADO'
            and not exists (select 1 from app.articulo_equivalencia e where e.fabricado_id = a.id and e.estado = 'CONFIRMADA')
            and meta.limpiar(a.justificacion_sin_equivalente) is null
           then 'EQUIVALENTE_IMPORTADO' end
    ]
    || coalesce((select array_agg('ATRIBUTO:' || r.nombre order by r.paid)
                 from meta.atributo_requerido r
                 where r.part_terminology_id = a.part_terminology_id
                   and not exists (select 1 from app.articulo_atributo t
                                   where t.articulo_id = a.id and t.paid = r.paid and t.confirmado_por is not null)), '{}'),
    null)
  from app.articulo a where a.id = p_articulo_id
$$;

------------------------------------------------------------------------------------------
-- Auditoría de cambios de datos (antes / después) en las tablas que editan los usuarios
------------------------------------------------------------------------------------------
create table audit.auditoria_evento (
  id         bigint generated always as identity primary key,
  entidad    text not null,
  entidad_id bigint,
  accion     text not null check (accion in ('INSERT', 'UPDATE', 'DELETE')),
  actor      text not null,
  antes      jsonb,
  despues    jsonb,
  creado_en  timestamptz not null default now()
);
create index on audit.auditoria_evento (entidad, entidad_id);

-- El actor lo fija la APP por transacción: set local app.usuario_id = '<id>'.
create function audit.registrar() returns trigger language plpgsql as $$
declare v_antes jsonb := case when tg_op <> 'INSERT' then to_jsonb(old) end;
        v_despues jsonb := case when tg_op <> 'DELETE' then to_jsonb(new) end;
begin
  insert into audit.auditoria_evento (entidad, entidad_id, accion, actor, antes, despues)
  values (tg_table_schema || '.' || tg_table_name, (coalesce(v_despues, v_antes) ->> 'id')::bigint, tg_op,
          coalesce(nullif(current_setting('app.usuario_id', true), ''), session_user), v_antes, v_despues);
  return null;
end $$;

do $$
declare t text;
begin
  foreach t in array array['articulo_parte', 'articulo_aplicacion', 'articulo_atributo', 'articulo_equivalencia',
                           'articulo_imagen', 'homologacion_marca', 'homologacion_modelo']
  loop
    execute format('create trigger auditar after insert or update or delete on app.%I for each row execute function audit.registrar()', t);
  end loop;
end $$;
