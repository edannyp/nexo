-- Nexo 0012 · ETL de SAP con foto completa (decisiones del 2026-10-20)
-- 1. Cada lote del ETL puede ser una foto completa (staging.lote.completo): lo activo que no venga ya no está en SAP → inactivo NO_EN_SAP.
--    Defensa: un lote al que le faltan más del etl.max_no_en_sap de los activos se rechaza entero (LOTE_INCOMPLETO).
-- 2. Un cambio en SAP de un artículo POR_VALIDAR lo regresa a PENDIENTE (HASH_CAMBIO), igual que a los validados.

alter type app.motivo_inactivo add value if not exists 'NO_EN_SAP';
alter table staging.lote add column completo boolean not null default false;
comment on column staging.lote.completo is
  'El ETL envía una foto completa (todos los artículos de las categorías en alcance más los que ya envió antes): lo que falte se inactiva.';

insert into meta.parametro values
  ('etl.max_no_en_sap', '0.05', 'Fracción máxima de artículos activos que puede faltar en un lote completo; si faltan más, el lote se rechaza.');

insert into app.transicion_permitida values ('POR_VALIDAR', 'PENDIENTE', 'PROCESO', null, true, false);   -- HASH_CAMBIO

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
  return res;
end $$;
