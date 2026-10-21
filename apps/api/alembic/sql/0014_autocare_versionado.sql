-- Nexo 0014 · Copia de AutoCare versionada (ADR 0024)
-- La herramienta db/ref/cargar_ref.py compara cada carga con la anterior: marca como obsoleto lo que AutoCare quitó (nunca lo borra)
-- y guarda el historial con su impacto en Nexo. Lo obsoleto no se asigna de nuevo ni se exige; lo que un artículo ya tenía se conserva.

alter table meta.atributo_config add column obsoleto_en timestamptz;
alter table meta.atributo_valor_permitido add column obsoleto_en timestamptz;
comment on column meta.atributo_config.obsoleto_en is 'AutoCare ya no asigna este atributo al tipo de parte (desde esa fecha). No se borra.';
comment on column meta.atributo_valor_permitido.obsoleto_en is 'AutoCare ya no tiene este valor para el atributo (desde esa fecha). No se borra.';

create table meta.historial_referencia (
  id          bigint generated always as identity primary key,
  cargado_en  timestamptz not null default now(),
  versiones   jsonb not null,                  -- VCdb / PCdb / PAdb de AutoCare en esa carga
  tabla       text not null,
  altas       integer not null,
  cambios     integer not null,
  bajas       integer not null,                -- marcadas como obsoletas
  reactivados integer not null,                -- obsoletas que AutoCare volvió a publicar
  detalle     jsonb not null default '{}',     -- ejemplos por tipo de cambio
  impacto     jsonb not null default '{}'      -- lo que estaba en uso en Nexo
);
comment on table meta.historial_referencia is 'Cada carga de AutoCare (db/ref/cargar_ref.py nexo): qué cambió respecto a la anterior y su impacto (ADR 0024).';

create or replace function app.validar_articulo_atributo() returns trigger language plpgsql as $$
declare cfg meta.atributo_config; pt integer;
begin
  select part_terminology_id into pt from app.articulo where id = new.articulo_id;
  select * into cfg from meta.atributo_config where part_terminology_id = pt and paid = new.paid;
  if not found or not cfg.habilitado then
    raise exception 'ATRIBUTO_NO_HABILITADO: el atributo % no está habilitado para el tipo de parte %', new.paid, pt using errcode = 'P0001';
  end if;
  -- Lo que AutoCare quitó (obsoleto) no se asigna de nuevo; lo que el artículo ya tenía se conserva
  if cfg.obsoleto_en is not null and tg_op = 'INSERT' then
    raise exception 'ATRIBUTO_OBSOLETO: AutoCare ya no asigna el atributo % al tipo de parte %', new.paid, pt using errcode = 'P0001';
  end if;
  if new.valid_value_id is not null and (tg_op = 'INSERT' or new.valid_value_id is distinct from old.valid_value_id) and not exists (
       select 1 from meta.atributo_valor_permitido v
       where v.part_terminology_id = pt and v.paid = new.paid and v.valid_value_id = new.valid_value_id and v.obsoleto_en is null) then
    raise exception 'VALOR_NO_VALIDO: % no es un valor válido de PAdb para el atributo %', new.valid_value_id, new.paid using errcode = 'P0001';
  end if;
  if new.valor_num is not null and cfg.requiere_uom and new.uom_code is null then
    raise exception 'REQUIERE_UOM: el atributo % requiere unidad', new.paid using errcode = 'P0001';
  end if;
  return new;
end $$;

create or replace function app.fn_precargar_atributos_sap(p_articulo_id bigint) returns integer
language plpgsql as $$
declare
  r record; v text; n integer := 0; pt integer; num numeric; vv integer; txt text;
  re_num constant text := '([0-9]+(?:[.,][0-9]+)?)\s*(?:mm)?';
begin
  select part_terminology_id into pt from app.articulo where id = p_articulo_id;
  for r in select * from meta.atributo_config
           where part_terminology_id = pt and habilitado and columna_sap is not null and obsoleto_en is null loop
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
        select s.valid_value_id into vv from meta.valor_sap_pies s
        join meta.atributo_valor_permitido x on x.part_terminology_id = pt and x.paid = s.paid and x.valid_value_id = s.valid_value_id
                                             and x.obsoleto_en is null
        where s.paid = r.paid and s.valor_sap = upper(v);
    end case;
    continue when num is null and vv is null and txt is null;
    insert into app.articulo_atributo (articulo_id, paid, valor_num, uom_code, valid_value_id, valor_texto, origen)
    values (p_articulo_id, r.paid, num, case when num is not null then r.uom_defecto end, vv, txt, 'SAP')
    on conflict (articulo_id, paid) do nothing;
    if found then n := n + 1; end if;
  end loop;
  return n;
end $$;

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
                 where r.part_terminology_id = a.part_terminology_id and r.habilitado and r.obligatorio and r.obsoleto_en is null
                   and not exists (select 1 from app.articulo_atributo t
                                   where t.articulo_id = a.id and t.paid = r.paid and t.confirmado_por is not null)), '{}'),
    null)
  from app.articulo a where a.id = p_articulo_id
$$;
