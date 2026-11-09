-- Consolidación V005 · Búsqueda rápida (ADR 0026)
-- La vista de V004 calculaba la medida de mayor prioridad de TODAS las partes y luego buscaba la de cada parte en esa lista: con
-- datos reales (12 100 partes) una búsqueda tardaba ~13 s. Ahora cada parte toma sus medidas por el índice (parte_id, paid):
-- mismos valores, ~0,1 s. Mismas columnas que antes (la APP no cambia).

create index if not exists parte_imagen_parte_id_idx on catalogo.parte_imagen (parte_id, orden);

create or replace view catalogo.v_parte_busqueda as
select p.id as parte_id,
       p.part_terminology_id,
       pt.nombre as tipo_parte,
       p.descripcion,
       (select string_agg(distinct n.numero, ' ' order by n.numero) from catalogo.parte_numero n where n.parte_id = p.id) as numeros,
       m.alto as panal_alto_mm, m.largo as panal_largo_mm, m.ancho as panal_ancho_mm,
       (select count(*) from catalogo.parte_aplicacion ap where ap.parte_id = p.id) as n_aplicaciones,
       (select count(distinct r.fuente_id) from catalogo.registro_fuente r where r.parte_id = p.id and r.vigente) as n_fuentes,
       (select i.url from catalogo.parte_imagen i where i.parte_id = p.id order by i.orden limit 1) as imagen_url
from catalogo.parte p
join ref.part_terminology pt using (part_terminology_id)
cross join lateral (
  select max(x.valor_num) filter (where x.paid = 267) as alto, max(x.valor_num) filter (where x.paid = 269) as largo,
         max(x.valor_num) filter (where x.paid = 268) as ancho
  from (select distinct on (a.paid) a.paid, a.valor_num
        from catalogo.parte_atributo a
        join catalogo.registro_fuente r on r.id = a.registro_fuente_id
        join catalogo.fuente f on f.id = r.fuente_id
        where a.parte_id = p.id and a.paid in (267, 268, 269) and a.valor_num is not null
        order by a.paid, r.vigente desc, f.prioridad, a.id) x
) m
where p.estado = 'ACTIVA';

grant select on catalogo.v_parte_busqueda to grp_app_lectura, grp_exploracion, grp_consolidacion_carga;
