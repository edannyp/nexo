-- Nexo 0016 · Vehículo principal (ADR 0025)
-- Cada artículo tiene UN vehículo principal: un grupo de sus aplicaciones (mismo vehículo, submodelo y motor en uno o varios años,
-- o un mismo equipo), además de las aplicaciones adicionales. Es obligatorio para enviar a validar, se entrega al proceso de salida
-- (Nexo → SAP) traducido a los códigos de SAP y, si no coincide con lo que dice SAP, abre el hallazgo VEHICULO_DISTINTO.

alter type app.tipo_hallazgo add value if not exists 'VEHICULO_DISTINTO';

alter table app.articulo_aplicacion
  add column es_principal boolean not null default false,
  add column make_id      integer,      -- copia del catálogo (AutoCare o MercadoExterno) para agrupar, filtrar y entregar a SAP
  add column model_id     integer,
  add column anio         integer,
  add column marca        text,
  add column modelo       text;
comment on column app.articulo_aplicacion.es_principal is
  'Del vehículo principal del artículo (ADR 0025). Todas las filas principales son el mismo vehículo, submodelo y motor (o equipo).';
comment on column app.articulo_aplicacion.make_id is 'Copia del catálogo al agregar la aplicación (el vehículo base no cambia de marca).';

create index articulo_aplicacion_principal on app.articulo_aplicacion (articulo_id) where es_principal;

-- Requisitos para enviar a POR_VALIDAR: el vehículo principal reemplaza "al menos una aplicación o un emparejamiento"
create or replace function app.fn_requisitos_por_validar(p_articulo_id bigint) returns text[]
language sql stable as $$
  select array_remove(
    array[
      case when a.part_terminology_id is null then 'TIPO_DE_PARTE' end,
      case when not exists (select 1 from app.articulo_aplicacion x where x.articulo_id = a.id and x.es_principal)
             or exists (select 1 from app.articulo_aplicacion x where x.articulo_id = a.id and x.es_principal
                        and x.confirmado_por is null)
             or (select count(distinct (x.make_id, x.model_id, x.sub_model_id, x.engine_config_id, x.equipment_base_id))
                 from app.articulo_aplicacion x where x.articulo_id = a.id and x.es_principal) > 1
           then 'VEHICULO_PRINCIPAL' end
    ]
    || coalesce((select array_agg('ATRIBUTO:' || r.nombre order by r.orden nulls last, r.paid)
                 from meta.atributo_config r
                 where r.part_terminology_id = a.part_terminology_id and r.habilitado and r.obligatorio and r.obsoleto_en is null
                   and not exists (select 1 from app.articulo_atributo t
                                   where t.articulo_id = a.id and t.paid = r.paid and t.confirmado_por is not null)), '{}'),
    null)
  from app.articulo a where a.id = p_articulo_id
$$;

-- El Fabricado hereda del Importado confirmado: también qué aplicaciones son el vehículo principal (como sugerencias)
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
                                       transmission_id, notas, origen, parte_id, es_principal, make_id, model_id, anio, marca, modelo)
  select p_fabricado_id, a.base_vehicle_id, a.equipment_base_id, a.sub_model_id, a.engine_config_id, a.transmission_id,
         a.notas, 'HEREDADO_EQUIVALENTE', a.parte_id, a.es_principal and not v_tiene_principal, a.make_id, a.model_id, a.anio,
         a.marca, a.modelo
  from app.articulo_aplicacion a
  where a.articulo_id = v_importado and a.confirmado_por is not null
  on conflict do nothing;
  get diagnostics n_apps = row_count;

  return jsonb_build_object('importado_id', v_importado, 'partes', n_partes, 'aplicaciones_sugeridas', n_apps);
end $$;

