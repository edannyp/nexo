-- Nexo 0018 · Emparejamiento fuera del workflow (ADR 0028)
-- Emparejar con el catálogo maestro deja de ser un paso del operador: se hace en la sección Emparejamiento, solo con este permiso
-- especial por usuario (como VER_ANALISIS_VENTAS, ADR 0022), sobre cualquier artículo activo y sin reservarlo.

alter type app.permiso add value if not exists 'EMPAREJAR_CATALOGO';

comment on table app.usuario_permiso is
  'Permisos especiales por usuario, además del rol (ADR 0022, 0028): VER_ANALISIS_VENTAS, EMPAREJAR_CATALOGO.';
