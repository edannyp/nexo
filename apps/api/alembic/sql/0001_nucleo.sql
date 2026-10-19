-- Nexo 0001 — Núcleo: staging del ETL, artículo canónico, máquina de estados, bitácora, usuarios y calidad SAP.
-- Decisiones: ADR 0005–0008, 0010, 0012, 0015. Mapeo: architecture/datos/mapeo-fuentes.md. Contrato ETL: contratos.md.

create extension if not exists pg_trgm;
create extension if not exists citext;

create schema if not exists staging;  -- lo escribe el ETL externo (contrato)
create schema if not exists app;      -- modelo de trabajo de la APP
create schema if not exists audit;    -- bitácora
create schema if not exists meta;     -- diccionario y catálogos de configuración

------------------------------------------------------------------------------------------
-- Tipos
------------------------------------------------------------------------------------------
create type app.estado_articulo as enum ('PENDIENTE', 'POR_VALIDAR', 'RECHAZADO', 'VALIDADO', 'SINCRONIZADO');
create type app.linea           as enum ('IMPORTADO', 'FABRICADO');
create type app.motivo_inactivo as enum ('SAP_CONGELADO', 'NOMBRE_INACTIVO', 'FUERA_DE_ALCANCE');
create type app.actor_tipo      as enum ('USUARIO', 'PROCESO');
create type app.rol             as enum ('OPERADOR', 'SUPERVISOR', 'ADMINISTRADOR', 'FOTOS');
create type app.transmision     as enum ('AUTOMATICA', 'MANUAL');
create type app.tipo_flujo      as enum ('HORIZONTAL', 'VERTICAL');
create type app.tamano_panal    as enum ('PEQUENO', 'MEDIANO', 'GRANDE');
create type app.tipo_hallazgo   as enum ('MARCA_INVALIDA', 'MEDIDAS_INVERTIDAS', 'SUBCATEGORIA_INCONSISTENTE', 'NOMBRE_INACTIVO_SIN_CONGELAR',
                                        'VALOR_NO_RECONOCIDO', 'ANIOS_INVERTIDOS');
create type audit.tipo_evento   as enum ('ALTA', 'TRANSICION', 'INACTIVADO', 'ACTIVADO', 'DATOS_SAP');

------------------------------------------------------------------------------------------
-- Utilidades
------------------------------------------------------------------------------------------
-- Recorta y colapsa espacios; cadena vacía → null.
create function meta.limpiar(txt text) returns text language sql immutable as $$
  select nullif(regexp_replace(btrim(coalesce(txt, '')), '\s+', ' ', 'g'), '') $$;

