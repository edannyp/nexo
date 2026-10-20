-- Cómo quedó la base local de Nexo después de correr el agente (ejecutar como postgres).
\echo '== Partes que el agente debe revisar'
select * from app.fn_partes_emparejadas();

\echo '== Verificaciones CAMBIO_CATALOGO (lo que verá el supervisor)'
select a.item_code, t.detalle ->> 'estado' as cambio, t.detalle ->> 'nota' as nota, t.estado, t.creada_en
from app.tarea_verificacion t join app.articulo a on a.id = t.articulo_id
where t.origen = 'CAMBIO_CATALOGO' order by t.id;
