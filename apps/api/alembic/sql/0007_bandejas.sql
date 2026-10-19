-- Nexo 0007 · Bandejas: "Siguiente" con doble control y prioridad, reservas, búsqueda y vistas guardadas
-- (architecture/ux/propuesta.md §6.2–6.5, context/workflow-estados.md reglas 3 y 8)

-- Quién envió el artículo a revisión por última vez (actor de la última transición a POR_VALIDAR)
create function app.fn_enviado_por(p_articulo_id bigint) returns text
language sql stable as $$
  select actor from audit.bitacora_articulo
  where articulo_id = p_articulo_id and tipo = 'TRANSICION' and estado_destino = 'POR_VALIDAR'
  order by id desc limit 1
$$;

-- "Siguiente": reserva el próximo artículo de la bandeja del tipo elegido.
--  · Prioridad: primero RECHAZADO (traen motivo), luego por clase de venta (A, B, C, sin venta) y participación, luego antigüedad.
--  · Doble control: en POR_VALIDAR nunca entrega lo que el propio usuario envió a revisión (no podría validarlo).
--  · Si el usuario ya tiene uno reservado y vigente en esa bandeja, se lo devuelve.
create or replace function app.fn_tomar_siguiente(
  p_usuario_id   bigint,
  p_estados      app.estado_articulo[],
  p_categoria_id smallint,
  p_linea        app.linea,
  p_minutos      integer default 30
) returns app.articulo
language plpgsql as $$
declare a app.articulo;
begin
  select * into a from app.articulo
  where asignado_a = p_usuario_id and asignado_hasta > now() and activo and estado = any (p_estados)
    and categoria_id = p_categoria_id and linea = p_linea
  limit 1;
  if found then return a; end if;

  update app.articulo set asignado_a = p_usuario_id, asignado_hasta = now() + make_interval(mins => p_minutos)
  where id = (
    select x.id from app.articulo x
    left join (select articulo_id, clase, participacion from app.v_indicador_venta
               where categoria_id = p_categoria_id and linea = p_linea) v on v.articulo_id = x.id
    where x.activo and x.estado = any (p_estados) and x.categoria_id = p_categoria_id and x.linea = p_linea
      and (x.asignado_hasta is null or x.asignado_hasta < now())
      and not (x.estado = 'POR_VALIDAR' and app.fn_enviado_por(x.id) = p_usuario_id::text)
    order by (x.estado = 'RECHAZADO') desc, coalesce(v.clase, 'Z'), v.participacion desc nulls last, x.actualizado_en, x.id
    for update of x skip locked
    limit 1
  )
  returning * into a;
  return a;  -- null si la bandeja está vacía
end $$;

-- Tomar un artículo concreto (desde Explorar o la búsqueda): si está libre, vencido o ya es suyo, queda reservado.
create function app.fn_reservar(p_articulo_id bigint, p_usuario_id bigint, p_minutos integer default 30)
returns timestamptz language plpgsql as $$
declare a app.articulo; v_nombre text;
begin
  select * into a from app.articulo where id = p_articulo_id for update;
  if not found then
    raise exception 'ARTICULO_NO_EXISTE: %', p_articulo_id using errcode = 'P0002';
  end if;
  if not a.activo then
    raise exception 'ARTICULO_INACTIVO: % (%)', a.item_code, a.motivo_inactivo using errcode = 'P0001';
  end if;
  if a.asignado_hasta > now() and a.asignado_a <> p_usuario_id then
    select nombre into v_nombre from app.usuario where id = a.asignado_a;
    raise exception 'RESERVADO_POR_OTRO: % lo está trabajando', v_nombre using errcode = 'P0001';
  end if;
  update app.articulo set asignado_a = p_usuario_id, asignado_hasta = now() + make_interval(mins => p_minutos)
  where id = p_articulo_id returning asignado_hasta into a.asignado_hasta;
  return a.asignado_hasta;
end $$;

-- Latido: renueva la reserva de quien la tiene. Si ya no es suya (venció y la tomó otro), lo dice.
create function app.fn_renovar_reserva(p_articulo_id bigint, p_usuario_id bigint, p_minutos integer default 30)
returns timestamptz language plpgsql as $$
declare v_hasta timestamptz;
begin
  update app.articulo set asignado_hasta = now() + make_interval(mins => p_minutos)
  where id = p_articulo_id and asignado_a = p_usuario_id and asignado_hasta > now()
  returning asignado_hasta into v_hasta;
  if v_hasta is null then
    raise exception 'RESERVA_PERDIDA: el artículo ya no está reservado por ti' using errcode = 'P0001';
  end if;
  return v_hasta;
end $$;

-- Soltar: devuelve el artículo a la bandeja sin cambiar su estado (solo quien lo tiene).
create function app.fn_soltar_reserva(p_articulo_id bigint, p_usuario_id bigint) returns boolean
language sql as $$
  update app.articulo set asignado_a = null, asignado_hasta = null
  where id = p_articulo_id and asignado_a = p_usuario_id
  returning true
$$;

-- Búsqueda (pg_trgm): descripción, códigos y número de parte del proveedor; tolerante a errores y fragmentos
create index articulo_descripcion_trgm on app.articulo using gin (descripcion gin_trgm_ops);
create index articulo_item_code_trgm on app.articulo using gin (item_code gin_trgm_ops);
create index articulo_numero_parte_trgm on app.articulo using gin (numero_parte_proveedor gin_trgm_ops);
create index articulo_codigo_anterior on app.articulo using gin (codigo_anterior);

-- Vistas guardadas de Explorar por usuario (filtros, columnas y orden)
create table app.vista_guardada (
  id          bigint generated always as identity primary key,
  usuario_id  bigint not null references app.usuario,
  pantalla    text not null default 'explorar',
  nombre      text not null check (length(nombre) between 1 and 60),
  parametros  jsonb not null,
  creada_en   timestamptz not null default now(),
  unique (usuario_id, pantalla, nombre)
);
