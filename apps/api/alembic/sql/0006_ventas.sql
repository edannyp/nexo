-- Nexo 0006 · Indicadores de venta relativos (ADR 0022)
-- Copia de apoyo desde ClickHouse (rlt_mov.mart_ventas_articulo_mes, rlt_ml.latest_clasificacion_abcxyz), refrescada por
-- `python -m nexo_api.cli actualizar-ventas`. Solo UNIDADES: nunca montos ni precios.

create table meta.parametro (
  clave       text primary key,
  valor       jsonb not null,
  descripcion text not null
);
insert into meta.parametro values
  ('ventas.meses_periodo', '12', 'Meses completos que forman el periodo de los indicadores de venta (y el periodo anterior para la tendencia).'),
  ('ventas.umbral_a', '0.8', 'Participación acumulada hasta la que un artículo es clase A dentro de su tipo.'),
  ('ventas.umbral_b', '0.95', 'Participación acumulada hasta la que un artículo es clase B dentro de su tipo; el resto es C.');

create table app.venta_mensual (
  item_code text not null,
  mes       date not null check (mes = date_trunc('month', mes)),
  unidades  numeric(14,2) not null,
  primary key (item_code, mes)
);
create index on app.venta_mensual (mes, item_code);
comment on table app.venta_mensual is 'Unidades vendidas por artículo y mes (todas las sucursales). Copia de apoyo de ClickHouse (ADR 0022).';

create table app.venta_referencia (
  item_code       text primary key,
  abcxyz_empresa  text,              -- clasificación global de la empresa (rlt_ml), solo como referencia
  ultima_venta    date,
  actualizado_en  timestamptz not null default now()
);

create table meta.carga_ventas (
  id            bigint generated always as identity primary key,
  ejecutada_en  timestamptz not null default now(),
  meses         integer not null,
  articulos     integer not null,
  filas         integer not null
);

-- Indicadores por artículo activo, calculados DENTRO de su tipo (categoría + línea). Periodo = últimos N meses completos.
create view app.v_indicador_venta as
with p as (
  select (select valor::int from meta.parametro where clave = 'ventas.meses_periodo') as meses,
         (select valor::numeric from meta.parametro where clave = 'ventas.umbral_a') as umbral_a,
         (select valor::numeric from meta.parametro where clave = 'ventas.umbral_b') as umbral_b,
         date_trunc('month', current_date)::date as fin
),
-- Primero se suman las ventas de los dos periodos (índice por mes) y luego se cruzan con los artículos activos
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
         sum(unidades) over (partition by categoria_id, linea order by unidades desc, item_code
                             rows between unbounded preceding and current row) as acumulado,
         count(*) over (partition by categoria_id, linea) as n_tipo,
         rank() over (partition by categoria_id, linea order by unidades desc) as posicion
  from u
)
select r.articulo_id, r.item_code, r.categoria_id, r.linea, r.unidades, r.unidades_previas,
       round(r.unidades / nullif(r.total_tipo, 0), 6) as participacion,
       case when r.unidades = 0 then null
            -- Un artículo es A si la venta acumulada ANTES de él aún no llegaba al umbral (el primero siempre es A)
            when (r.acumulado - r.unidades) < p.umbral_a * r.total_tipo then 'A'
            when (r.acumulado - r.unidades) < p.umbral_b * r.total_tipo then 'B'
            else 'C' end as clase,
       case when r.unidades = 0 then null else round(r.posicion::numeric / r.n_tipo, 4) end as top_pct,  -- 0.08 = está en el 8 % que más vende
       case when r.unidades_previas = 0 then null
            else round((r.unidades - r.unidades_previas) / r.unidades_previas, 4) end as tendencia,
       ref.abcxyz_empresa, ref.ultima_venta
from r cross join p
left join app.venta_referencia ref on ref.item_code = r.item_code;

comment on view app.v_indicador_venta is
  'Indicadores relativos de venta por artículo activo dentro de su tipo: clase ABC, top %, participación y tendencia (ADR 0022).';
