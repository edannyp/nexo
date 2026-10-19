-- Exploración de SAP Business One sobre HANA. Reemplazar "SCHEMA" por la base de la compañía.

-- Grupos de artículos (candidatos a "categorías")
select "ItmsGrpCod", "ItmsGrpNam" from "SCHEMA"."OITB" order by 1;

-- Artículos por grupo
select b."ItmsGrpNam", count(*) as articulos
from "SCHEMA"."OITM" a join "SCHEMA"."OITB" b on a."ItmsGrpCod" = b."ItmsGrpCod"
group by b."ItmsGrpNam" order by 2 desc;

-- Columnas de OITM, incluidos campos de usuario U_* (posible Importado/Fabricado, medidas, etc.)
select column_name, data_type_name, length
from sys.table_columns
where schema_name = 'SCHEMA' and table_name = 'OITM'
order by position;

-- Muestra de artículos
select top 50 "ItemCode", "ItemName", "ItmsGrpCod", "FirmCode", "CardCode", "SuppCatNum", "UpdateDate"
from "SCHEMA"."OITM";

-- Fabricantes y proveedores
select "FirmCode", "FirmName" from "SCHEMA"."OMRC";
