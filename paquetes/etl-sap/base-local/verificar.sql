-- Cómo quedó la base local después de correr el ETL (ejecutar como postgres).
\echo '== Lotes'
select lote_id, iniciado_en, procesado_en, resultado from staging.lote order by lote_id desc limit 5;

\echo '== Artículos por categoría y línea (activos / total)'
select c.codigo_sap, c.nombre, a.linea, count(*) filter (where a.activo) as activos, count(*) as total
from app.articulo a join app.categoria c on c.id = a.categoria_id
group by 1, 2, 3 order by 1, 3;

\echo '== Inactivos por motivo (SAP_CONGELADO, NOMBRE_INACTIVO, FUERA_DE_ALCANCE, NO_EN_SAP)'
select motivo_inactivo, count(*) from app.articulo where not activo group by 1 order by 2 desc;

\echo '== Hallazgos de calidad de SAP (lo que Nexo reporta para corregir en SAP)'
select tipo, count(*) from app.hallazgo_calidad_sap where corregido_en is null group by 1 order by 2 desc;

\echo '== Medidas convertidas a mm (muestra)'
select item_code, panal_alto_mm, panal_largo_mm, panal_ancho_mm from app.articulo
where panal_alto_mm is not null order by item_code limit 5;
