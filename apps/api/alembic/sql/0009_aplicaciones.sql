-- Nexo 0009 · Aplicaciones: submodelo y motor obligatorios para confirmar una aplicación de vehículo
-- (decisión UX 4, architecture/ux/propuesta.md §12). Las de equipo (maquinaria) no los llevan. Las sugeridas (heredadas de un
-- equivalente o del catálogo maestro) pueden estar incompletas: se completan antes de confirmarlas.

alter table app.articulo_aplicacion add constraint aplicacion_vehiculo_completa check (
  confirmado_por is null or equipment_base_id is not null or (sub_model_id is not null and engine_config_id is not null)
);

comment on constraint aplicacion_vehiculo_completa on app.articulo_aplicacion is
  'Una aplicación de vehículo confirmada lleva submodelo y motor (decisión UX 4).';
