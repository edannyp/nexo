-- Nexo 0020 · Solicitud de campos y campos oficiales (ADR 0030)
-- Un operador o supervisor que trabaja un artículo puede solicitar un campo propio que falta. Queda PROPUESTO: aparece en la
-- ficha de todos los artículos de ese tipo de parte y se puede capturar, pero no es oficial (no puede ser obligatorio). Quien
-- tiene CONFIGURAR_FICHA lo aprueba (OFICIAL) o lo rechaza con motivo (RECHAZADO: sale de la ficha y lo capturado se conserva).
-- Los atributos de AutoCare y los campos propios creados desde la configuración son oficiales.

create type meta.estado_campo as enum ('OFICIAL', 'PROPUESTO', 'RECHAZADO');

alter table meta.atributo_config
  add column estado           meta.estado_campo not null default 'OFICIAL',
  add column motivo_solicitud text check (length(motivo_solicitud) between 1 and 500),
  add column solicitado_por   bigint references app.usuario,
  add column solicitado_en    timestamptz,
  add column revisado_por     bigint references app.usuario,
  add column revisado_en      timestamptz,
  add column motivo_rechazo   text check (length(motivo_rechazo) between 1 and 500),
  add constraint solo_propios_se_proponen check (estado = 'OFICIAL' or paid >= 1000000),
  add constraint propuesto_no_obligatorio check (estado <> 'PROPUESTO' or not obligatorio),
  add constraint rechazado_fuera_de_la_ficha check (estado <> 'RECHAZADO' or (not habilitado and motivo_rechazo is not null)),
  add constraint solicitud_completa check ((solicitado_por is null) = (solicitado_en is null));

comment on column meta.atributo_config.estado is
  'OFICIAL (AutoCare o aprobado), PROPUESTO (lo solicitó quien trabaja artículos; se captura pero no es oficial) o RECHAZADO (ADR 0030).';
comment on column meta.atributo_config.motivo_solicitud is 'Por qué se necesita el campo, según quien lo solicitó.';
comment on column meta.atributo_config.motivo_rechazo is 'Por qué no se aprobó. Lo capturado se conserva oculto por si se reconsidera.';
