-- Nexo 0011 · Clase de venta de ClickHouse (ADR 0023) y contrato del agente de revisión del catálogo (ADR 0012, 0017)

------------------------------------------------------------------------------------------
-- Clase de venta: la de la clasificación ABC-XYZ de la empresa (rlt_ml.latest_clasificacion_abcxyz), que Nexo ya copia a diario
-- en app.venta_referencia. Participación, top % y tendencia siguen calculándose con las unidades, dentro de cada tipo.
------------------------------------------------------------------------------------------
create or replace view app.v_indicador_venta as
with p as (
  select (select valor::int from meta.parametro where clave = 'ventas.meses_periodo') as meses,
         date_trunc('month', current_date)::date as fin
),
s as (
  select v.item_code,
         sum(v.unidades) filter (where v.mes >= (p.fin - make_interval(months => p.meses))) as unidades,
         sum(v.unidades) filter (where v.mes < (p.fin - make_interval(months => p.meses))) as unidades_previas
  from app.venta_mensual v cross join p
  where v.mes >= (p.fin - make_interval(months => 2 * p.meses)) and v.mes < p.fin
  group by v.item_code
),
u as (
  select a.id as articulo_id, a.item_code, a.categoria_id, a.linea,
         coalesce(s.unidades, 0) as unidades, coalesce(s.unidades_previas, 0) as unidades_previas
  from app.articulo a left join s on s.item_code = a.item_code
  where a.activo
),
r as (
  select u.*,
         sum(unidades) over (partition by categoria_id, linea) as total_tipo,
         count(*) over (partition by categoria_id, linea) as n_tipo,
         rank() over (partition by categoria_id, linea order by unidades desc) as posicion
  from u
)
select r.articulo_id, r.item_code, r.categoria_id, r.linea, r.unidades, r.unidades_previas,
       round(r.unidades / nullif(r.total_tipo, 0), 6) as participacion,
       case when left(ref.abcxyz_empresa, 1) in ('A', 'B', 'C') then left(ref.abcxyz_empresa, 1) end as clase,
       case when r.unidades = 0 then null else round(r.posicion::numeric / r.n_tipo, 4) end as top_pct,
       case when r.unidades_previas = 0 then null
            else round((r.unidades - r.unidades_previas) / r.unidades_previas, 4) end as tendencia,
       ref.abcxyz_empresa, ref.ultima_venta
from r
left join app.venta_referencia ref on ref.item_code = r.item_code;

comment on view app.v_indicador_venta is
  'Indicadores de venta por artículo activo: clase A/B/C de la clasificación de la empresa en ClickHouse (ADR 0023); participación, top % y tendencia relativos a su tipo (ADR 0022).';
delete from meta.parametro where clave in ('ventas.umbral_a', 'ventas.umbral_b');   -- los umbrales los aplica ClickHouse

------------------------------------------------------------------------------------------
-- Agente de revisión del catálogo (Consolidación → verificaciones de Nexo). Corre aparte, con su propio usuario: lee lo validado en
-- Nexo, lo compara con el catálogo maestro e informa los cambios; Nexo crea las verificaciones CAMBIO_CATALOGO. Cada cambio lleva
-- una clave: el mismo cambio no se informa dos veces al mismo artículo, aunque el supervisor ya lo haya resuelto (el ciclo cierra).
------------------------------------------------------------------------------------------
-- Una verificación abierta por artículo y origen… salvo los cambios del catálogo, que se distinguen por parte y clave del cambio:
-- con una fusión abierta, un cambio de datos distinto del mismo artículo también debe llegar al supervisor.
drop index app.tarea_abierta_unica;
create unique index tarea_abierta_unica on app.tarea_verificacion
  (articulo_id, origen, coalesce(detalle ->> 'imagen_id', (detalle ->> 'parte_id') || '|' || (detalle ->> 'clave'), ''))
  where estado = 'ABIERTA';

-- Partes de Consolidación emparejadas con artículos ya validados: las únicas que hay que revisar
create function app.fn_partes_emparejadas() returns table (parte_id bigint, articulos integer)
language sql stable security definer set search_path = app, pg_temp as $$
  select ap.parte_id, count(*)::integer
  from app.articulo_parte ap join app.articulo a on a.id = ap.articulo_id
  where a.activo and a.estado in ('VALIDADO', 'SINCRONIZADO')
  group by ap.parte_id order by ap.parte_id
$$;

-- Lo validado de cada artículo emparejado con esas partes, para compararlo con el catálogo
create function app.fn_datos_emparejamiento(p_partes bigint[]) returns table (
  parte_id bigint, item_code text, descripcion text, linea text, es_principal boolean, validado_en timestamptz,
  numero_parte_proveedor text, codigo_anterior text[], atributos jsonb, aplicaciones jsonb
)
language sql stable security definer set search_path = app, pg_temp as $$
  select ap.parte_id, a.item_code, a.descripcion, a.linea::text, ap.es_principal,
         (select max(b.creado_en) from audit.bitacora_articulo b
          where b.articulo_id = a.id and b.tipo = 'TRANSICION' and b.estado_destino = 'VALIDADO'),
         a.numero_parte_proveedor, a.codigo_anterior,
         coalesce((select jsonb_object_agg(t.paid::text, jsonb_strip_nulls(jsonb_build_object(
                     'valor_num', t.valor_num, 'uom_code', t.uom_code, 'valid_value_id', t.valid_value_id, 'valor_texto', t.valor_texto)))
                   from app.articulo_atributo t where t.articulo_id = a.id and t.confirmado_por is not null), '{}'),
         coalesce((select jsonb_agg(jsonb_strip_nulls(jsonb_build_object(
                     'base_vehicle_id', x.base_vehicle_id, 'equipment_base_id', x.equipment_base_id,
                     'sub_model_id', x.sub_model_id, 'engine_config_id', x.engine_config_id)) order by x.base_vehicle_id)
                   from app.articulo_aplicacion x where x.articulo_id = a.id and x.confirmado_por is not null), '[]')
  from app.articulo_parte ap join app.articulo a on a.id = ap.articulo_id
  where ap.parte_id = any(p_partes) and a.activo and a.estado in ('VALIDADO', 'SINCRONIZADO')
  order by ap.parte_id, a.item_code
