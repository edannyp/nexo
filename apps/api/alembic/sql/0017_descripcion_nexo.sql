-- Nexo 0017 · Descripción armada por Nexo (ADR 0027)
-- Además de la descripción de SAP (que no se toca), cada artículo tiene una descripción estandarizada que Nexo arma con el patrón
-- de SAP sin abreviar: TIPO MARCA MODELO M AA/AA MOTOR TRANSMISIÓN (+ MATERIAL en fabricados), a partir del vehículo principal
-- (ADR 0025). Se recalcula sola cuando cambia lo que la forma, salvo que una persona la haya ajustado a mano.

alter table app.articulo
  add column descripcion_nexo        text check (length(descripcion_nexo) between 1 and 100),
  add column descripcion_nexo_manual boolean not null default false;
comment on column app.articulo.descripcion_nexo is
  'Descripción estandarizada de Nexo (ADR 0027). Automática salvo descripcion_nexo_manual; null si aún no hay vehículo principal.';

-- El motor del vehículo (texto del catálogo, p. ej. "2.5L L4 2KD · Diésel"), copiado como marca y modelo (0016)
alter table app.articulo_aplicacion add column motor text;

-- Texto en mayúsculas y sin acentos, como las descripciones de SAP
create function app.fn_texto_sap(t text) returns text language sql immutable as $$
  select nullif(btrim(regexp_replace(upper(translate(coalesce(t, ''), 'áéíóúàèìòùäëïöüñÁÉÍÓÚÀÈÌÒÙÄËÏÖÜÑ',
                                                     'aeiouaeiouaeiounAEIOUAEIOUAEIOUN')), '\s+', ' ', 'g')), '')
$$;

-- La descripción que corresponde hoy al artículo (null si no tiene vehículo principal con marca y modelo)
create function app.fn_descripcion_nexo(a app.articulo) returns text language plpgsql stable as $$
declare
  p record;
  v_tipo text; v_anios text; v_motor text; v_trans text; v_material text;
begin
  select min(x.marca) as marca, min(x.modelo) as modelo, min(x.anio) as desde, max(x.anio) as hasta, min(x.motor) as motor
  into p from app.articulo_aplicacion x
  where x.articulo_id = a.id and x.es_principal and x.equipment_base_id is null;
  if p.marca is null or p.modelo is null then
    return null;
  end if;

  v_tipo := case a.part_terminology_id
    when 2172  then 'RADIADOR'
    when 6708  then 'CONDENSADOR'
    when 12616 then 'INTERCOOLER'
    when 2084  then 'ENFRIADOR DE ACEITE'
    when 2088  then 'ENFRIADOR DE ACEITE DE TRANSMISION'
    when 17668 then 'ENFRIADOR DE ACEITE Y TRANSMISION'
    when 20531 then 'ENFRIADOR DE ACEITE DE TRANSMISION MANUAL'
    when 48305 then 'TANQUE'
    when 17700 then 'TANQUE DE ENTRADA'
    when 17701 then 'TANQUE DE SALIDA'
    when 10457 then 'DEPOSITO DE REFRIGERANTE'
    when 63482 then 'DEPOSITO DE EXPANSION'
    when 10707 then 'TOLVA'
    when 64918 then 'INTERCAMBIADOR'
  end;
  if v_tipo is null then
    v_tipo := (select case c.codigo_sap when '25' then 'RADIADOR' when '07' then 'CONDENSADOR' when '18' then 'INTERCOOLER'
                                        when '11' then 'ENFRIADOR DE ACEITE' when '29' then 'TANQUE' when '09' then 'DEPOSITO'
                                        when '44' then 'TOLVA' when '46' then 'INTERCAMBIADOR' end
               from app.categoria c where c.id = a.categoria_id);
  end if;

  v_anios := case when p.desde is null then null
                  when p.hasta = p.desde then 'M ' || lpad((p.desde % 100)::text, 2, '0')
                  else 'M ' || lpad((p.desde % 100)::text, 2, '0') || '/' || lpad((p.hasta % 100)::text, 2, '0') end;
  v_motor := (regexp_match(coalesce(p.motor, ''), '(\d+(?:\.\d+)?)\s*L\M'))[1];
  v_motor := case when v_motor is not null then v_motor || 'L' end;
  v_trans := case a.transmision when 'AUTOMATICA' then 'AT' when 'MANUAL' then 'MT' end;
  -- Fabricados: el material de la sub-subcategoría de SAP ("COBRE LATON"; de "RADIADORES-…-ALUMINIO", lo último)
  if a.linea = 'FABRICADO' then
    v_material := replace(regexp_replace(coalesce(a.material_descripcion, ''), '^.*-', ''), '/', ' ');
  end if;

  return left(app.fn_texto_sap(concat_ws(' ', v_tipo, p.marca, p.modelo, v_anios, v_motor, v_trans, v_material)), 100);
