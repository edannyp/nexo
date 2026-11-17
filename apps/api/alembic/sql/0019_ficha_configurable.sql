-- Nexo 0019 · Ficha configurable desde la consola y campos propios de Nexo (ADR 0029)
-- El catálogo de atributos por tipo de parte (ADR 0019) se configura desde la consola, con el permiso especial CONFIGURAR_FICHA.
-- Además de los atributos de AutoCare (PAdb), se pueden crear campos PROPIOS que AutoCare no tiene: número con unidad, lista de
-- opciones, texto libre o sí/no. Sus códigos (paid y valid_value_id) empiezan en 1 000 000 para no chocar nunca con AutoCare, y
-- la carga de AutoCare no los toca. Por ahora solo viven en Nexo: no salen a otros sistemas.

alter type app.permiso add value if not exists 'CONFIGURAR_FICHA';
alter type meta.conversion_sap add value if not exists 'SI_NO';          -- S/N, Sí/No, Y/N, 1/0, true/false → SI o NO

create type meta.tipo_atributo as enum ('NUMERO', 'LISTA', 'TEXTO', 'SI_NO');
create sequence meta.codigo_propio start 1000000;
comment on sequence meta.codigo_propio is 'Códigos de los campos propios de Nexo y de sus opciones (desde 1 000 000; AutoCare usa menos).';

alter table meta.atributo_config
  add column tipo   meta.tipo_atributo,
  add column propio boolean generated always as (paid >= 1000000) stored,
  add constraint atributo_propio_con_tipo check (paid < 1000000 or tipo is not null),
  add constraint uom_solo_en_numeros check (not (requiere_uom and tipo is not null and tipo <> 'NUMERO'));
comment on column meta.atributo_config.tipo is
  'Tipo del campo propio (NUMERO, LISTA, TEXTO, SI_NO). En los de AutoCare queda null: el tipo sale de PAdb (unidad, valores válidos).';
comment on column meta.atributo_config.propio is 'Campo propio de Nexo (no existe en AutoCare): paid desde 1 000 000.';

alter table meta.atributo_valor_permitido
  add column propio boolean generated always as (valid_value_id >= 1000000) stored;
comment on table meta.atributo_valor_permitido is
  'Valores válidos por atributo: los de PAdb (en inglés) y las opciones de los campos propios (en español, desde 1 000 000).';

-- Toda la configuración queda auditada (quién cambió qué), como meta.atributo_config y meta.traduccion_valor
create trigger auditoria after insert or update or delete on meta.atributo_valor_permitido
  for each row execute function audit.registrar();
create trigger auditoria after insert or update or delete on meta.valor_sap_pies
  for each row execute function audit.registrar();

------------------------------------------------------------------------------------------
-- Validación: además de lo de 0014, el valor de un campo propio debe ser de su tipo
------------------------------------------------------------------------------------------
create or replace function app.validar_articulo_atributo() returns trigger language plpgsql as $$
declare cfg meta.atributo_config; pt integer; de_su_tipo boolean;
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
  de_su_tipo := case cfg.tipo
                  when 'NUMERO' then new.valor_num is not null
                  when 'LISTA'  then new.valid_value_id is not null
                  when 'TEXTO'  then new.valor_texto is not null
                  when 'SI_NO'  then coalesce(new.valor_texto in ('SI', 'NO'), false)
                  else true end;
  if not de_su_tipo then
    raise exception 'VALOR_NO_VALIDO: el campo % es de tipo %', coalesce(cfg.etiqueta, cfg.nombre), cfg.tipo using errcode = 'P0001';
  end if;
  if new.valid_value_id is not null and (tg_op = 'INSERT' or new.valid_value_id is distinct from old.valid_value_id) and not exists (
       select 1 from meta.atributo_valor_permitido v
       where v.part_terminology_id = pt and v.paid = new.paid and v.valid_value_id = new.valid_value_id and v.obsoleto_en is null) then
    raise exception 'VALOR_NO_VALIDO: % no es una opción válida para el atributo %', new.valid_value_id, new.paid using errcode = 'P0001';
  end if;
  if new.valor_num is not null and cfg.requiere_uom and new.uom_code is null then
    raise exception 'REQUIERE_UOM: el atributo % requiere unidad', new.paid using errcode = 'P0001';
  end if;
  return new;
end $$;

------------------------------------------------------------------------------------------
-- Precarga desde SAP: además de 0014, la conversión SI_NO (p. ej. incluye_tapon)
------------------------------------------------------------------------------------------
create or replace function app.fn_precargar_atributos_sap(p_articulo_id bigint) returns integer
language plpgsql as $$
declare
  r record; v text; n integer := 0; pt integer; num numeric; vv integer; txt text; de_su_tipo boolean;
  re_num constant text := '([0-9]+(?:[.,][0-9]+)?)\s*(?:mm)?';
begin
  select part_terminology_id into pt from app.articulo where id = p_articulo_id;
  for r in select * from meta.atributo_config
           where part_terminology_id = pt and habilitado and columna_sap is not null and obsoleto_en is null loop
    execute format('select %I::text from app.articulo where id = $1', r.columna_sap) into v using p_articulo_id;
    continue when v is null;
    num := null; vv := null; txt := null;
    begin
      case r.conversion::text
        when 'NUMERO' then
          num := v::numeric;
        when 'NUMERO_EN_TEXTO' then                        -- '35mm', '35 MM', '35,5'; con varios ('33mm 40mm') no se precarga
          num := meta.numero((regexp_match(v, '^\s*' || re_num || '\s*$', 'i'))[1]);
        when 'PARTE_DE_MEDIDA' then                        -- '545*54.5', '545 x 54,5'; con dos anchos ('756*33/48') no se precarga
          num := meta.numero((regexp_match(v, '^\s*' || re_num || '\s*[*xX×]\s*' || re_num || '\s*$', 'i'))[r.parte]);
        when 'TEXTO' then
          txt := v;
        when 'SI_NO' then
          txt := case when upper(btrim(v)) in ('S', 'SI', 'SÍ', 'Y', 'YES', '1', 'TRUE', 'T') then 'SI'
                      when upper(btrim(v)) in ('N', 'NO', '0', 'FALSE', 'F') then 'NO' end;
        when 'LISTA' then
          select s.valid_value_id into vv from meta.valor_sap_pies s
          join meta.atributo_valor_permitido x on x.part_terminology_id = pt and x.paid = s.paid and x.valid_value_id = s.valid_value_id
                                               and x.obsoleto_en is null
          where s.paid = r.paid and s.valor_sap = upper(v);
      end case;
    exception when invalid_text_representation then        -- una columna mal configurada no detiene la ficha
      continue;
    end;
    -- La precarga respeta el tipo del campo propio (una columna de texto no llena un número)
    de_su_tipo := case r.tipo::text
                    when 'NUMERO' then num is not null when 'LISTA' then vv is not null
                    when 'TEXTO' then txt is not null when 'SI_NO' then coalesce(txt in ('SI', 'NO'), false)
                    else true end;
    continue when not de_su_tipo;
    continue when num is null and vv is null and txt is null;
    insert into app.articulo_atributo (articulo_id, paid, valor_num, uom_code, valid_value_id, valor_texto, origen)
    values (p_articulo_id, r.paid, num, case when num is not null then r.uom_defecto end, vv, txt, 'SAP')
    on conflict (articulo_id, paid) do nothing;
    if found then n := n + 1; end if;
  end loop;
  return n;
end $$;
