-- Consolidación V004 · Carga del catálogo maestro (ADR 0026): fuentes con prioridad, corridas de foto completa con defensa,
-- conflictos de medidas entre fuentes y una vista de búsqueda que toma cada medida de la fuente más confiable.

-- Fuentes iniciales del catálogo maestro: los diagramas propios mandan sobre JJ Radiators cuando discrepan.
insert into catalogo.fuente (codigo, nombre, tipo, url_base, prioridad) values
  ('DB_DIAGRAMS', 'Diagramas propios (db_diagrams)', 'CATALOGO_PROPIO', null, 1),
  ('JJ_RADIATOR', 'JJ Radiator', 'SCRAPING', 'https://jjradiator.com', 2)
on conflict (codigo) do nothing;

-- Corridas de foto completa: la corrida trae TODO lo de su fuente; lo que no vino queda no vigente al cerrarla.
alter table carga.corrida add column completa boolean not null default false;
comment on column carga.corrida.completa is
  'Foto completa de la fuente: al cerrarla con carga.fn_cerrar_corrida, lo que no tocó queda vigente = false (ADR 0026).';

-- Un registro que la corrida leyó y no cambió solo actualiza corrida_id ("visto"): eso no cuenta como cambio.
create or replace function catalogo.tocar_actualizado_en() returns trigger language plpgsql as $$
begin
  if tg_table_name <> 'registro_fuente'
     or (to_jsonb(new) - 'corrida_id' - 'actualizado_en') is distinct from (to_jsonb(old) - 'corrida_id' - 'actualizado_en') then
    new.actualizado_en := now();
  end if;
  return new;
end $$;

-- Cierra una corrida: marca no vigente lo que no vino (si es foto completa, con defensa), detecta medidas que discrepan entre
-- fuentes de una misma parte y deja la corrida COMPLETA. Devuelve {no_vigentes, conflictos}.
create function carga.fn_cerrar_corrida(p_corrida_id bigint, p_max_faltantes numeric default 0.05) returns jsonb
language plpgsql as $$
declare
  c carga.corrida;
  v_total integer; v_faltan integer; v_conflictos integer := 0;
begin
  select * into c from carga.corrida where id = p_corrida_id for update;
  if c.id is null then
    raise exception 'CORRIDA_NO_EXISTE: %', p_corrida_id using errcode = 'P0002';
  end if;
  if c.estado <> 'EN_PROCESO' then
    raise exception 'CORRIDA_CERRADA: la corrida % ya está %', p_corrida_id, c.estado using errcode = 'P0001';
  end if;

  v_faltan := 0;
  if c.completa then
    select count(*), count(*) filter (where corrida_id is distinct from p_corrida_id)
    into v_total, v_faltan
    from catalogo.registro_fuente where fuente_id = c.fuente_id and vigente;
    -- Defensa: casi siempre es una lectura cortada (scraping incompleto, consulta vacía). No se aplica nada.
    if v_faltan > greatest(10, ceil(v_total * p_max_faltantes)) then
      raise exception 'CORRIDA_INCOMPLETA: faltan % de % registros vigentes de la fuente (máximo %)',
        v_faltan, v_total, greatest(10, ceil(v_total * p_max_faltantes)) using errcode = 'P0001';
    end if;
    update catalogo.registro_fuente set vigente = false, corrida_id = p_corrida_id
    where fuente_id = c.fuente_id and vigente and corrida_id is distinct from p_corrida_id;
  end if;

  -- Medidas del panal (alto 267, ancho 268, largo 269) que difieren más de 2 mm entre registros vigentes de la misma parte
  with medidas as (
    select a.parte_id, a.paid, a.valor_num, r.id as registro_fuente_id, f.codigo as fuente
    from catalogo.parte_atributo a
    join catalogo.registro_fuente r on r.id = a.registro_fuente_id and r.vigente
    join catalogo.fuente f on f.id = r.fuente_id
    where a.paid in (267, 268, 269) and a.valor_num is not null
      and a.parte_id in (select parte_id from catalogo.registro_fuente where corrida_id = p_corrida_id and parte_id is not null)
  ), discrepan as (
    select parte_id, paid,
           jsonb_agg(jsonb_build_object('registro_fuente_id', registro_fuente_id, 'fuente', fuente, 'valor', valor_num)
                     order by registro_fuente_id) as valores
    from medidas group by parte_id, paid having max(valor_num) - min(valor_num) > 2
  ), nuevos as (
    insert into catalogo.conflicto (parte_id, tipo, detalle)
    select d.parte_id, 'ATRIBUTO_DISCREPA', jsonb_build_object('paid', d.paid, 'valores', d.valores, 'corrida_id', p_corrida_id)
    from discrepan d
    where not exists (select 1 from catalogo.conflicto x
                      where x.parte_id = d.parte_id and x.tipo = 'ATRIBUTO_DISCREPA' and x.estado = 'ABIERTO'
                        and (x.detalle ->> 'paid')::integer = d.paid)
    returning 1
  )
  select count(*) into v_conflictos from nuevos;

  update carga.corrida set estado = 'COMPLETA', terminada_en = now() where id = p_corrida_id;
  return jsonb_build_object('no_vigentes', v_faltan, 'conflictos', v_conflictos);
end $$;
comment on function carga.fn_cerrar_corrida(bigint, numeric) is
  'Cierra la corrida (ADR 0026): foto completa → no vigente lo que no vino, con defensa CORRIDA_INCOMPLETA; conflictos de medidas.';

-- Búsqueda: cada medida sale de la fuente de mayor prioridad (1 = más confiable) entre los registros vigentes de la parte.
create or replace view catalogo.v_parte_busqueda as
with medida as (
  select distinct on (a.parte_id, a.paid) a.parte_id, a.paid, a.valor_num
  from catalogo.parte_atributo a
  join catalogo.registro_fuente r on r.id = a.registro_fuente_id
  join catalogo.fuente f on f.id = r.fuente_id
  where a.paid in (267, 268, 269) and a.valor_num is not null
  order by a.parte_id, a.paid, r.vigente desc, f.prioridad, a.id
)
select p.id as parte_id,
       p.part_terminology_id,
       pt.nombre as tipo_parte,
       p.descripcion,
       (select string_agg(distinct n.numero, ' ' order by n.numero) from catalogo.parte_numero n where n.parte_id = p.id) as numeros,
       (select m.valor_num from medida m where m.parte_id = p.id and m.paid = 267) as panal_alto_mm,
       (select m.valor_num from medida m where m.parte_id = p.id and m.paid = 269) as panal_largo_mm,
       (select m.valor_num from medida m where m.parte_id = p.id and m.paid = 268) as panal_ancho_mm,
       (select count(*) from catalogo.parte_aplicacion ap where ap.parte_id = p.id) as n_aplicaciones,
       (select count(distinct r.fuente_id) from catalogo.registro_fuente r where r.parte_id = p.id and r.vigente) as n_fuentes,
       (select i.url from catalogo.parte_imagen i where i.parte_id = p.id order by i.orden limit 1) as imagen_url
from catalogo.parte p
join ref.part_terminology pt using (part_terminology_id)
where p.estado = 'ACTIVA';

grant execute on function carga.fn_cerrar_corrida(bigint, numeric) to grp_consolidacion_carga;
grant select on catalogo.v_parte_busqueda to grp_app_lectura, grp_exploracion, grp_consolidacion_carga;