end $$;

-- Recalcula la automática de un artículo (nunca toca una ajustada a mano)
create function app.fn_actualizar_descripcion_nexo(p_articulo_id bigint) returns void language sql as $$
  update app.articulo a set descripcion_nexo = app.fn_descripcion_nexo(a)
  where a.id = p_articulo_id and not a.descripcion_nexo_manual
    and a.descripcion_nexo is distinct from app.fn_descripcion_nexo(a)
$$;

create function app.al_cambiar_aplicacion_descripcion() returns trigger language plpgsql as $$
begin
  perform app.fn_actualizar_descripcion_nexo(coalesce(new.articulo_id, old.articulo_id));
  return null;
end $$;
create trigger descripcion_nexo
  after insert or delete or update of es_principal, marca, modelo, anio, motor on app.articulo_aplicacion
  for each row execute function app.al_cambiar_aplicacion_descripcion();

-- Cambios del propio artículo que entran en la descripción (tipo de parte, transmisión o material de SAP)
create function app.al_cambiar_articulo_descripcion() returns trigger language plpgsql as $$
begin
  if not new.descripcion_nexo_manual then
    new.descripcion_nexo := app.fn_descripcion_nexo(new);
  end if;
  return new;
end $$;
create trigger descripcion_nexo
  before update of part_terminology_id, categoria_id, transmision, material_descripcion, linea, descripcion_nexo_manual
  on app.articulo for each row execute function app.al_cambiar_articulo_descripcion();

-- El Fabricado hereda también el motor de las aplicaciones del Importado (copia del catálogo)
create or replace function app.fn_heredar_de_equivalente(p_fabricado_id bigint, p_usuario_id bigint) returns jsonb
language plpgsql as $$
declare v_importado bigint; n_partes integer; n_apps integer; v_tiene_principal boolean;
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

  v_tiene_principal := exists (select 1 from app.articulo_aplicacion x where x.articulo_id = p_fabricado_id and x.es_principal);
  insert into app.articulo_aplicacion (articulo_id, base_vehicle_id, equipment_base_id, sub_model_id, engine_config_id,
                                       transmission_id, notas, origen, parte_id, es_principal, make_id, model_id, anio, marca, modelo,
                                       motor)
  select p_fabricado_id, a.base_vehicle_id, a.equipment_base_id, a.sub_model_id, a.engine_config_id, a.transmission_id,
         a.notas, 'HEREDADO_EQUIVALENTE', a.parte_id, a.es_principal and not v_tiene_principal, a.make_id, a.model_id, a.anio,
         a.marca, a.modelo, a.motor
  from app.articulo_aplicacion a
  where a.articulo_id = v_importado and a.confirmado_por is not null
  on conflict do nothing;
  get diagnostics n_apps = row_count;

  return jsonb_build_object('importado_id', v_importado, 'partes', n_partes, 'aplicaciones_sugeridas', n_apps);
end $$;
