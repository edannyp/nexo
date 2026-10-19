-- Nexo 0008 · Ficha de atributos: traducción al español de los valores PIES (decisión UX 5, architecture/ux/propuesta.md §12)
-- PIES publica los valores en inglés; la APP muestra "Plastic (Plástico)". Las traducciones las mantiene un administrador.

create table meta.traduccion_valor (
  valid_value_id integer primary key,      -- PAdb valid_value_id (el mismo valor en cualquier atributo)
  valor_es       text not null check (length(valor_es) between 1 and 120),
  actualizado_en timestamptz not null default now()
);
comment on table meta.traduccion_valor is 'Traducción al español de los valores válidos de PIES, para mostrarlos junto al valor original.';

create trigger auditoria after insert or update or delete on meta.traduccion_valor
  for each row execute function audit.registrar();

-- Valores de la ficha del radiador (los demás se agregan desde Administración)
insert into meta.traduccion_valor (valid_value_id, valor_es) values
  (203,  'Aluminio'),
  (381,  'Cobre'),
  (287,  'Latón'),
  (890,  'Plástico'),
  (1150, 'Acero'),
  (391,  'Horizontal (flujo cruzado)'),
  (444,  'Vertical (flujo descendente)');