------------------------------------------------------------------------------------------
-- meta: catálogos de configuración y diccionario de campos (ADR 0007)
------------------------------------------------------------------------------------------
create table meta.unidad_longitud (      -- SAP OLGT
  codigo_sap integer primary key,
  simbolo    text not null,
  factor_mm  numeric not null check (factor_mm > 0)
);
insert into meta.unidad_longitud values (1, 'mm', 1), (2, 'cm', 10), (3, 'dm', 100), (4, 'm', 1000), (5, '"', 25.4), (6, '''', 304.8);

create table meta.valor_lista_sap (      -- valores de listas UDF de SAP (UFD1) → valor canónico
  campo_sap      text not null,
  valor_sap      text not null,
  valor_canonico text not null,
  primary key (campo_sap, valor_sap)
);
insert into meta.valor_lista_sap values
  ('U_InletLocation', 'Bottom Center', 'ABAJO_CENTRO'), ('U_InletLocation', 'Bottom Left', 'ABAJO_IZQUIERDA'),
  ('U_InletLocation', 'Bottom Right', 'ABAJO_DERECHA'), ('U_InletLocation', 'Center Left', 'CENTRO_IZQUIERDA'),
  ('U_InletLocation', 'Center Right', 'CENTRO_DERECHA'), ('U_InletLocation', 'Left', 'IZQUIERDA'),
  ('U_InletLocation', 'Right', 'DERECHA'), ('U_InletLocation', 'Top Center', 'ARRIBA_CENTRO'),
  ('U_InletLocation', 'Top Left', 'ARRIBA_IZQUIERDA'), ('U_InletLocation', 'Top Right', 'ARRIBA_DERECHA'),
  ('U_OutletLocation', 'Bottom Center', 'ABAJO_CENTRO'), ('U_OutletLocation', 'Bottom Left', 'ABAJO_IZQUIERDA'),
  ('U_OutletLocation', 'Bottom Right', 'ABAJO_DERECHA'), ('U_OutletLocation', 'Left', 'IZQUIERDA'),
  ('U_OutletLocation', 'Right', 'DERECHA'), ('U_OutletLocation', 'Top Center', 'ARRIBA_CENTRO'),
  ('U_OutletLocation', 'Top Left', 'ARRIBA_IZQUIERDA'),
  ('U_OutletLocation', 'Top Rigth', 'ARRIBA_DERECHA');  -- sic en SAP

create table meta.marca_sap_invalida (   -- códigos de @IGT_MARCAS que no son marcas: basura, no se interpretan (pregunta 23)
  marca_codigo text primary key,
  nombre       text not null
);
insert into meta.marca_sap_invalida values ('00132', 'Varios'), ('00133', 'NO APLICA'), ('00136', 'RLT'), ('00137', 'UNIVERSAL');

create table meta.diccionario_campo (
  esquema        text not null,
  tabla          text not null,
  columna        text not null,
  fuente         text not null,
  tabla_origen   text,
  campo_origen   text,
  transformacion text,
  en_hash        boolean not null default false,
  orden_hash     smallint,
  descripcion    text,
  primary key (esquema, tabla, columna),
  check (en_hash = (orden_hash is not null))
);

insert into meta.diccionario_campo (esquema, tabla, columna, fuente, tabla_origen, campo_origen, transformacion, en_hash, orden_hash) values
  ('app','articulo','item_code',                     'SAP','OITM','ItemCode',              'trim, mayúsculas', false, null),
  ('app','articulo','descripcion',                   'SAP','OITM','ItemName',              'trim, colapsar espacios', true, 1),
  ('app','articulo','categoria_codigo',              'SAP','OITM','U_Categoria',           '@IGT_CAT.Code', true, 2),
  ('app','articulo','subcategoria_codigo',           'SAP','OITM','U_SubCat',              '@IGT_CAT2.Code', true, 3),
  ('app','articulo','linea',                         'SAP','@IGT_CAT2','Name',             'IMPORTADOS→IMPORTADO, FABRICADOS→FABRICADO', false, null),
  ('app','articulo','material_codigo',               'SAP','OITM','U_SubSubCat',           null, true, 4),
  ('app','articulo','material_descripcion',          'SAP','OITM','U_SSCatName',           'trim', true, 5),
  ('app','articulo','numero_parte_proveedor',        'SAP','OITM','SuppCatNum',            'trim, mayúsculas', true, 6),
  ('app','articulo','codigo_anterior',               'SAP','OITM','U_CodAnterior',         'separar por coma', false, null),
  ('app','articulo','marca_vehiculo_codigo',         'SAP','OITM','U_Marca',               'numérico → 5 dígitos; si no existe en @IGT_MARCAS → null + hallazgo', true, 7),
  ('app','articulo','modelo_vehiculo_codigo',        'SAP','OITM','U_Linea',               'LineId en @IGT_LINEA', true, 8),
  ('app','articulo','modelo_vehiculo',               'SAP','OITM','U_LineName',            'trim, mayúsculas', true, 9),
  ('app','articulo','anio_desde',                    'SAP','OITM','U_anio1',               '0 → null', true, 10),
  ('app','articulo','anio_hasta',                    'SAP','OITM','U_anio2',               '0 → null', true, 11),
  ('app','articulo','motor',                         'SAP','OITM','U_Motor',               'trim', true, 12),
  ('app','articulo','cilindrada',                    'SAP','OITM','U_Cyl',                 'trim', true, 13),
  ('app','articulo','transmision',                   'SAP','OITM','U_transmision',         'AT→AUTOMATICA, MT→MANUAL', true, 14),
  ('app','articulo','panal_alto_mm',                 'SAP','OITM','SHeight1 + SHght1Unit', '× OLGT.SizeInMM; 0 → null', true, 15),
  ('app','articulo','panal_largo_mm',                'SAP','OITM','SLength1 + SLen1Unit',  '× OLGT.SizeInMM; 0 → null', true, 16),
  ('app','articulo','panal_ancho_mm',              'SAP','OITM','SWidth1 + SWdth1Unit',  '× OLGT.SizeInMM; 0 → null', true, 17),
  ('app','articulo','tamano_panal',                  'SAP','OITM','U_Tamanio',             'P/M/G o Pequeño/Mediano/Grande', true, 18),
  ('app','articulo','filas_panal',                   'SAP','OITM','U_Filas',               null, true, 19),
  ('app','articulo','tipo_panal',                    'SAP','OITM','U_TipoPanal',           'trim', true, 20),
  ('app','articulo','material_panal',                'SAP','OITM','U_CoreMaterial',        'trim', true, 21),
  ('app','articulo','material_tanque',               'SAP','OITM','U_TankMaterial',        'trim', true, 22),
  ('app','articulo','dimension_tanque',              'SAP','OITM','U_TankDimension',       'trim', true, 23),
  ('app','articulo','tipo_flujo',                    'SAP','OITM','U_FlowType',            'Cross Flow→HORIZONTAL, Down Flow→VERTICAL', true, 24),
  ('app','articulo','entrada_diametro',              'SAP','OITM','U_InletDiameter',       'trim', true, 25),
  ('app','articulo','entrada_ubicacion',             'SAP','OITM','U_InletLocation',       'meta.valor_lista_sap', true, 26),
  ('app','articulo','salida_diametro',               'SAP','OITM','U_OutletDiameter',      'trim', true, 27),
  ('app','articulo','salida_ubicacion',              'SAP','OITM','U_OutletLocation',      'meta.valor_lista_sap', true, 28),
  ('app','articulo','incluye_tapon',                 'SAP','OITM','U_CapIncluded',         'S/N', true, 29),
  ('app','articulo','incluye_termostato',            'SAP','OITM','U_ThermostatIncluded',  'S/N', true, 30),
  ('app','articulo','incluye_enfriador_transmision', 'SAP','OITM','U_TransmissionOilCoolerIncluded', 'S/N', true, 31),
  ('app','articulo','material_principal',            'SAP','OITM','U_Material_PRI',        'trim', true, 32),
  ('app','articulo','material_secundario',           'SAP','OITM','U_Material_SEC',        'trim', true, 33),
  ('app','articulo','material_otro',                 'SAP','OITM','U_Material_Other',      'trim', true, 34),
  ('app','articulo','composicion_material',          'SAP','OITM','U_Material_Comp',       'trim', true, 35),
  ('app','articulo','autocare_id_sap',               'SAP','OITM','U_ID_Aces',             'trim', false, null);

------------------------------------------------------------------------------------------
-- Usuarios (ADR 0015)
------------------------------------------------------------------------------------------
create table app.usuario (
  id                    bigint generated always as identity primary key,
  usuario               citext not null unique,
  nombre                text not null,
  correo                citext,
  password_hash         text not null,
  debe_cambiar_password boolean not null default true,
  intentos_fallidos     smallint not null default 0,
  bloqueado_hasta       timestamptz,
  activo                boolean not null default true,
  ultimo_acceso_en      timestamptz,
  creado_en             timestamptz not null default now()
);

create table app.usuario_rol (
  usuario_id bigint not null references app.usuario,
  rol        app.rol not null,
  primary key (usuario_id, rol)
);

------------------------------------------------------------------------------------------
-- Categorías en alcance (context/categorias.md) y preferencia de filtro global (ADR 0010)
------------------------------------------------------------------------------------------
create table app.categoria (
  id                          smallint generated always as identity primary key,
  codigo_sap                  text not null unique,
  nombre                      text not null,
  part_terminology_id_defecto integer,
  activa                      boolean not null default true
);
insert into app.categoria (codigo_sap, nombre, part_terminology_id_defecto) values
  ('25', 'RADIADORES', 2172), ('07', 'CONDENSADORES', 6708), ('18', 'INTERCOOLER', 12616),
  ('11', 'ENFRIADORES DE ACEITE', 2084), ('29', 'TANQUES', 48305), ('09', 'DEPOSITOS AUXILIARES', 10457),
  ('44', 'TOLVA RADIADOR', 10707), ('46', 'INTERCAMBIADOR', null);

create table app.preferencia_usuario (
  usuario_id   bigint primary key references app.usuario,
  categoria_id smallint not null references app.categoria default 1,  -- 25 RADIADORES
  linea        app.linea not null default 'IMPORTADO'
);

------------------------------------------------------------------------------------------
-- staging: lo que escribe el ETL (contrato, ADR 0006). Valores CRUDOS con nombres canónicos.
------------------------------------------------------------------------------------------
create table staging.lote (
  lote_id      bigint generated always as identity primary key,
  iniciado_en  timestamptz not null default now(),
  procesado_en timestamptz,
  resultado    jsonb
);

-- Catálogos SAP necesarios para validar (@IGT_MARCAS, @IGT_LINEA). El ETL los envía completos en cada lote.
create table staging.sap_marca (
  marca_codigo text primary key,          -- @IGT_MARCAS.Code
  nombre       text not null,
  lote_id      bigint not null references staging.lote
);
create table staging.sap_modelo (
  marca_codigo  text not null,            -- @IGT_LINEA.Code
  modelo_codigo integer not null,         -- @IGT_LINEA.LineId
  nombre        text not null,            -- @IGT_LINEA.U_Linea
  tamano        text,                     -- @IGT_LINEA.U_Tamanio
  lote_id       bigint not null references staging.lote,
  primary key (marca_codigo, modelo_codigo)
);

create table staging.articulo_sap (
  item_code                     text primary key,
  descripcion                   text,
  categoria_codigo              text,
  subcategoria_codigo           text,
  subcategoria_nombre           text,     -- @IGT_CAT2.Name
  material_codigo               text,
  material_descripcion          text,
  numero_parte_proveedor        text,
  codigo_anterior               text,
  marca_vehiculo_codigo         text,
  modelo_vehiculo_codigo        integer,
  modelo_vehiculo               text,
  anio_desde                    integer,
  anio_hasta                    integer,
  motor                         text,
  cilindrada                    text,
  transmision                   text,     -- AT / MT
  panal_alto                    numeric,
  panal_alto_unidad             integer,  -- OLGT.UnitCode
  panal_largo                   numeric,
  panal_largo_unidad            integer,
  panal_ancho                 numeric,
  panal_ancho_unidad          integer,
  tamano_panal                  text,     -- P / M / G
  filas_panal                   integer,
  tipo_panal                    text,
  material_panal                text,
  material_tanque               text,
  dimension_tanque              text,
  tipo_flujo                    text,     -- Cross Flow / Down Flow
  entrada_diametro              text,
  entrada_ubicacion             text,
  salida_diametro               text,
  salida_ubicacion              text,
  incluye_tapon                 text,     -- S / N
  incluye_termostato            text,
  incluye_enfriador_transmision text,
  material_principal            text,
  material_secundario           text,
  material_otro                 text,
  composicion_material          text,
  autocare_id_sap               text,
  congelado_sap                 text,     -- frozenFor Y / N
  datos_sap                     jsonb not null default '{}',
  extraido_en                   timestamptz not null,
  lote_id                       bigint not null references staging.lote
);
create index on staging.articulo_sap (lote_id);

------------------------------------------------------------------------------------------
-- app.articulo: copia de trabajo con valores normalizados
------------------------------------------------------------------------------------------
create table app.articulo (
  id                            bigint generated always as identity primary key,
  item_code                     text not null unique,
  descripcion                   text,
  categoria_id                  smallint references app.categoria,
  categoria_codigo              text,
  subcategoria_codigo           text,
  linea                         app.linea,
  part_terminology_id           integer,
  material_codigo               text,
  material_descripcion          text,
  numero_parte_proveedor        text,
  codigo_anterior               text[],
  marca_vehiculo_codigo         text,
  marca_vehiculo                text,
  modelo_vehiculo_codigo        integer,
  modelo_vehiculo               text,
  anio_desde                    smallint,
  anio_hasta                    smallint,
  motor                         text,
  cilindrada                    text,
  transmision                   app.transmision,
  panal_alto_mm                 numeric(10,2),
  panal_largo_mm                numeric(10,2),
  panal_ancho_mm              numeric(10,2),
  tamano_panal                  app.tamano_panal,
  filas_panal                   smallint,
  tipo_panal                    text,
  material_panal                text,
  material_tanque               text,
  dimension_tanque              text,
  tipo_flujo                    app.tipo_flujo,
  entrada_diametro              text,
  entrada_ubicacion             text,
  salida_diametro               text,
  salida_ubicacion              text,
  incluye_tapon                 boolean,
  incluye_termostato            boolean,
  incluye_enfriador_transmision boolean,
  material_principal            text,
  material_secundario           text,
  material_otro                 text,
  composicion_material          text,
  autocare_id_sap               text,
  hash_control                  text not null,
  estado                        app.estado_articulo not null default 'PENDIENTE',
  version                       integer not null default 1,
  activo                        boolean not null default true,
  motivo_inactivo               app.motivo_inactivo,
  asignado_a                    bigint references app.usuario,
  asignado_hasta                timestamptz,
  datos_sap                     jsonb not null default '{}',
  ultimo_lote_id                bigint references staging.lote,
  creado_en                     timestamptz not null default now(),
  actualizado_en                timestamptz not null default now(),
  check (activo = (motivo_inactivo is null)),
  check ((asignado_a is null) = (asignado_hasta is null))
);
create index on app.articulo (categoria_id, linea, estado) where activo;
create index on app.articulo using gin (descripcion gin_trgm_ops);
create index on app.articulo using gin (numero_parte_proveedor gin_trgm_ops);

-- Comentario con el nombre de origen en cada columna (ADR 0007), generado desde el diccionario.
do $$
declare r record;
begin
  for r in select * from meta.diccionario_campo where esquema = 'app' and tabla = 'articulo' loop
    execute format('comment on column app.articulo.%I is %L', r.columna,
                   r.fuente || ': ' || r.tabla_origen || '.' || r.campo_origen || coalesce(' — ' || r.transformacion, ''));
  end loop;
end $$;

------------------------------------------------------------------------------------------
-- Bitácora y calidad
------------------------------------------------------------------------------------------
create table audit.bitacora_articulo (
  id             bigint generated always as identity primary key,
  articulo_id    bigint not null references app.articulo,
  tipo           audit.tipo_evento not null,
  estado_origen  app.estado_articulo,
  estado_destino app.estado_articulo,
  actor_tipo     app.actor_tipo not null,
  actor          text not null,           -- usuario.id como texto, o 'PROCESO:ETL', 'PROCESO:SALIDA'…
  motivo         text,
  detalle        jsonb,
  creado_en      timestamptz not null default now()
);
create index on audit.bitacora_articulo (articulo_id, creado_en);

create table app.hallazgo_calidad_sap (
  id           bigint generated always as identity primary key,
  articulo_id  bigint not null references app.articulo,
  tipo         app.tipo_hallazgo not null,
  campo_sap    text not null,
  valor        text,
  detectado_en timestamptz not null default now(),
  corregido_en timestamptz
);
create unique index hallazgo_abierto_unico on app.hallazgo_calidad_sap (articulo_id, tipo, campo_sap) where corregido_en is null;

------------------------------------------------------------------------------------------
-- Máquina de estados (ADR 0012)
------------------------------------------------------------------------------------------
create table app.transicion_permitida (
  origen                app.estado_articulo not null,
  destino               app.estado_articulo not null,
  actor_tipo            app.actor_tipo not null,
  roles                 app.rol[],                 -- null = proceso
  requiere_motivo       boolean not null default false,
  prohibe_mismo_usuario boolean not null default false,  -- doble control: quien envió a POR_VALIDAR no valida
  primary key (origen, destino, actor_tipo),
  check ((actor_tipo = 'USUARIO') = (roles is not null))
);
insert into app.transicion_permitida values
  ('PENDIENTE',    'POR_VALIDAR',  'USUARIO', '{OPERADOR,SUPERVISOR}',      false, false),
  ('POR_VALIDAR',  'VALIDADO',     'USUARIO', '{SUPERVISOR}',               false, true),
  ('POR_VALIDAR',  'RECHAZADO',    'USUARIO', '{SUPERVISOR}',               true,  true),
  ('RECHAZADO',    'POR_VALIDAR',  'USUARIO', '{OPERADOR,SUPERVISOR}',      false, false),
  ('VALIDADO',     'SINCRONIZADO', 'PROCESO', null,                         false, false),
  ('VALIDADO',     'PENDIENTE',    'PROCESO', null,                         true,  false),  -- HASH_CAMBIO
  ('SINCRONIZADO', 'PENDIENTE',    'PROCESO', null,                         true,  false),  -- HASH_CAMBIO
  ('VALIDADO',     'PENDIENTE',    'USUARIO', '{SUPERVISOR,ADMINISTRADOR}', true,  false),  -- reapertura / verificación
  ('SINCRONIZADO', 'PENDIENTE',    'USUARIO', '{SUPERVISOR,ADMINISTRADOR}', true,  false);

-- Requisitos para enviar a POR_VALIDAR. Devuelve lo que falta (vacío = listo).
-- La migración de enriquecimiento la reemplaza con las reglas completas (aplicaciones, emparejamiento, atributos).
create function app.fn_requisitos_por_validar(p_articulo_id bigint) returns text[]
language sql stable as $$
  select array_remove(array[
    case when a.part_terminology_id is null then 'TIPO_DE_PARTE' end
  ], null)
  from app.articulo a where a.id = p_articulo_id
$$;

create function app.fn_transicionar(
  p_articulo_id bigint,
  p_destino     app.estado_articulo,
  p_actor_tipo  app.actor_tipo,
  p_actor       text,
  p_motivo      text default null,
  p_detalle     jsonb default null,
  p_version     integer default null       -- control optimista: si viene y no coincide → error
) returns app.articulo
language plpgsql as $$
declare
  a       app.articulo;
  regla   app.transicion_permitida;
  faltan  text[];
  envio   text;
begin
  select * into a from app.articulo where id = p_articulo_id for update;
  if not found then
    raise exception 'ARTICULO_NO_EXISTE: %', p_articulo_id using errcode = 'P0002';
  end if;
  if p_version is not null and p_version <> a.version then
    raise exception 'CONFLICTO_VERSION: el artículo cambió (versión % ≠ %)', a.version, p_version using errcode = '40001';
  end if;
  if not a.activo then
    raise exception 'ARTICULO_INACTIVO: % (%)', a.item_code, a.motivo_inactivo using errcode = 'P0001';
  end if;

  select * into regla from app.transicion_permitida
  where origen = a.estado and destino = p_destino and actor_tipo = p_actor_tipo;
  if not found then
    raise exception 'TRANSICION_NO_PERMITIDA: % → % por %', a.estado, p_destino, p_actor_tipo using errcode = 'P0001';
  end if;
  if regla.requiere_motivo and meta.limpiar(p_motivo) is null then
    raise exception 'MOTIVO_OBLIGATORIO: % → %', a.estado, p_destino using errcode = 'P0001';
  end if;

  if p_actor_tipo = 'USUARIO' then
    if not exists (select 1 from app.usuario_rol r join app.usuario u on u.id = r.usuario_id
                   where u.id = p_actor::bigint and u.activo and r.rol = any (regla.roles)) then
      raise exception 'ROL_INSUFICIENTE: se requiere uno de %', regla.roles using errcode = '42501';
    end if;
    if regla.prohibe_mismo_usuario then
      select b.actor into envio from audit.bitacora_articulo b
      where b.articulo_id = a.id and b.tipo = 'TRANSICION' and b.estado_destino = 'POR_VALIDAR'
      order by b.id desc limit 1;
      if envio = p_actor then
        raise exception 'DOBLE_CONTROL: quien envió a revisión no puede validar ni rechazar' using errcode = 'P0001';
      end if;
    end if;
  end if;

  if p_destino = 'POR_VALIDAR' then
    faltan := app.fn_requisitos_por_validar(a.id);
    if cardinality(faltan) > 0 then
      raise exception 'REQUISITOS_INCOMPLETOS: %', array_to_string(faltan, ', ') using errcode = 'P0001';
    end if;
  end if;

  update app.articulo
  set estado = p_destino, version = version + 1, asignado_a = null, asignado_hasta = null, actualizado_en = now()
  where id = a.id
  returning * into a;

  insert into audit.bitacora_articulo (articulo_id, tipo, estado_origen, estado_destino, actor_tipo, actor, motivo, detalle)
  values (a.id, 'TRANSICION', regla.origen, p_destino, p_actor_tipo, p_actor, meta.limpiar(p_motivo), p_detalle);

  return a;
end $$;

------------------------------------------------------------------------------------------
-- Reserva con "Siguiente" (30 min renovables) — segura con varios usuarios a la vez
------------------------------------------------------------------------------------------
create function app.fn_tomar_siguiente(
  p_usuario_id   bigint,
  p_estados      app.estado_articulo[],
  p_categoria_id smallint,
  p_linea        app.linea,
  p_minutos      integer default 30
) returns app.articulo
language plpgsql as $$
declare a app.articulo;
begin
  -- Si ya tiene uno reservado y vigente en esa bandeja, se lo devuelve.
  select * into a from app.articulo
  where asignado_a = p_usuario_id and asignado_hasta > now() and activo and estado = any (p_estados)
    and categoria_id = p_categoria_id and linea = p_linea
  limit 1;
  if found then return a; end if;

  update app.articulo set asignado_a = p_usuario_id, asignado_hasta = now() + make_interval(mins => p_minutos)
  where id = (
    select id from app.articulo
    where activo and estado = any (p_estados) and categoria_id = p_categoria_id and linea = p_linea
      and (asignado_hasta is null or asignado_hasta < now())
    order by actualizado_en, id
    for update skip locked
    limit 1
  )
  returning * into a;
  return a;  -- null si la bandeja está vacía
end $$;

------------------------------------------------------------------------------------------
-- Normalización y procesamiento de staging (ADR 0006, 0007, 0008)
------------------------------------------------------------------------------------------
create view staging.v_articulo_normalizado as
select b.*,
  -- Valores que SAP trae pero no se reconocen: quedan en null y se reportan (hallazgo VALOR_NO_RECONOCIDO)
  jsonb_strip_nulls(jsonb_build_object(
    'U_transmision',     case when b.transmision is null then meta.limpiar(b.r_transmision) end,
    'U_Tamanio',         case when b.tamano_panal is null then meta.limpiar(b.r_tamano) end,
    'U_FlowType',        case when b.tipo_flujo is null then meta.limpiar(b.r_tipo_flujo) end,
    'U_InletLocation',   case when b.entrada_ubicacion is null then meta.limpiar(b.r_entrada_ubicacion) end,
    'U_OutletLocation',  case when b.salida_ubicacion is null then meta.limpiar(b.r_salida_ubicacion) end,
    'U_CapIncluded',     case when b.incluye_tapon is null then meta.limpiar(b.r_tapon) end,
    'U_ThermostatIncluded', case when b.incluye_termostato is null then meta.limpiar(b.r_termostato) end,
    'U_TransmissionOilCoolerIncluded', case when b.incluye_enfriador_transmision is null then meta.limpiar(b.r_enfriador) end,
    'SHght1Unit',        case when b.panal_alto_mm is null and b.r_alto <> 0 then coalesce(b.r_alto_unidad::text, '(vacía)') end,
    'SLen1Unit',         case when b.panal_largo_mm is null and b.r_largo <> 0 then coalesce(b.r_largo_unidad::text, '(vacía)') end,
    'SWdth1Unit',        case when b.panal_ancho_mm is null and b.r_ancho <> 0 then coalesce(b.r_ancho_unidad::text, '(vacía)') end,
    'U_Linea',           case when not b.modelo_valido then b.modelo_vehiculo_codigo::text end
  )) as no_reconocidos
from (
select
  s.lote_id,
  upper(meta.limpiar(s.item_code))                         as item_code,
  meta.limpiar(s.descripcion)                              as descripcion,
  c.id                                                     as categoria_id,
  meta.limpiar(s.categoria_codigo)                         as categoria_codigo,
  meta.limpiar(s.subcategoria_codigo)                      as subcategoria_codigo,
  case upper(meta.limpiar(s.subcategoria_nombre)) when 'IMPORTADOS' then 'IMPORTADO'::app.linea
                                                  when 'FABRICADOS' then 'FABRICADO'::app.linea end as linea,
  c.part_terminology_id_defecto                            as part_terminology_id,
  meta.limpiar(s.material_codigo)                          as material_codigo,
  meta.limpiar(s.material_descripcion)                     as material_descripcion,
  upper(meta.limpiar(s.numero_parte_proveedor))            as numero_parte_proveedor,
  (select array_agg(meta.limpiar(x)) filter (where meta.limpiar(x) is not null)
   from unnest(string_to_array(s.codigo_anterior, ',')) x) as codigo_anterior,
  m.marca_codigo                                           as marca_vehiculo_codigo,
  m.nombre                                                 as marca_vehiculo,
  s.modelo_vehiculo_codigo,
  upper(meta.limpiar(s.modelo_vehiculo))                   as modelo_vehiculo,
  nullif(s.anio_desde, 0)::smallint                        as anio_desde,
  nullif(s.anio_hasta, 0)::smallint                        as anio_hasta,
  meta.limpiar(s.motor)                                    as motor,
  meta.limpiar(s.cilindrada)                               as cilindrada,
  case upper(meta.limpiar(s.transmision)) when 'AT' then 'AUTOMATICA'::app.transmision
                                          when 'MT' then 'MANUAL'::app.transmision end as transmision,
  round(nullif(s.panal_alto, 0)    * ua.factor_mm, 2)      as panal_alto_mm,
  round(nullif(s.panal_largo, 0)   * ul.factor_mm, 2)      as panal_largo_mm,
  round(nullif(s.panal_ancho, 0) * ue.factor_mm, 2)      as panal_ancho_mm,
  case when upper(meta.limpiar(s.tamano_panal)) in ('P', 'PEQUEÑO', 'PEQUENO') then 'PEQUENO'::app.tamano_panal
       when upper(meta.limpiar(s.tamano_panal)) in ('M', 'MEDIANO') then 'MEDIANO'::app.tamano_panal
       when upper(meta.limpiar(s.tamano_panal)) in ('G', 'GRANDE') then 'GRANDE'::app.tamano_panal end as tamano_panal,
  nullif(s.filas_panal, 0)::smallint                       as filas_panal,
  nullif(meta.limpiar(s.tipo_panal), '0')                              as tipo_panal,
  nullif(meta.limpiar(s.material_panal), '0')                          as material_panal,
  nullif(meta.limpiar(s.material_tanque), '0')                         as material_tanque,
  nullif(meta.limpiar(s.dimension_tanque), '0')                        as dimension_tanque,
  case meta.limpiar(s.tipo_flujo) when 'Cross Flow' then 'HORIZONTAL'::app.tipo_flujo
                                  when 'Down Flow' then 'VERTICAL'::app.tipo_flujo end as tipo_flujo,
  nullif(meta.limpiar(s.entrada_diametro), '0')                        as entrada_diametro,
  vi.valor_canonico                                        as entrada_ubicacion,
  nullif(meta.limpiar(s.salida_diametro), '0')                         as salida_diametro,
  vo.valor_canonico                                        as salida_ubicacion,
  case upper(meta.limpiar(s.incluye_tapon)) when 'S' then true when 'N' then false end                 as incluye_tapon,
  case upper(meta.limpiar(s.incluye_termostato)) when 'S' then true when 'N' then false end            as incluye_termostato,
  case upper(meta.limpiar(s.incluye_enfriador_transmision)) when 'S' then true when 'N' then false end as incluye_enfriador_transmision,
  meta.limpiar(s.material_principal)                       as material_principal,
  meta.limpiar(s.material_secundario)                      as material_secundario,
  meta.limpiar(s.material_otro)                            as material_otro,
  meta.limpiar(s.composicion_material)                     as composicion_material,
  meta.limpiar(s.autocare_id_sap)                          as autocare_id_sap,
  s.datos_sap,
  -- Auxiliares (no van a app.articulo tal cual)
  meta.limpiar(s.marca_vehiculo_codigo)                    as marca_sap_original,
  (c.id is not null and c.activa
   and upper(meta.limpiar(s.subcategoria_nombre)) in ('IMPORTADOS', 'FABRICADOS')) as en_alcance,
  upper(coalesce(meta.limpiar(s.congelado_sap), 'N')) = 'Y' as congelado,
  coalesce(s.descripcion, '') ilike '%INACTIV%'            as nombre_inactivo,
  nullif(s.anio_desde, 0) > nullif(s.anio_hasta, 0)        as anios_invertidos,
  coalesce(m.marca_codigo is null or s.modelo_vehiculo_codigo is null or exists (
    select 1 from staging.sap_modelo sm where sm.marca_codigo = m.marca_codigo and sm.modelo_codigo = s.modelo_vehiculo_codigo), true) as modelo_valido,
  s.transmision as r_transmision, s.tamano_panal as r_tamano, s.tipo_flujo as r_tipo_flujo,
  s.entrada_ubicacion as r_entrada_ubicacion, s.salida_ubicacion as r_salida_ubicacion, s.incluye_tapon as r_tapon,
  s.incluye_termostato as r_termostato, s.incluye_enfriador_transmision as r_enfriador,
  s.panal_alto as r_alto, s.panal_alto_unidad as r_alto_unidad, s.panal_largo as r_largo, s.panal_largo_unidad as r_largo_unidad,
  s.panal_ancho as r_ancho, s.panal_ancho_unidad as r_ancho_unidad
from staging.articulo_sap s
left join app.categoria c on c.codigo_sap = meta.limpiar(s.categoria_codigo)
left join staging.sap_marca m
  on m.marca_codigo = case when meta.limpiar(s.marca_vehiculo_codigo) ~ '^[0-9]+$'
                           then lpad(meta.limpiar(s.marca_vehiculo_codigo), 5, '0')
                           else meta.limpiar(s.marca_vehiculo_codigo) end
 and m.marca_codigo not in (select marca_codigo from meta.marca_sap_invalida)
left join meta.unidad_longitud ua on ua.codigo_sap = s.panal_alto_unidad
left join meta.unidad_longitud ul on ul.codigo_sap = s.panal_largo_unidad
left join meta.unidad_longitud ue on ue.codigo_sap = s.panal_ancho_unidad
left join meta.valor_lista_sap vi on vi.campo_sap = 'U_InletLocation'  and vi.valor_sap = meta.limpiar(s.entrada_ubicacion)
left join meta.valor_lista_sap vo on vo.campo_sap = 'U_OutletLocation' and vo.valor_sap = meta.limpiar(s.salida_ubicacion)
) b;

-- hash_control: sha256 de las columnas con en_hash, en orden_hash, separadas por U+001F; null → ''.
create function app.fn_hash_control(fila jsonb) returns text language sql stable as $$
  select encode(sha256(convert_to(string_agg(coalesce(fila ->> d.columna, ''), chr(31) order by d.orden_hash), 'UTF8')), 'hex')
  from meta.diccionario_campo d
  where d.esquema = 'app' and d.tabla = 'articulo' and d.en_hash
$$;

create function app.fn_procesar_staging(p_lote_id bigint) returns jsonb
language plpgsql as $$
declare
  n           record;
  a           app.articulo;
  fila        jsonb;
  v_hash      text;
  v_activo    boolean;
  v_motivo    app.motivo_inactivo;
  cambios     jsonb;
  v_old_activo boolean;
  res         jsonb := '{"nuevos":0,"actualizados":0,"sin_cambios":0,"reabiertos":0,"inactivados":0,"activados":0,"descartados":0}';
  cols        text[];
begin
  select array_agg(columna order by columna) into cols
  from meta.diccionario_campo where esquema = 'app' and tabla = 'articulo' and en_hash;

  for n in select * from staging.v_articulo_normalizado where lote_id = p_lote_id loop
    fila   := to_jsonb(n);
    v_hash := app.fn_hash_control(fila);
    v_motivo := case when not n.en_alcance then 'FUERA_DE_ALCANCE'
                     when n.congelado then 'SAP_CONGELADO'
                     when n.nombre_inactivo then 'NOMBRE_INACTIVO' end;
    v_activo := v_motivo is null;

    select * into a from app.articulo where item_code = n.item_code for update;
    v_old_activo := a.activo;

    if not found then
      if not n.en_alcance then                      -- defensa: el ETL no debería enviarlo
        res := jsonb_set(res, '{descartados}', to_jsonb((res->>'descartados')::int + 1));
        continue;
      end if;
      insert into app.articulo (item_code, descripcion, categoria_id, categoria_codigo, subcategoria_codigo, linea, part_terminology_id,
        material_codigo, material_descripcion, numero_parte_proveedor, codigo_anterior, marca_vehiculo_codigo, marca_vehiculo,
        modelo_vehiculo_codigo, modelo_vehiculo, anio_desde, anio_hasta, motor, cilindrada, transmision, panal_alto_mm, panal_largo_mm,
        panal_ancho_mm, tamano_panal, filas_panal, tipo_panal, material_panal, material_tanque, dimension_tanque, tipo_flujo,
        entrada_diametro, entrada_ubicacion, salida_diametro, salida_ubicacion, incluye_tapon, incluye_termostato,
        incluye_enfriador_transmision, material_principal, material_secundario, material_otro, composicion_material, autocare_id_sap,
        hash_control, activo, motivo_inactivo, datos_sap, ultimo_lote_id)
      values (n.item_code, n.descripcion, n.categoria_id, n.categoria_codigo, n.subcategoria_codigo, n.linea, n.part_terminology_id,
        n.material_codigo, n.material_descripcion, n.numero_parte_proveedor, n.codigo_anterior, n.marca_vehiculo_codigo, n.marca_vehiculo,
        n.modelo_vehiculo_codigo, n.modelo_vehiculo, n.anio_desde, n.anio_hasta, n.motor, n.cilindrada, n.transmision, n.panal_alto_mm,
        n.panal_largo_mm, n.panal_ancho_mm, n.tamano_panal, n.filas_panal, n.tipo_panal, n.material_panal, n.material_tanque,
        n.dimension_tanque, n.tipo_flujo, n.entrada_diametro, n.entrada_ubicacion, n.salida_diametro, n.salida_ubicacion, n.incluye_tapon,
        n.incluye_termostato, n.incluye_enfriador_transmision, n.material_principal, n.material_secundario, n.material_otro,
        n.composicion_material, n.autocare_id_sap, v_hash, v_activo, v_motivo, n.datos_sap, p_lote_id)
      returning * into a;
      insert into audit.bitacora_articulo (articulo_id, tipo, estado_destino, actor_tipo, actor, motivo)
      values (a.id, 'ALTA', 'PENDIENTE', 'PROCESO', 'PROCESO:ETL', 'Lote ' || p_lote_id);
      res := jsonb_set(res, '{nuevos}', to_jsonb((res->>'nuevos')::int + 1));

    elsif a.hash_control <> v_hash then
      -- Qué columnas cambiaron (para mostrarlo al operador)
      select jsonb_object_agg(c, jsonb_build_object('antes', to_jsonb(a) -> c, 'despues', fila -> c))
      into cambios
      from unnest(cols) c where (to_jsonb(a) -> c) is distinct from (fila -> c);

      update app.articulo set
        descripcion = n.descripcion, categoria_id = n.categoria_id, categoria_codigo = n.categoria_codigo,
        subcategoria_codigo = n.subcategoria_codigo, linea = coalesce(n.linea, linea),
        material_codigo = n.material_codigo, material_descripcion = n.material_descripcion,
        numero_parte_proveedor = n.numero_parte_proveedor, codigo_anterior = n.codigo_anterior,
        marca_vehiculo_codigo = n.marca_vehiculo_codigo, marca_vehiculo = n.marca_vehiculo,
        modelo_vehiculo_codigo = n.modelo_vehiculo_codigo, modelo_vehiculo = n.modelo_vehiculo, anio_desde = n.anio_desde,
        anio_hasta = n.anio_hasta, motor = n.motor, cilindrada = n.cilindrada, transmision = n.transmision,
        panal_alto_mm = n.panal_alto_mm, panal_largo_mm = n.panal_largo_mm, panal_ancho_mm = n.panal_ancho_mm,
        tamano_panal = n.tamano_panal, filas_panal = n.filas_panal, tipo_panal = n.tipo_panal, material_panal = n.material_panal,
        material_tanque = n.material_tanque, dimension_tanque = n.dimension_tanque, tipo_flujo = n.tipo_flujo,
        entrada_diametro = n.entrada_diametro, entrada_ubicacion = n.entrada_ubicacion, salida_diametro = n.salida_diametro,
        salida_ubicacion = n.salida_ubicacion, incluye_tapon = n.incluye_tapon, incluye_termostato = n.incluye_termostato,
        incluye_enfriador_transmision = n.incluye_enfriador_transmision, material_principal = n.material_principal,
        material_secundario = n.material_secundario, material_otro = n.material_otro,
        composicion_material = n.composicion_material, autocare_id_sap = n.autocare_id_sap,
        hash_control = v_hash, datos_sap = n.datos_sap, ultimo_lote_id = p_lote_id,
        activo = v_activo, motivo_inactivo = v_motivo,
        version = version + 1, actualizado_en = now()
      where id = a.id
      returning * into a;

      insert into audit.bitacora_articulo (articulo_id, tipo, actor_tipo, actor, motivo, detalle)
      values (a.id, 'DATOS_SAP', 'PROCESO', 'PROCESO:ETL', 'Lote ' || p_lote_id, cambios);

      if a.estado in ('VALIDADO', 'SINCRONIZADO') and v_activo then  -- fuera de alcance o inactivo: no se reabre
        perform app.fn_transicionar(a.id, 'PENDIENTE', 'PROCESO', 'PROCESO:ETL', 'HASH_CAMBIO', cambios);
        res := jsonb_set(res, '{reabiertos}', to_jsonb((res->>'reabiertos')::int + 1));
      end if;
      res := jsonb_set(res, '{actualizados}', to_jsonb((res->>'actualizados')::int + 1));
    else
      update app.articulo set ultimo_lote_id = p_lote_id, activo = v_activo, motivo_inactivo = v_motivo
      where id = a.id returning * into a;
      res := jsonb_set(res, '{sin_cambios}', to_jsonb((res->>'sin_cambios')::int + 1));
    end if;

    -- Inactivos (ADR 0008): ya se aplicó arriba; aquí se registra el cambio y se libera la reserva.
    if v_old_activo is not null and v_old_activo <> v_activo then
      update app.articulo set asignado_a = null, asignado_hasta = null where id = a.id and not v_activo;
      begin
        insert into audit.bitacora_articulo (articulo_id, tipo, actor_tipo, actor, motivo)
        values (a.id, case when v_activo then 'ACTIVADO'::audit.tipo_evento else 'INACTIVADO' end,
                'PROCESO', 'PROCESO:ETL', coalesce(v_motivo::text, 'REACTIVADO'));
        res := jsonb_set(res, case when v_activo then '{activados}' else '{inactivados}' end::text[],
                         to_jsonb((res->>(case when v_activo then 'activados' else 'inactivados' end))::int + 1));
      end;
    end if;

    -- Calidad SAP (se corrige en SAP, no aquí)
    if n.marca_sap_original is not null and n.marca_vehiculo_codigo is null then
      insert into app.hallazgo_calidad_sap (articulo_id, tipo, campo_sap, valor)
      values (a.id, 'MARCA_INVALIDA', 'U_Marca', n.marca_sap_original) on conflict do nothing;
    else
      update app.hallazgo_calidad_sap set corregido_en = now()
      where articulo_id = a.id and tipo = 'MARCA_INVALIDA' and corregido_en is null;
    end if;
    if n.nombre_inactivo and not n.congelado then
      insert into app.hallazgo_calidad_sap (articulo_id, tipo, campo_sap, valor)
      values (a.id, 'NOMBRE_INACTIVO_SIN_CONGELAR', 'frozenFor', n.descripcion) on conflict do nothing;
    end if;
    if n.anios_invertidos then
      insert into app.hallazgo_calidad_sap (articulo_id, tipo, campo_sap, valor)
      values (a.id, 'ANIOS_INVERTIDOS', 'U_anio1', n.anio_desde || ' > ' || n.anio_hasta) on conflict do nothing;
    else
      update app.hallazgo_calidad_sap set corregido_en = now()
      where articulo_id = a.id and tipo = 'ANIOS_INVERTIDOS' and corregido_en is null;
    end if;
    insert into app.hallazgo_calidad_sap (articulo_id, tipo, campo_sap, valor)
    select a.id, 'VALOR_NO_RECONOCIDO', k, v from jsonb_each_text(n.no_reconocidos) as x(k, v) on conflict do nothing;
    update app.hallazgo_calidad_sap set corregido_en = now()
    where articulo_id = a.id and tipo = 'VALOR_NO_RECONOCIDO' and corregido_en is null and not n.no_reconocidos ? campo_sap;
  end loop;

  update staging.lote set procesado_en = now(), resultado = res where lote_id = p_lote_id;
  return res;
end $$;

comment on function app.fn_procesar_staging is 'La llama el ETL después de cargar staging (contrato, ADR 0006). Única vía de alta/actualización de artículos.';
comment on function app.fn_transicionar is 'Única vía para cambiar el estado de un artículo (ADR 0012). Valida reglas, roles, motivo y doble control.';