-- Lo que recibe el proceso de salida (Nexo → SAP; contratos.md): el vehículo principal confirmado y sus códigos de SAP según las
-- homologaciones confirmadas (null si la marca o el modelo aún no están homologados).
create view app.v_vehiculo_principal as
select a.id as articulo_id, a.item_code, a.estado,
       min(x.make_id) as make_id, min(x.marca) as marca, min(x.model_id) as model_id, min(x.modelo) as modelo,
       min(x.sub_model_id) as sub_model_id, min(x.engine_config_id) as engine_config_id, min(x.equipment_base_id) as equipment_base_id,
       min(x.anio) as anio_desde, max(x.anio) as anio_hasta,
       (select min(hm.marca_codigo_sap) from app.homologacion_marca hm
        where hm.make_id = min(x.make_id) and hm.estado = 'CONFIRMADA') as marca_codigo_sap,
       (select min(ho.modelo_codigo_sap) from app.homologacion_modelo ho
        where ho.model_id = min(x.model_id) and ho.estado = 'CONFIRMADA'
          and ho.marca_codigo_sap = (select min(hm.marca_codigo_sap) from app.homologacion_marca hm
                                     where hm.make_id = min(x.make_id) and hm.estado = 'CONFIRMADA')) as modelo_codigo_sap
from app.articulo a
join app.articulo_aplicacion x on x.articulo_id = a.id and x.es_principal and x.confirmado_por is not null
group by a.id;
comment on view app.v_vehiculo_principal is 'Vehículo principal confirmado de cada artículo, con sus códigos de SAP (ADR 0025).';

-- VEHICULO_DISTINTO: el vehículo principal (lo que decidió el operador) no es el que dice SAP. Manda Nexo; SAP se corrige (a mano o
-- con el proceso de salida). Se compara con la homologación confirmada de la marca y del modelo de SAP y, si no la hay, por nombre;
-- los años deben solaparse. Se recalcula al cambiar el principal y al cambiar el vehículo en SAP (el hallazgo se cierra solo).
create function app.fn_texto_comparable(t text) returns text language sql immutable as $$
  select nullif(regexp_replace(upper(translate(coalesce(t, ''), 'áéíóúàèìòùäëïöüñÁÉÍÓÚÀÈÌÒÙÄËÏÖÜÑ', 'aeiouaeiouaeiounAEIOUAEIOUAEIOUN')),
                               '[^A-Z0-9]', '', 'g'), '')
$$;

create function app.fn_revisar_vehiculo_principal(p_articulo_id bigint) returns boolean
language plpgsql as $$
declare
  a app.articulo;
  p record;
  v_marca_ok boolean; v_modelo_ok boolean; v_anios_ok boolean;
  v_make integer; v_model integer; v_valor text;
