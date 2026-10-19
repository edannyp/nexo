-- Ejemplo de carga: cómo quedan diagramas reales de db_diagrams en el esquema de Consolidación.
-- Valores tomados de db_diagrams el 2026-10-15. Explicación paso a paso: ejemplo_carga.md.
-- Requiere: migraciones aplicadas y `ref` cargada (db/ref/cargar_ref.py, o db/pruebas/ref_minimo_consolidacion.sql en pruebas).
-- Cada bloque es lo que haría el proceso de carga por cada registro leído de la fuente.

begin;

-- 0. Catálogos (una sola vez) -----------------------------------------------------------------
insert into catalogo.fuente (codigo, nombre, tipo, prioridad)
values ('DB_DIAGRAMS', 'Catálogo de diagramas propio', 'CATALOGO_PROPIO', 1)
on conflict (codigo) do nothing;

insert into catalogo.marca_pieza (nombre, tipo) values ('Hyundai', 'OEM'), ('Ford', 'OEM')
on conflict (nombre_norm) do nothing;

-- 1. Abrir corrida ----------------------------------------------------------------------------
create temp table ctx (corrida_id bigint) on commit drop;
with c as (
  insert into carga.corrida (fuente_id, version_proceso)
  select id, 'ejemplo-1.0' from catalogo.fuente where codigo = 'DB_DIAGRAMS'
  returning id
)
insert into ctx select id from c;

------------------------------------------------------------------------------------------------
-- Caso A: diagrama 905096 (radiador Hyundai) — OEM abreviados, medidas numéricas, vehículo incompleto
--   db_diagrams: dpi=1816, oem='2531022050/22070', core_size='335x608x16/22/26', tank_size='626x44',
--                marca='HYUNDAI', modelo=null, años=null, alto_panal=335, ancho_panal=16, largo_panal=608
------------------------------------------------------------------------------------------------
do $$
declare
  v_corrida bigint := (select corrida_id from ctx);
  v_fuente  smallint := (select id from catalogo.fuente where codigo = 'DB_DIAGRAMS');
  v_hyundai integer := (select id from catalogo.marca_pieza where nombre_norm = 'HYUNDAI');
  v_parte   bigint;
  v_reg     bigint;
begin
  insert into catalogo.parte (part_terminology_id, descripcion)
  values (2172, 'Radiador Hyundai panal 335x608x16')               -- 2172 = PCdb "Radiator"
  returning id into v_parte;

  -- El registro guarda TODO lo que vino, tal cual.
  insert into catalogo.registro_fuente (fuente_id, id_en_fuente, descripcion_original, datos_crudos, hash_contenido,
                                        parte_id, vinculo_metodo, vinculo_confianza, corrida_id)
  values (v_fuente, '905096', 'RADIADOR',
          '{"codigo":"905096","parte":"RADIADOR","dpi":"1816","oem":"2531022050/22070","core_size":"335x608x16/22/26",
            "tank_size":"626x44","marca":"HYUNDAI","alto_panal":335,"ancho_panal":16,"largo_panal":608}',
          'sha256-del-json-original', v_parte, 'NUMERO', 1.0, v_corrida)
  returning id into v_reg;

  -- '2531022050/22070' son DOS números OEM: el segundo abrevia el sufijo → 25310-22070.
  insert into catalogo.parte_numero (parte_id, registro_fuente_id, tipo, marca_pieza_id, numero, confianza) values
    (v_parte, v_reg, 'DPI', null,      '1816',        0.9),
    (v_parte, v_reg, 'OEM', v_hyundai, '25310-22050', 0.8),
    (v_parte, v_reg, 'OEM', v_hyundai, '25310-22070', 0.6);       -- menor confianza: se expandió una abreviatura

  -- Medidas del panal en mm (PAdb 267 Core Height, 269 Core Width, 268 Core Thickness), con el texto original.
  insert into catalogo.parte_atributo (parte_id, registro_fuente_id, paid, valor_num, uom_code, valor_original) values
    (v_parte, v_reg, 267, 335, 'MM', '335x608x16/22/26'),
    (v_parte, v_reg, 269, 608, 'MM', '335x608x16/22/26'),
    (v_parte, v_reg, 268, 16,  'MM', '335x608x16/22/26');

  -- '16/22/26' sugiere variantes de espesor: se registra para revisión, no se adivina.
  insert into catalogo.conflicto (parte_id, tipo, detalle)
  values (v_parte, 'ATRIBUTO_DISCREPA',
          jsonb_build_object('paid', 268, 'valores', jsonb_build_array(16, 22, 26), 'origen', 'core_size', 'registro_fuente_id', v_reg));

  -- Solo se sabe la marca: no hay base vehicle posible → aplicación sin homologar (no se inventa).
  insert into catalogo.aplicacion_sin_homologar (parte_id, registro_fuente_id, marca_texto, motivo)
  values (v_parte, v_reg, 'HYUNDAI', 'MODELO_DESCONOCIDO');
end $$;

