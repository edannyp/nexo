-- Nexo 0005 · Autenticación propia (ADR 0015) y permisos especiales por usuario (ADR 0022)
-- Las sesiones viven en Redis; aquí quedan usuarios, permisos y el registro de accesos.

-- Permisos especiales, además del rol (un usuario de cualquier rol puede tenerlos o no)
create type app.permiso as enum ('VER_ANALISIS_VENTAS');

create table app.usuario_permiso (
  usuario_id   bigint not null references app.usuario,
  permiso      app.permiso not null,
  otorgado_por bigint references app.usuario,
  otorgado_en  timestamptz not null default now(),
  primary key (usuario_id, permiso)
);

-- Registro de accesos: lo que pasa con la sesión de cada usuario (no los cambios de datos, que van en auditoria_evento)
create type audit.tipo_acceso as enum (
  'ALTA', 'ENTRADA', 'ENTRADA_FALLIDA', 'BLOQUEO', 'SALIDA', 'CAMBIO_PASSWORD', 'RESTABLECER_PASSWORD', 'SESIONES_CERRADAS', 'DESBLOQUEO'
);

create table audit.evento_acceso (
  id          bigint generated always as identity primary key,
  usuario_id  bigint references app.usuario,
  usuario     text not null,                 -- lo que se escribió al entrar (puede no existir)
  tipo        audit.tipo_acceso not null,
  actor_id    bigint references app.usuario, -- quien lo hizo, si fue un administrador
  ip          inet,
  agente      text,
  creado_en   timestamptz not null default now()
);
create index on audit.evento_acceso (usuario_id, creado_en);

-- Auditoría de usuarios sin secretos: igual que audit.registrar() pero sin el hash de la contraseña
create function audit.registrar_sin_secretos() returns trigger language plpgsql as $$
declare v_antes jsonb := case when tg_op <> 'INSERT' then to_jsonb(old) - 'password_hash' end;
        v_despues jsonb := case when tg_op <> 'DELETE' then to_jsonb(new) - 'password_hash' end;
begin
  if tg_op = 'UPDATE' and v_antes = v_despues then
    return null;                                 -- solo cambió la contraseña o un contador: va en evento_acceso
  end if;
  insert into audit.auditoria_evento (entidad, entidad_id, accion, actor, antes, despues)
  values (tg_table_schema || '.' || tg_table_name, (coalesce(v_despues, v_antes) ->> 'id')::bigint, tg_op,
          coalesce(nullif(current_setting('app.usuario_id', true), ''), session_user), v_antes, v_despues);
  return null;
end $$;

create trigger auditoria after insert or update or delete on app.usuario
  for each row execute function audit.registrar_sin_secretos();
create trigger auditoria after insert or update or delete on app.usuario_rol
  for each row execute function audit.registrar();
create trigger auditoria after insert or update or delete on app.usuario_permiso
  for each row execute function audit.registrar();

comment on table app.usuario_permiso is 'Permisos especiales por usuario, además del rol (ADR 0022). Ej.: VER_ANALISIS_VENTAS.';
comment on table audit.evento_acceso is 'Entradas, intentos fallidos, bloqueos y cambios de contraseña (ADR 0015).';
