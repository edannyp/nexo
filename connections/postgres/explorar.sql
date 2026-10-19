-- Consultas de exploración para cualquier base Postgres (AutoCare, Consolidación, MercadoExterno).

-- Tablas con su tamaño y filas estimadas
select schemaname, relname as tabla, n_live_tup as filas_estimadas,
       pg_size_pretty(pg_total_relation_size(relid)) as tamano
from pg_stat_user_tables
order by n_live_tup desc;

-- Columnas de una tabla
select column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public' and table_name = 'NOMBRE_TABLA'
order by ordinal_position;

-- Llaves foráneas (para entender relaciones)
select tc.table_name, kcu.column_name, ccu.table_name as tabla_ref, ccu.column_name as columna_ref
from information_schema.table_constraints tc
join information_schema.key_column_usage kcu on tc.constraint_name = kcu.constraint_name
join information_schema.constraint_column_usage ccu on ccu.constraint_name = tc.constraint_name
where tc.constraint_type = 'FOREIGN KEY';