begin
  select * into a from app.articulo where id = p_articulo_id;
  select min(x.make_id) as make_id, min(x.model_id) as model_id, min(x.marca) as marca, min(x.modelo) as modelo,
         min(x.anio) as desde, max(x.anio) as hasta
  into p from app.articulo_aplicacion x
  where x.articulo_id = p_articulo_id and x.es_principal and x.confirmado_por is not null and x.equipment_base_id is null;

  -- Sin principal de vehículo o sin vehículo válido en SAP (la marca basura ya es MARCA_INVALIDA): nada que comparar
  if a.id is null or p.make_id is null or a.marca_vehiculo_codigo is null then
    update app.hallazgo_calidad_sap set corregido_en = now()
    where articulo_id = p_articulo_id and tipo = 'VEHICULO_DISTINTO' and corregido_en is null;
    return null;
  end if;

  select make_id into v_make from app.homologacion_marca where marca_codigo_sap = a.marca_vehiculo_codigo and estado = 'CONFIRMADA';
  v_marca_ok := case when v_make is not null then v_make = p.make_id
                     else app.fn_texto_comparable(a.marca_vehiculo) = app.fn_texto_comparable(p.marca) end;
  select model_id into v_model from app.homologacion_modelo
  where marca_codigo_sap = a.marca_vehiculo_codigo and modelo_codigo_sap = a.modelo_vehiculo_codigo and estado = 'CONFIRMADA';
  v_modelo_ok := case when a.modelo_vehiculo is null and v_model is null then true
                      when v_model is not null then v_model = p.model_id
                      else strpos(app.fn_texto_comparable(p.modelo), app.fn_texto_comparable(a.modelo_vehiculo)) > 0
                        or strpos(app.fn_texto_comparable(a.modelo_vehiculo), app.fn_texto_comparable(p.modelo)) > 0 end;
  v_anios_ok := a.anio_desde is null or p.desde is null
                or (p.desde <= coalesce(a.anio_hasta, a.anio_desde) and p.hasta >= a.anio_desde);

  if coalesce(v_marca_ok, false) and coalesce(v_modelo_ok, false) and v_anios_ok then
    update app.hallazgo_calidad_sap set corregido_en = now()
    where articulo_id = p_articulo_id and tipo = 'VEHICULO_DISTINTO' and corregido_en is null;
    return false;
  end if;

  v_valor := format('SAP: %s %s %s · Nexo: %s %s %s',
                    coalesce(a.marca_vehiculo, '?'), coalesce(a.modelo_vehiculo, '?'),
                    concat_ws('–', a.anio_desde, nullif(a.anio_hasta, a.anio_desde)),
                    p.marca, p.modelo, concat_ws('–', p.desde, nullif(p.hasta, p.desde)));
  update app.hallazgo_calidad_sap set valor = v_valor
  where articulo_id = p_articulo_id and tipo = 'VEHICULO_DISTINTO' and corregido_en is null;
  if not found then
    insert into app.hallazgo_calidad_sap (articulo_id, tipo, campo_sap, valor)
    values (p_articulo_id, 'VEHICULO_DISTINTO', 'U_Marca', v_valor);
  end if;
  return true;
end $$;

create function app.al_cambiar_aplicacion_principal() returns trigger language plpgsql as $$
begin
  perform app.fn_revisar_vehiculo_principal(coalesce(new.articulo_id, old.articulo_id));
  return null;
end $$;
create trigger revisar_vehiculo_principal
  after insert or delete or update of es_principal, confirmado_por, make_id, model_id, anio on app.articulo_aplicacion
  for each row execute function app.al_cambiar_aplicacion_principal();

create function app.al_cambiar_vehiculo_sap() returns trigger language plpgsql as $$
begin
  perform app.fn_revisar_vehiculo_principal(new.id);
  return null;
end $$;
create trigger revisar_vehiculo_sap
  after update of marca_vehiculo_codigo, marca_vehiculo, modelo_vehiculo_codigo, modelo_vehiculo, anio_desde, anio_hasta
  on app.articulo for each row
  when ((old.marca_vehiculo_codigo, old.marca_vehiculo, old.modelo_vehiculo_codigo, old.modelo_vehiculo, old.anio_desde, old.anio_hasta)
        is distinct from
        (new.marca_vehiculo_codigo, new.marca_vehiculo, new.modelo_vehiculo_codigo, new.modelo_vehiculo, new.anio_desde, new.anio_hasta))
  execute function app.al_cambiar_vehiculo_sap();

-- Una homologación confirmada cambia la comparación de los artículos de esa marca o modelo
create function app.al_cambiar_homologacion() returns trigger language plpgsql as $$
begin
  perform app.fn_revisar_vehiculo_principal(a.id) from app.articulo a
  where a.marca_vehiculo_codigo = coalesce(new.marca_codigo_sap, old.marca_codigo_sap)
    and exists (select 1 from app.articulo_aplicacion x where x.articulo_id = a.id and x.es_principal);
  return null;
end $$;
create trigger revisar_vehiculo_principal after insert or update or delete on app.homologacion_marca
  for each row execute function app.al_cambiar_homologacion();
create trigger revisar_vehiculo_principal after insert or update or delete on app.homologacion_modelo
  for each row execute function app.al_cambiar_homologacion();
