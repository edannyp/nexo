-- Nexo 0004 · Catálogo configurable de atributos PIES por tipo de parte (ADR 0019)
-- Reemplaza meta.atributo_requerido y meta.atributo_desde_sap (0002). db/ref/cargar_ref.py carga desde PAdb TODOS los atributos de
-- los tipos de parte en alcance (deshabilitados); un administrador decide cuáles se usan (habilitado), cuáles bloquean POR_VALIDAR
-- (obligatorio), su etiqueta y de qué campo de SAP se precargan. Aquí se siembra la ficha del radiador que usa el negocio.

create type meta.conversion_sap as enum ('NUMERO', 'NUMERO_EN_TEXTO', 'LISTA', 'TEXTO', 'PARTE_DE_MEDIDA');
create type meta.grupo_atributo as enum ('MEDIDAS', 'MATERIALES', 'CONSTRUCCION', 'CONEXIONES', 'INCLUYE', 'OTROS');

create table meta.atributo_config (
  part_terminology_id integer not null,
  paid                integer not null,
  nombre              text not null,                     -- PAdb (inglés); lo actualiza la carga de AutoCare
  requiere_uom        boolean not null default false,    -- PAdb: el valor numérico lleva unidad
  -- Configuración (la carga de AutoCare nunca la modifica)
  habilitado          boolean not null default false,
  obligatorio         boolean not null default false,
  etiqueta            text,                              -- nombre en el vocabulario del negocio; si es null, la APP muestra `nombre`
  grupo               meta.grupo_atributo not null default 'OTROS',
  orden               smallint,
  uom_defecto         text,
  columna_sap         text,                              -- columna de app.articulo que se precarga como sugerencia
  conversion          meta.conversion_sap,
  parte               smallint check (parte in (1, 2)),  -- PARTE_DE_MEDIDA: 1 = antes del '*', 2 = después
  actualizado_en      timestamptz not null default now(),
  primary key (part_terminology_id, paid),
  check (not obligatorio or habilitado),
  check ((columna_sap is null) = (conversion is null)),
  check ((conversion = 'PARTE_DE_MEDIDA') = (parte is not null))
);
comment on table meta.atributo_config is 'Catálogo de atributos PIES por tipo de parte y su uso en la APP (ADR 0019). Se configura sin migración.';
comment on column meta.atributo_config.habilitado is 'El atributo se carga y se usa en la APP. Solo se capturan atributos habilitados.';
comment on column meta.atributo_config.obligatorio is 'Bloquea el envío a POR_VALIDAR hasta que el operador lo confirme.';

create table meta.atributo_valor_permitido (           -- valores válidos de PAdb (listas desplegables y validación)
  part_terminology_id integer not null,
  paid                integer not null,
  valid_value_id      integer not null,
  valor               text not null,
  primary key (part_terminology_id, paid, valid_value_id),
  foreign key (part_terminology_id, paid) references meta.atributo_config
);

-- Valor de SAP (ya normalizado en app.articulo) → valor válido de PAdb; se compara en mayúsculas
create table meta.valor_sap_pies (
  paid           integer not null,
  valor_sap      text not null,
  valid_value_id integer not null,
  valor_pies     text not null,
  primary key (paid, valor_sap)
);

-- Ficha del radiador (2172) que usa el negocio. Los datos propios de la empresa van en el atributo PIES donde encajan.
insert into meta.atributo_config
  (part_terminology_id, paid, nombre, requiere_uom, habilitado, obligatorio, etiqueta, grupo, orden, uom_defecto, columna_sap, conversion, parte)