------------------------------------------------------------------------------------------------
-- Caso B: diagrama 918255 (radiador Ford) — medidas solo en texto
--   db_diagrams: dpi=770, oem='568.770.38', core_size='770x588x36', alto/ancho/largo_panal = null
------------------------------------------------------------------------------------------------
do $$
declare
  v_corrida bigint := (select corrida_id from ctx);
  v_fuente  smallint := (select id from catalogo.fuente where codigo = 'DB_DIAGRAMS');
  v_ford    integer := (select id from catalogo.marca_pieza where nombre_norm = 'FORD');
  v_parte   bigint;
  v_reg     bigint;
begin
  insert into catalogo.parte (part_terminology_id, descripcion)
  values (2172, 'Radiador Ford panal 770x588x36') returning id into v_parte;

  insert into catalogo.registro_fuente (fuente_id, id_en_fuente, descripcion_original, datos_crudos, hash_contenido,
                                        parte_id, vinculo_metodo, vinculo_confianza, corrida_id)
  values (v_fuente, '918255', 'RADIADOR',
          '{"codigo":"918255","parte":"RADIADOR","dpi":"770","oem":"568.770.38","core_size":"770x588x36",
            "tank_size":"598.5x76.6","marca":"FORD"}',
          'sha256-del-json-original', v_parte, 'NUMERO', 1.0, v_corrida)
  returning id into v_reg;

  -- numero_norm se calcula solo: '568.770.38' → '56877038'.
  insert into catalogo.parte_numero (parte_id, registro_fuente_id, tipo, marca_pieza_id, numero, confianza) values
    (v_parte, v_reg, 'DPI', null,   '770',        0.8),
    (v_parte, v_reg, 'OEM', v_ford, '568.770.38', 0.8);

  -- core_size viene como alto x largo x espesor (verificado con 905096, que trae ambos formatos).
  insert into catalogo.parte_atributo (parte_id, registro_fuente_id, paid, valor_num, uom_code, valor_original) values
    (v_parte, v_reg, 267, 770, 'MM', '770x588x36'),
    (v_parte, v_reg, 269, 588, 'MM', '770x588x36'),
    (v_parte, v_reg, 268, 36,  'MM', '770x588x36');
end $$;

------------------------------------------------------------------------------------------------
-- Caso C: diagrama 915015 — vehículo de db_diagrams homologado a ACES
--   compatibilidades: marca='SUZUKI', modelo='Grand Vitara II', ano1=2005, ano2=2015, motor='JB420', cilindrada='2.0'
--   'Grand Vitara II' es una GENERACIÓN, no un modelo VCdb: se homologa al model 'Grand Vitara'.
------------------------------------------------------------------------------------------------
do $$
declare
  v_corrida bigint := (select corrida_id from ctx);
  v_fuente  smallint := (select id from catalogo.fuente where codigo = 'DB_DIAGRAMS');
  v_vcdb    text := (select version from ref.version where base = 'VCdb');
  v_parte   bigint;
  v_reg     bigint;
  n         integer;
begin
  insert into catalogo.parte (part_terminology_id, descripcion)
  values (2172, 'Radiador Suzuki Grand Vitara 2005-2015') returning id into v_parte;

  insert into catalogo.registro_fuente (fuente_id, id_en_fuente, descripcion_original, datos_crudos, hash_contenido,
                                        parte_id, vinculo_metodo, vinculo_confianza, corrida_id)
  values (v_fuente, '915015', 'RADIADOR',
          '{"codigo":"915015","compatibilidades":[{"marca":"SUZUKI","modelo":"Grand Vitara II","ano1":2005,"ano2":2015,
            "motor":"JB420","cilindrada":"2.0","carroceria":"SUV"}]}',
          'sha256-del-json-original', v_parte, 'MEDIDAS_APLICACION', 0.7, v_corrida)
  returning id into v_reg;

  -- Un base vehicle por año. El motor JB420 2.0 no se resolvió a engine_config_id: queda en notas.
  insert into catalogo.parte_aplicacion (parte_id, registro_fuente_id, base_vehicle_id, notas, vcdb_version, confianza)
  select v_parte, v_reg, bv.base_vehicle_id, 'Motor JB420 2.0 (sin engine_config_id)', v_vcdb, 0.7
  from ref.make mk
  join ref.base_vehicle bv on bv.make_id = mk.make_id and bv.year_id between 2005 and 2015
  join ref.model md on md.model_id = bv.model_id
  where upper(mk.make_name) = 'SUZUKI' and upper(md.model_name) = 'GRAND VITARA';
  get diagnostics n = row_count;

  if n = 0 then  -- si AutoCare no lo tuviera, no se inventa: queda pendiente de homologar
    insert into catalogo.aplicacion_sin_homologar (parte_id, registro_fuente_id, marca_texto, modelo_texto, anio_desde, anio_hasta, motor_texto, motivo)
    values (v_parte, v_reg, 'SUZUKI', 'Grand Vitara II', 2005, 2015, 'JB420 2.0', 'MODELO_DESCONOCIDO');
  end if;
end $$;

-- 2. Cerrar corrida ---------------------------------------------------------------------------
update carga.corrida set estado = 'COMPLETA', terminada_en = now(), leidos = 3, insertados = 3
where id = (select corrida_id from ctx);

commit;
