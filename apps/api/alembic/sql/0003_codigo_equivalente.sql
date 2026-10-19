-- Nexo 0003 · Código equivalente de fabricados (pregunta 24, ADR 0018)
-- La equivalencia ya no bloquea la validación del fabricado. En la revisión de fabricados el operador captura un código
-- equivalente (texto libre: ItemCode, OEM o proveedor) y un supervisor lo valida cuando el artículo tiene foto propia validada.

alter table app.articulo drop column justificacion_sin_equivalente;

alter table app.articulo
  add column codigo_equivalente              text,
  add column codigo_equivalente_por          bigint references app.usuario,
  add column codigo_equivalente_en           timestamptz,
  add column codigo_equivalente_validado_por bigint references app.usuario,
  add column codigo_equivalente_validado_en  timestamptz,
  add constraint codigo_equivalente_validado check (codigo_equivalente_validado_por is null or codigo_equivalente is not null);

comment on column app.articulo.codigo_equivalente is
  'APP: código equivalente del fabricado capturado en la revisión de fabricados (ItemCode, OEM o proveedor). Sugerencia inicial: codigo_anterior.';

-- Cambiar el código invalida su validación. Si es el ItemCode de un importado de la misma categoría, se sugiere la equivalencia.
create function app.al_cambiar_codigo_equivalente() returns trigger language plpgsql as $$
begin
  new.codigo_equivalente := upper(meta.limpiar(new.codigo_equivalente));
  if new.codigo_equivalente is not distinct from old.codigo_equivalente then
    return new;
  end if;
  new.codigo_equivalente_por := nullif(current_setting('app.usuario_id', true), '')::bigint;
  new.codigo_equivalente_en := case when new.codigo_equivalente is not null then now() end;
  new.codigo_equivalente_validado_por := null;
  new.codigo_equivalente_validado_en := null;
  insert into app.articulo_equivalencia (fabricado_id, importado_id, origen)
  select new.id, i.id, 'MANUAL' from app.articulo i
  where i.item_code = new.codigo_equivalente and i.linea = 'IMPORTADO' and i.categoria_id = new.categoria_id
  on conflict (fabricado_id, importado_id) do nothing;
  return new;
end $$;

create trigger codigo_equivalente before update of codigo_equivalente on app.articulo
  for each row execute function app.al_cambiar_codigo_equivalente();

create type app.estado_codigo_equivalente as enum ('SIN_CODIGO', 'ESPERA_FOTO', 'LISTO_PARA_VALIDAR', 'VALIDADO');

-- Bandeja de revisión de fabricados
create view app.v_revision_fabricados as
select a.id, a.item_code, a.descripcion, a.categoria_id, a.estado, a.codigo_anterior, a.codigo_equivalente,
       a.codigo_equivalente_por, a.codigo_equivalente_en, a.codigo_equivalente_validado_por, a.codigo_equivalente_validado_en,
       f.fotos_validadas,
       case when a.codigo_equivalente is null then 'SIN_CODIGO'
            when a.codigo_equivalente_validado_por is not null then 'VALIDADO'
            when f.fotos_validadas = 0 then 'ESPERA_FOTO'
            else 'LISTO_PARA_VALIDAR' end::app.estado_codigo_equivalente as estado_codigo
from app.articulo a
cross join lateral (select count(*)::int as fotos_validadas from app.articulo_imagen i
                    where i.articulo_id = a.id and i.origen = 'PROPIA' and i.validada) f
where a.linea = 'FABRICADO' and a.activo;

create function app.fn_validar_codigo_equivalente(p_articulo_id bigint, p_usuario_id bigint)
returns app.articulo language plpgsql security definer as $$
declare a app.articulo;
begin
  if not exists (select 1 from app.usuario_rol where usuario_id = p_usuario_id and rol in ('SUPERVISOR', 'ADMINISTRADOR')) then
    raise exception 'ROL_INSUFICIENTE: el código equivalente lo valida un supervisor o administrador' using errcode = '42501';
  end if;
  select * into a from app.articulo where id = p_articulo_id for update;
  if a.codigo_equivalente is null then
    raise exception 'SIN_CODIGO_EQUIVALENTE: el artículo % no tiene código equivalente', a.item_code using errcode = 'P0001';
  end if;
  if not exists (select 1 from app.articulo_imagen where articulo_id = a.id and origen = 'PROPIA' and validada) then
    raise exception 'SIN_FOTO_VALIDADA: el código equivalente se valida con una foto propia validada (%)', a.item_code using errcode = 'P0001';
  end if;
  update app.articulo set codigo_equivalente_validado_por = p_usuario_id, codigo_equivalente_validado_en = now()
  where id = a.id returning * into a;
  return a;
end $$;

-- Requisitos para POR_VALIDAR: la equivalencia ya no es obligatoria (pregunta 24)
create or replace function app.fn_requisitos_por_validar(p_articulo_id bigint) returns text[]
language sql stable as $$
  select array_remove(
    array[
      case when a.part_terminology_id is null then 'TIPO_DE_PARTE' end,
      case when not exists (select 1 from app.articulo_aplicacion x where x.articulo_id = a.id and x.confirmado_por is not null)
            and not exists (select 1 from app.articulo_parte x where x.articulo_id = a.id)
           then 'APLICACION_O_EMPAREJAMIENTO' end
    ]
    || coalesce((select array_agg('ATRIBUTO:' || r.nombre order by r.paid)
                 from meta.atributo_requerido r
                 where r.part_terminology_id = a.part_terminology_id
                   and not exists (select 1 from app.articulo_atributo t
                                   where t.articulo_id = a.id and t.paid = r.paid and t.confirmado_por is not null)), '{}'),
    null)
  from app.articulo a where a.id = p_articulo_id
$$;