values
  (2172, 267,  'Core Height',                  true,  true, true, 'Alto',             'MEDIDAS',      1,  'MM', 'panal_alto_mm',    'NUMERO',          null),
  (2172, 269,  'Core Width',                   true,  true, true, 'Largo',            'MEDIDAS',      2,  'MM', 'panal_largo_mm',   'NUMERO',          null),
  (2172, 268,  'Core Thickness',               true,  true, true, 'Ancho',            'MEDIDAS',      3,  'MM', 'panal_ancho_mm',   'NUMERO',          null),
  (2172, 5061, 'Core Row Quantity',            false, true, true, 'Filas',            'CONSTRUCCION', 4,  null, 'filas_panal',      'NUMERO',          null),
  (2172, 3664, 'Core Type',                    false, true, true, 'Tipo de panal',    'CONSTRUCCION', 5,  null, 'tipo_panal',       'TEXTO',           null),
  (2172, 7448, 'Down Flow Or Cross Flow Type', false, true, true, 'Tipo flujo',       'CONSTRUCCION', 6,  null, 'tipo_flujo',       'LISTA',           null),
  (2172, 302,  'Core Material',                false, true, true, 'Material panal',   'MATERIALES',   7,  null, 'material_panal',   'LISTA',           null),
  (2172, 305,  'Tank Material',                false, true, true, 'Material tanque',  'MATERIALES',   8,  null, 'material_tanque',  'LISTA',           null),
  (2172, 270,  'Inlet Header Length',          true,  true, true, 'Largo tanque',     'MEDIDAS',      9,  'MM', 'dimension_tanque', 'PARTE_DE_MEDIDA', 1),
  (2172, 316,  'Inlet Header Width',           true,  true, true, 'Ancho tanque',     'MEDIDAS',      10, 'MM', 'dimension_tanque', 'PARTE_DE_MEDIDA', 2),
  (2172, 570,  'Inlet Diameter',               true,  true, true, 'Diámetro entrada', 'CONEXIONES',   11, 'MM', 'entrada_diametro', 'NUMERO_EN_TEXTO', null);

insert into meta.atributo_valor_permitido values
  (2172, 302, 203, 'Aluminum'), (2172, 302, 381, 'Copper'),
  (2172, 305, 203, 'Aluminum'), (2172, 305, 287, 'Brass'), (2172, 305, 381, 'Copper'), (2172, 305, 890, 'Plastic'), (2172, 305, 1150, 'Steel'),
  (2172, 7448, 391, 'Cross Flow'), (2172, 7448, 444, 'Down Flow');

insert into meta.valor_sap_pies values
  (302,  'ALUMINUM', 203, 'Aluminum'),  (302,  'ALUMINIO', 203, 'Aluminum'),
  (302,  'COBRE',    381, 'Copper'),    (302,  'COPPER',   381, 'Copper'),
  (305,  'PLASTIC',  890, 'Plastic'),   (305,  'PLASTICO', 890, 'Plastic'),
  (305,  'ALUMINUM', 203, 'Aluminum'),  (305,  'ALUMINIO', 203, 'Aluminum'),
  (305,  'LATON',    287, 'Brass'),     (305,  'BRASS',    287, 'Brass'),
  (305,  'COBRE',    381, 'Copper'),    (305,  'COPPER',   381, 'Copper'),
  (7448, 'HORIZONTAL', 391, 'Cross Flow'), (7448, 'VERTICAL', 444, 'Down Flow');

-- Los cambios de configuración quedan auditados (quién habilitó u obligó qué)
create trigger auditoria after insert or update or delete on meta.atributo_config
  for each row execute function audit.registrar();

-- El catálogo reemplaza a las tablas fijas de 0002
drop table meta.atributo_requerido;
drop table meta.atributo_desde_sap;

------------------------------------------------------------------------------------------
-- Validación: solo atributos habilitados para el tipo de parte del artículo, con valor y unidad válidos
------------------------------------------------------------------------------------------
create function app.validar_articulo_atributo() returns trigger language plpgsql as $$
declare cfg meta.atributo_config; pt integer;
begin
  select part_terminology_id into pt from app.articulo where id = new.articulo_id;
  select * into cfg from meta.atributo_config where part_terminology_id = pt and paid = new.paid;
  if not found or not cfg.habilitado then
    raise exception 'ATRIBUTO_NO_HABILITADO: el atributo % no está habilitado para el tipo de parte %', new.paid, pt using errcode = 'P0001';
  end if;
  if new.valid_value_id is not null and not exists (
       select 1 from meta.atributo_valor_permitido v
       where v.part_terminology_id = pt and v.paid = new.paid and v.valid_value_id = new.valid_value_id) then
    raise exception 'VALOR_NO_VALIDO: % no es un valor válido de PAdb para el atributo %', new.valid_value_id, new.paid using errcode = 'P0001';
  end if;
  if new.valor_num is not null and cfg.requiere_uom and new.uom_code is null then
    raise exception 'REQUIERE_UOM: el atributo % requiere unidad', new.paid using errcode = 'P0001';
  end if;
  return new;
end $$;

create trigger validar before insert or update of paid, valor_num, uom_code, valid_value_id on app.articulo_atributo
  for each row execute function app.validar_articulo_atributo();