$$;

-- p_cambios: lista JSON de cambios.
--   {"parte_id": 5003, "estado": "FUSIONADA", "fusionada_en_id": 9001}
--   {"parte_id": 5004, "estado": "DESCARTADA"}   ·   {"parte_id": 5005, "estado": "NO_EXISTE"}
--   {"parte_id": 5006, "estado": "DATOS_CAMBIARON", "item_code": "RAD00188", "huella": "<hash de los datos revisados>",
--    "nota": "El catálogo ahora dice alto 410 mm (antes 400)", "campos": ["267"]}
-- Crea una verificación CAMBIO_CATALOGO por artículo validado afectado. Devuelve {recibidos, tareas, repetidos}.
create function app.fn_registrar_cambios_catalogo(p_cambios jsonb) returns jsonb
language plpgsql security definer set search_path = app, audit, public, pg_temp as $$
declare
  c         jsonb;
  v_estado  text;
  v_clave   text;
  v_detalle jsonb;
  n         integer := 0;
  m         integer;
  recibidos integer := 0;
  afectados integer := 0;
begin
  if jsonb_typeof(p_cambios) is distinct from 'array' then
    raise exception 'CAMBIOS_INVALIDOS: se espera una lista JSON' using errcode = 'P0001';
  end if;
  perform set_config('app.usuario_id', 'PROCESO:REVISION_CATALOGO', true);
  for c in select * from jsonb_array_elements(p_cambios) loop
    v_estado := c ->> 'estado';
    if jsonb_typeof(c -> 'parte_id') is distinct from 'number'
       or coalesce(v_estado, '') not in ('FUSIONADA', 'DESCARTADA', 'NO_EXISTE', 'DATOS_CAMBIARON')
       or (v_estado = 'FUSIONADA' and jsonb_typeof(c -> 'fusionada_en_id') is distinct from 'number')
       or (v_estado = 'DATOS_CAMBIARON' and (length(trim(coalesce(c ->> 'nota', ''))) < 10 or length(c ->> 'nota') > 2000
                                             or length(trim(coalesce(c ->> 'huella', ''))) = 0))
       or (c ? 'item_code' and jsonb_typeof(c -> 'item_code') is distinct from 'string')
       or (c ? 'campos' and jsonb_typeof(c -> 'campos') is distinct from 'array') then
      raise exception 'CAMBIOS_INVALIDOS: %', c using errcode = 'P0001',
        hint = 'parte_id numérico; estado FUSIONADA (con fusionada_en_id), DESCARTADA, NO_EXISTE o DATOS_CAMBIARON (con nota y huella)';
    end if;
    -- La clave identifica el cambio: el mismo cambio no vuelve a crear una verificación para el mismo artículo
    v_clave := v_estado || ':' || coalesce(c ->> 'fusionada_en_id', c ->> 'huella', '');
    v_detalle := jsonb_strip_nulls(jsonb_build_object(
      'parte_id', (c ->> 'parte_id')::bigint, 'estado', v_estado, 'fusionada_en_id', (c ->> 'fusionada_en_id')::bigint,
      'nota', nullif(trim(c ->> 'nota'), ''), 'campos', c -> 'campos', 'clave', v_clave));
    insert into app.tarea_verificacion (articulo_id, origen, detalle)
    select ap.articulo_id, 'CAMBIO_CATALOGO', v_detalle
    from app.articulo_parte ap join app.articulo a on a.id = ap.articulo_id
    where ap.parte_id = (c ->> 'parte_id')::bigint and a.activo and a.estado in ('VALIDADO', 'SINCRONIZADO')
      and (not c ? 'item_code' or a.item_code = upper(c ->> 'item_code'))
      and not exists (select 1 from app.tarea_verificacion t
                      where t.articulo_id = ap.articulo_id and t.origen = 'CAMBIO_CATALOGO'
                        and t.detalle ->> 'parte_id' = c ->> 'parte_id' and t.detalle ->> 'clave' = v_clave)
    on conflict do nothing;
    get diagnostics m = row_count;
    n := n + m;
    recibidos := recibidos + 1;
    afectados := afectados + (select count(*) from app.articulo_parte ap join app.articulo a on a.id = ap.articulo_id
                              where ap.parte_id = (c ->> 'parte_id')::bigint and a.activo and a.estado in ('VALIDADO', 'SINCRONIZADO')
                                and (not c ? 'item_code' or a.item_code = upper(c ->> 'item_code')));
  end loop;
  return jsonb_build_object('recibidos', recibidos, 'tareas', n, 'repetidos', afectados - n);
end $$;

revoke execute on function app.fn_partes_emparejadas(), app.fn_datos_emparejamiento(bigint[]),
  app.fn_registrar_cambios_catalogo(jsonb) from public;
