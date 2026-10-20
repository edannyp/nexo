-- Usuario del agente de revisión del catálogo (Consolidación → verificaciones de Nexo), con permisos mínimos (ADR 0012, 0017).
-- Ejecutar UNA vez en la base nexo, como superusuario, DESPUÉS de que la API haya migrado a 0011:
--   psql -h <servidor> -U postgres -d nexo -v clave='<contraseña larga>' -f deploy/sql/usuario-agente-revision-catalogo.sql
-- La contraseña se pasa al ejecutar: nunca se guarda en el repositorio.

create role agente_revision_catalogo login password :'clave';
grant connect on database nexo to agente_revision_catalogo;

-- Solo tres funciones: qué partes revisar, qué se validó en cada artículo y cuáles cambiaron. Corren con los permisos de su dueño:
-- el agente no lee ni escribe tablas de Nexo.
grant usage on schema app to agente_revision_catalogo;
grant execute on function app.fn_partes_emparejadas(), app.fn_datos_emparejamiento(bigint[]),
  app.fn_registrar_cambios_catalogo(jsonb) to agente_revision_catalogo;