------------------------------------------------------------------------------------------
-- Precarga desde SAP (sugerencias). Solo atributos habilitados; lo que no se puede convertir lo captura el operador.
------------------------------------------------------------------------------------------
create function meta.numero(p text) returns numeric language sql immutable as $$
  select replace(p, ',', '.')::numeric                     -- coma o punto decimal
$$;

create or replace function app.fn_precargar_atributos_sap(p_articulo_id bigint) returns integer
language plpgsql as $$
declare
  r record; v text; n integer := 0; pt integer; num numeric; vv integer; txt text;
  re_num constant text := '([0-9]+(?:[.,][0-9]+)?)\s*(?:mm)?';
begin
  select part_terminology_id into pt from app.articulo where id = p_articulo_id;
  for r in select * from meta.atributo_config where part_terminology_id = pt and habilitado and columna_sap is not null loop
    execute format('select %I::text from app.articulo where id = $1', r.columna_sap) into v using p_articulo_id;
    continue when v is null;
    num := null; vv := null; txt := null;
    case r.conversion
      when 'NUMERO' then
        num := v::numeric;
      when 'NUMERO_EN_TEXTO' then                          -- '35mm', '35 MM', '35,5'; con varios ('33mm 40mm') no se precarga
        num := meta.numero((regexp_match(v, '^\s*' || re_num || '\s*$', 'i'))[1]);
      when 'PARTE_DE_MEDIDA' then                          -- '545*54.5', '545 x 54,5'; con dos anchos ('756*33/48') no se precarga
        num := meta.numero((regexp_match(v, '^\s*' || re_num || '\s*[*xX×]\s*' || re_num || '\s*$', 'i'))[r.parte]);
      when 'TEXTO' then
        txt := v;
      when 'LISTA' then
        select valid_value_id into vv from meta.valor_sap_pies where paid = r.paid and valor_sap = upper(v);
    end case;
    continue when num is null and vv is null and txt is null;
    insert into app.articulo_atributo (articulo_id, paid, valor_num, uom_code, valid_value_id, valor_texto, origen)
    values (p_articulo_id, r.paid, num, case when num is not null then r.uom_defecto end, vv, txt, 'SAP')
    on conflict (articulo_id, paid) do nothing;
    if found then n := n + 1; end if;
  end loop;
  return n;
end $$;

------------------------------------------------------------------------------------------
-- Requisitos para POR_VALIDAR: atributos habilitados y obligatorios del catálogo
------------------------------------------------------------------------------------------
create or replace function app.fn_requisitos_por_validar(p_articulo_id bigint) returns text[]
language sql stable as $$
  select array_remove(
    array[
      case when a.part_terminology_id is null then 'TIPO_DE_PARTE' end,
      case when not exists (select 1 from app.articulo_aplicacion x where x.articulo_id = a.id and x.confirmado_por is not null)
            and not exists (select 1 from app.articulo_parte x where x.articulo_id = a.id)
           then 'APLICACION_O_EMPAREJAMIENTO' end
    ]
    || coalesce((select array_agg('ATRIBUTO:' || r.nombre order by r.orden nulls last, r.paid)
                 from meta.atributo_config r
                 where r.part_terminology_id = a.part_terminology_id and r.habilitado and r.obligatorio
                   and not exists (select 1 from app.articulo_atributo t
                                   where t.articulo_id = a.id and t.paid = r.paid and t.confirmado_por is not null)), '{}'),
    null)
  from app.articulo a where a.id = p_articulo_id
$$;

-- Ficha que arma la APP: atributos habilitados del tipo de parte, en orden, con el valor del artículo si lo tiene
create view app.v_ficha_atributo as
select a.id as articulo_id, c.paid, coalesce(c.etiqueta, c.nombre) as etiqueta, c.nombre as nombre_pies, c.grupo, c.orden,
       c.obligatorio, c.requiere_uom, c.uom_defecto,
       t.valor_num, t.uom_code, t.valid_value_id, v.valor as valor_lista, t.valor_texto, t.origen,
       t.confirmado_por is not null as confirmado
from app.articulo a
join meta.atributo_config c on c.part_terminology_id = a.part_terminology_id and c.habilitado
left join app.articulo_atributo t on t.articulo_id = a.id and t.paid = c.paid
left join meta.atributo_valor_permitido v
  on v.part_terminology_id = c.part_terminology_id and v.paid = c.paid and v.valid_value_id = t.valid_value_id;
