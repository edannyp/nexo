-- Tres radiadores importados, validados por el camino normal (un operador completa y envía, un supervisor valida) y emparejados
-- con las partes 1, 2 y 3 de la Consolidación local. Solo base local.
do $$
declare
  v_lote bigint;
  v_op   bigint;
  v_sup  bigint;
  r      record;
  i      integer := 0;
begin
  insert into staging.lote default values returning lote_id into v_lote;
  insert into staging.articulo_sap (item_code, descripcion, categoria_codigo, subcategoria_codigo, subcategoria_nombre, congelado_sap,
                                    datos_sap, extraido_en, lote_id)
  select c, d, '25', '2501', 'IMPORTADOS', 'N', jsonb_build_object('ItemCode', c), now(), v_lote
  from (values ('RAD00701', 'RAD. HYUNDAI ACCENT'), ('RAD00702', 'RAD. FORD F-350'), ('RAD00703', 'RAD. SUZUKI GRAND VITARA'))
       as t(c, d);
  perform app.fn_procesar_staging(v_lote);

  insert into app.usuario (usuario, nombre, password_hash) values ('op.ejemplo', 'Operador de ejemplo', 'x') returning id into v_op;
  insert into app.usuario (usuario, nombre, password_hash) values ('sup.ejemplo', 'Supervisor de ejemplo', 'x') returning id into v_sup;
  insert into app.usuario_rol values (v_op, 'OPERADOR'), (v_sup, 'SUPERVISOR');

  for r in select id from app.articulo where item_code in ('RAD00701', 'RAD00702', 'RAD00703') order by item_code loop
    i := i + 1;
    insert into app.articulo_parte (articulo_id, parte_id, es_principal, origen, confirmado_por)
    values (r.id, i, true, 'CONSOLIDACION', v_op);
    insert into app.articulo_atributo (articulo_id, paid, valor_texto, origen, confirmado_por, confirmado_en)
    select r.id, c.paid, 'confirmado', 'MANUAL', v_op, now()
    from app.articulo a join meta.atributo_config c on c.part_terminology_id = a.part_terminology_id
    where a.id = r.id and c.habilitado and c.obligatorio
    on conflict (articulo_id, paid) do nothing;
    perform app.fn_transicionar(r.id, 'POR_VALIDAR', 'USUARIO', v_op::text);
    perform app.fn_transicionar(r.id, 'VALIDADO', 'USUARIO', v_sup::text);
  end loop;
end $$;
