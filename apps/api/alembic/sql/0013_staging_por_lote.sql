-- Nexo 0013 · Staging con una fila por artículo y lote (decisión 2026-10-21)
-- El ETL de SAP escribe cada lote agregando filas (modo append de Spark/JDBC), sin upsert. Las marcas y modelos se validan con los
-- del mismo lote, un lote no se procesa dos veces y Nexo conserva los últimos etl.lotes_conservados lotes procesados.
-- "Lo que ya se envió antes" ya no sale de staging sino de Nexo: app.fn_articulos_conocidos().

alter table staging.articulo_sap drop constraint articulo_sap_pkey, add primary key (lote_id, item_code);
alter table staging.sap_marca drop constraint sap_marca_pkey, add primary key (lote_id, marca_codigo);
alter table staging.sap_modelo drop constraint sap_modelo_pkey, add primary key (lote_id, marca_codigo, modelo_codigo);
comment on table staging.articulo_sap is 'Contrato del ETL de entrada: una fila por artículo y lote, solo INSERT (sin upsert).';

insert into meta.parametro values
  ('etl.lotes_conservados', '7', 'Lotes procesados del ETL de SAP que se conservan en staging; los anteriores se limpian al procesar.');

-- Los ItemCode que Nexo conoce: el ETL los vuelve a enviar aunque hoy estén en otra categoría (así Nexo sabe que salieron del alcance)
create function app.fn_articulos_conocidos() returns setof text
language sql stable security definer set search_path = app, pg_temp as $$
  select item_code from app.articulo order by item_code
$$;
revoke execute on function app.fn_articulos_conocidos() from public;

create or replace view staging.v_articulo_normalizado as
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
    select 1 from staging.sap_modelo sm where sm.lote_id = s.lote_id and sm.marca_codigo = m.marca_codigo
      and sm.modelo_codigo = s.modelo_vehiculo_codigo), true) as modelo_valido,
  s.transmision as r_transmision, s.tamano_panal as r_tamano, s.tipo_flujo as r_tipo_flujo,
  s.entrada_ubicacion as r_entrada_ubicacion, s.salida_ubicacion as r_salida_ubicacion, s.incluye_tapon as r_tapon,
  s.incluye_termostato as r_termostato, s.incluye_enfriador_transmision as r_enfriador,
  s.panal_alto as r_alto, s.panal_alto_unidad as r_alto_unidad, s.panal_largo as r_largo, s.panal_largo_unidad as r_largo_unidad,
  s.panal_ancho as r_ancho, s.panal_ancho_unidad as r_ancho_unidad
from staging.articulo_sap s
left join app.categoria c on c.codigo_sap = meta.limpiar(s.categoria_codigo)
left join staging.sap_marca m
  on m.lote_id = s.lote_id and m.marca_codigo = case when meta.limpiar(s.marca_vehiculo_codigo) ~ '^[0-9]+$'
                           then lpad(meta.limpiar(s.marca_vehiculo_codigo), 5, '0')
                           else meta.limpiar(s.marca_vehiculo_codigo) end
 and m.marca_codigo not in (select marca_codigo from meta.marca_sap_invalida)
left join meta.unidad_longitud ua on ua.codigo_sap = s.panal_alto_unidad
left join meta.unidad_longitud ul on ul.codigo_sap = s.panal_largo_unidad
left join meta.unidad_longitud ue on ue.codigo_sap = s.panal_ancho_unidad
left join meta.valor_lista_sap vi on vi.campo_sap = 'U_InletLocation'  and vi.valor_sap = meta.limpiar(s.entrada_ubicacion)
left join meta.valor_lista_sap vo on vo.campo_sap = 'U_OutletLocation' and vo.valor_sap = meta.limpiar(s.salida_ubicacion)
) b;

create or replace function app.fn_procesar_staging(p_lote_id bigint) returns jsonb
language plpgsql security definer set search_path = app, staging, meta, audit, public, pg_temp as $$
declare
  n           record;
  a           app.articulo;
  fila        jsonb;
  v_hash      text;
  v_activo    boolean;
  v_motivo    app.motivo_inactivo;
  cambios     jsonb;
  v_old_activo boolean;
  res         jsonb := '{"nuevos":0,"actualizados":0,"sin_cambios":0,"reabiertos":0,"inactivados":0,"activados":0,"descartados":0,"no_en_sap":0}';
  v_completo  boolean;
  v_total     integer;
  v_faltan    integer;
  v_max       numeric;
  v_conservar integer;
  cols        text[];
begin
  if (select procesado_en from staging.lote where lote_id = p_lote_id) is not null then
    raise exception 'LOTE_YA_PROCESADO: el lote % ya se aplicó', p_lote_id using errcode = 'P0001';
  end if;
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

      -- Lo ya revisado o en revisión vuelve a Pendiente para que el operador vea qué cambió (fuera de alcance o inactivo: no se reabre)
      if a.estado in ('VALIDADO', 'SINCRONIZADO', 'POR_VALIDAR') and v_activo then
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

  -- Foto completa (contrato del ETL): lo activo que no vino en el lote ya no está en SAP → inactivo NO_EN_SAP (si vuelve, se reactiva).
  -- Defensa: si faltan demasiados, el lote está roto (vacío, filtro equivocado…) y se rechaza entero sin tocar nada.
  select completo into v_completo from staging.lote where lote_id = p_lote_id;
  if v_completo then
    select count(*), count(*) filter (where ultimo_lote_id is distinct from p_lote_id) into v_total, v_faltan
    from app.articulo where activo;
    v_max := (select valor::numeric from meta.parametro where clave = 'etl.max_no_en_sap');
    if v_faltan > greatest(10, v_total * v_max) then
      raise exception 'LOTE_INCOMPLETO: el lote no trae % de % artículos activos (más del % %%); no se aplicó nada', v_faltan, v_total,
        round(v_max * 100) using errcode = 'P0001', hint = 'Revisa el ETL. Si de verdad salieron de SAP, ajusta meta.parametro etl.max_no_en_sap.';
    end if;
    for a in select * from app.articulo where activo and ultimo_lote_id is distinct from p_lote_id for update loop
      update app.articulo set activo = false, motivo_inactivo = 'NO_EN_SAP', asignado_a = null, asignado_hasta = null where id = a.id;
      insert into audit.bitacora_articulo (articulo_id, tipo, actor_tipo, actor, motivo)
      values (a.id, 'INACTIVADO', 'PROCESO', 'PROCESO:ETL', 'NO_EN_SAP');
    end loop;
    res := jsonb_set(res, '{no_en_sap}', to_jsonb(v_faltan));
  end if;

  update staging.lote set procesado_en = now(), resultado = res where lote_id = p_lote_id;

  -- Staging guarda una fila por artículo y lote: se conservan los últimos lotes procesados y el resto se limpia (el lote queda
  -- registrado en staging.lote con su resultado). El historial completo de SAP lo guarda el ETL en su propio almacenamiento.
  v_conservar := (select valor::int from meta.parametro where clave = 'etl.lotes_conservados');
  delete from staging.articulo_sap s where s.lote_id in (
    select lote_id from staging.lote where procesado_en is not null order by lote_id desc offset v_conservar);
  delete from staging.sap_marca s where s.lote_id in (
    select lote_id from staging.lote where procesado_en is not null order by lote_id desc offset v_conservar);
  delete from staging.sap_modelo s where s.lote_id in (
    select lote_id from staging.lote where procesado_en is not null order by lote_id desc offset v_conservar);
  return res;
end $$;
