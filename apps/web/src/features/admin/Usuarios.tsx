import {
  getListarUsuariosQueryKey,
  ProblemaError,
  useCerrarSesionesUsuario,
  useCrearUsuario,
  useDesbloquearUsuario,
  useListarUsuarios,
  useModificarUsuario,
  useRestablecerPassword,
  type Permiso,
  type Rol,
  type UsuarioAdmin,
} from '@nexo/api-client';
import { useQueryClient } from '@tanstack/react-query';
import { Check, Copy, KeyRound, LogOut, LockOpen, Pencil, Plus } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import { useUsuario } from '@/app/contexto-usuario';
import { Aviso, Boton, Campo, Dialogo, Insignia } from '@/shared/ui';

const ROLES: { valor: Rol; nombre: string; descripcion: string }[] = [
  { valor: 'OPERADOR', nombre: 'Operador', descripcion: 'Completa artículos y los envía a revisión' },
  { valor: 'SUPERVISOR', nombre: 'Supervisor', descripcion: 'Valida o rechaza y atiende verificaciones' },
  { valor: 'ADMINISTRADOR', nombre: 'Administrador', descripcion: 'Usuarios, configuración y reaperturas' },
  { valor: 'FOTOS', nombre: 'Fotos', descripcion: 'Sube las fotos propias de los artículos' },
];
const PERMISOS: { valor: Permiso; nombre: string }[] = [
  { valor: 'VER_ANALISIS_VENTAS', nombre: 'Ver análisis de ventas' },
];

const fecha = new Intl.DateTimeFormat('es-GT', { dateStyle: 'medium', timeStyle: 'short' });
const bloqueado = (u: UsuarioAdmin) => !!u.bloqueado_hasta && new Date(u.bloqueado_hasta) > new Date();

function Estado({ u }: { u: UsuarioAdmin }) {
  if (!u.activo) return <Insignia className="text-suave">Inactivo</Insignia>;
  if (bloqueado(u)) return <Insignia className="border-rechazado/50 text-rechazado">Bloqueado</Insignia>;
  if (u.debe_cambiar_password)
    return <Insignia className="border-por-validar/50 text-por-validar">Contraseña temporal</Insignia>;
  return <Insignia className="border-validado/50 text-validado">Activo</Insignia>;
}

function mensaje(error: unknown) {
  return error instanceof ProblemaError
    ? error.problema
    : { title: 'No se pudo completar la acción', detail: undefined };
}

/** Contraseña temporal: se muestra una sola vez, con botón para copiarla. */
function Temporal({ usuario, password }: { usuario: string; password: string }) {
  const [copiado, setCopiado] = useState(false);
  return (
    <div className="space-y-3">
      <Aviso tono="exito" titulo={`Contraseña temporal de «${usuario}»`}>
        Entrégala por un canal seguro. Se muestra solo esta vez y se pedirá cambiarla al entrar.
      </Aviso>
      <div className="flex items-center gap-2 rounded-md border border-borde bg-superficie-2 p-3">
        <code className="flex-1 font-mono text-lg tracking-wide select-all">{password}</code>
        <Boton
          variante="secundario"
          onClick={() => void navigator.clipboard?.writeText(password).then(() => setCopiado(true))}
          aria-label="Copiar contraseña"
        >
          {copiado ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
          {copiado ? 'Copiada' : 'Copiar'}
        </Boton>
      </div>
    </div>
  );
}

function CasillasAcceso({ roles, permisos }: { roles: Rol[]; permisos: Permiso[] }) {
  return (
    <>
      <fieldset className="space-y-2">
        <legend className="mb-1 text-sm font-medium">Roles</legend>
        {ROLES.map((r) => (
          <label
            key={r.valor}
            className="flex items-start gap-3 rounded-md border border-borde p-2.5 has-checked:border-primario"
          >
            <input
              type="checkbox"
              name="roles"
              value={r.valor}
              defaultChecked={roles.includes(r.valor)}
              className="mt-1 size-4"
            />
            <span>
              <span className="block text-sm font-medium">{r.nombre}</span>
              <span className="block text-xs text-suave">{r.descripcion}</span>
            </span>
          </label>
        ))}
      </fieldset>
      <fieldset className="space-y-2">
        <legend className="mb-1 text-sm font-medium">Permisos especiales</legend>
        {PERMISOS.map((p) => (
          <label key={p.valor} className="flex items-center gap-3 text-sm">
            <input
              type="checkbox"
              name="permisos"
              value={p.valor}
              defaultChecked={permisos.includes(p.valor)}
              className="size-4"
            />
            {p.nombre}
          </label>
        ))}
      </fieldset>
    </>
  );
}

function FormularioNuevo({ alTerminar }: { alTerminar: () => void }) {
  const consultas = useQueryClient();
  const crear = useCrearUsuario();
  const [creado, setCreado] = useState<{ usuario: string; password: string } | null>(null);
  const [errorRoles, setErrorRoles] = useState<string>();

  if (creado) {
    return (
      <div className="space-y-4">
        <Temporal usuario={creado.usuario} password={creado.password} />
        <Boton className="w-full" onClick={alTerminar}>
          Listo
        </Boton>
      </div>
    );
  }

  const enviar = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const d = new FormData(e.currentTarget);
    const roles = d.getAll('roles') as Rol[];
    setErrorRoles(roles.length ? undefined : 'Elige al menos un rol.');
    if (!roles.length) return;
    crear.mutate(
      {
        data: {
          usuario: String(d.get('usuario')).trim(),
          nombre: String(d.get('nombre')).trim(),
          correo: String(d.get('correo')).trim() || null,
          roles,
          permisos: d.getAll('permisos') as Permiso[],
        },
      },
      {
        onSuccess: (r) => {
          void consultas.invalidateQueries({ queryKey: getListarUsuariosQueryKey() });
          setCreado({ usuario: r.usuario.usuario, password: r.password_temporal });
        },
      },
    );
  };

  const errores = crear.error instanceof ProblemaError ? crear.error.problema.errors : undefined;
  const errorDe = (campo: string) => errores?.find((x) => x.campo === campo)?.mensaje;

  return (
    <form onSubmit={enviar} className="space-y-4" noValidate>
      {crear.isError && !errores && (
        <Aviso tono="error" titulo={mensaje(crear.error).title}>
          {mensaje(crear.error).detail}
        </Aviso>
      )}
      <Campo
        etiqueta="Usuario"
        name="usuario"
        required
        autoComplete="off"
        autoCapitalize="none"
        error={errorDe('usuario')}
        ayuda="Letras, números, punto, guion o guion bajo. Ej.: ana.lopez"
      />
      <Campo etiqueta="Nombre completo" name="nombre" required error={errorDe('nombre')} />
      <Campo etiqueta="Correo (opcional)" name="correo" type="email" error={errorDe('correo')} />
      <CasillasAcceso roles={['OPERADOR']} permisos={[]} />
      {errorRoles && <p className="text-sm text-rechazado">{errorRoles}</p>}
      <Boton type="submit" className="w-full" cargando={crear.isPending}>
        Crear usuario
      </Boton>
    </form>
  );
}

function FormularioEditar({ u, alTerminar }: { u: UsuarioAdmin; alTerminar: () => void }) {
  const consultas = useQueryClient();
  const modificar = useModificarUsuario();

  const enviar = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const d = new FormData(e.currentTarget);
    modificar.mutate(
      {
        usuarioId: u.id,
        data: {
          nombre: String(d.get('nombre')).trim(),
          correo: String(d.get('correo')).trim() || null,
          roles: d.getAll('roles') as Rol[],
          permisos: d.getAll('permisos') as Permiso[],
          activo: d.get('activo') === 'on',
        },
      },
      {
        onSuccess: () => {
          void consultas.invalidateQueries({ queryKey: getListarUsuariosQueryKey() });
          alTerminar();
        },
      },
    );
  };

  return (
    <form onSubmit={enviar} className="space-y-4" noValidate>
      {modificar.isError && (
        <Aviso tono="error" titulo={mensaje(modificar.error).title}>
          {mensaje(modificar.error).detail}
        </Aviso>
      )}
      <Campo etiqueta="Nombre completo" name="nombre" defaultValue={u.nombre} required />
      <Campo etiqueta="Correo (opcional)" name="correo" type="email" defaultValue={u.correo ?? ''} />
      <CasillasAcceso roles={u.roles} permisos={u.permisos} />
      <label className="flex items-center gap-3 text-sm">
        <input type="checkbox" name="activo" defaultChecked={u.activo} className="size-4" />
        Usuario activo (si lo desactivas, se cierran sus sesiones)
      </label>
      <Boton type="submit" className="w-full" cargando={modificar.isPending}>
        Guardar cambios
      </Boton>
    </form>
  );
}

type Accion =
  { tipo: 'nuevo' } | { tipo: 'editar'; u: UsuarioAdmin } | { tipo: 'temporal'; usuario: string; password: string };

/** Administración de usuarios (ADR 0015): alta con contraseña temporal, roles, permisos, bloqueo y sesiones. */
export function Usuarios() {
  const yo = useUsuario();
  const consultas = useQueryClient();
  const lista = useListarUsuarios();
  const restablecer = useRestablecerPassword();
  const desbloquear = useDesbloquearUsuario();
  const cerrarSesiones = useCerrarSesionesUsuario();
  const [accion, setAccion] = useState<Accion | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const refrescar = () => void consultas.invalidateQueries({ queryKey: getListarUsuariosQueryKey() });

  const acciones = (u: UsuarioAdmin) => (
    <div className="flex flex-wrap gap-1">
      <Boton
        variante="fantasma"
        className="h-8 px-2"
        onClick={() => setAccion({ tipo: 'editar', u })}
        aria-label={`Editar ${u.nombre}`}
      >
        <Pencil className="size-4" aria-hidden /> Editar
      </Boton>
      <Boton
        variante="fantasma"
        className="h-8 px-2"
        aria-label={`Restablecer la contraseña de ${u.nombre}`}
        onClick={() =>
          confirm(`¿Generar una contraseña temporal para ${u.nombre}? Se cerrarán sus sesiones.`) &&
          restablecer.mutate(
            { usuarioId: u.id },
            {
              onSuccess: (r) => (
                refrescar(),
                setAccion({ tipo: 'temporal', usuario: u.usuario, password: r.password_temporal })
              ),
            },
          )
        }
      >
        <KeyRound className="size-4" aria-hidden /> Contraseña
      </Boton>
      {bloqueado(u) && (
        <Boton
          variante="fantasma"
          className="h-8 px-2"
          onClick={() =>
            desbloquear.mutate(
              { usuarioId: u.id },
              { onSuccess: () => (refrescar(), setAviso(`${u.nombre} ya puede entrar.`)) },
            )
          }
        >
          <LockOpen className="size-4" aria-hidden /> Desbloquear
        </Boton>
      )}
      {u.id !== yo.id && u.activo && (
        <Boton
          variante="fantasma"
          className="h-8 px-2"
          onClick={() =>
            confirm(`¿Cerrar todas las sesiones de ${u.nombre}?`) &&
            cerrarSesiones.mutate(
              { usuarioId: u.id },
              { onSuccess: () => setAviso(`Se cerraron las sesiones de ${u.nombre}.`) },
            )
          }
        >
          <LogOut className="size-4" aria-hidden /> Cerrar sesiones
        </Boton>
      )}
    </div>
  );

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Usuarios</h1>
          <p className="text-sm text-suave">
            Alta, roles, permisos y acceso. No hay autorregistro: solo un administrador da de alta.
          </p>
        </div>
        <Boton onClick={() => setAccion({ tipo: 'nuevo' })}>
          <Plus className="size-4" aria-hidden /> Nuevo usuario
        </Boton>
      </header>

      {aviso && <Aviso tono="exito" titulo={aviso} />}
      {lista.isError && <Aviso tono="error" titulo="No se pudo cargar la lista de usuarios" />}

      {/* Celular: tarjetas */}
      <ul className="space-y-3 md:hidden">
        {lista.data?.map((u) => (
          <li key={u.id} className="rounded-lg border border-borde bg-superficie p-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-medium">{u.nombre}</p>
                <p className="text-sm text-suave">@{u.usuario}</p>
              </div>
              <Estado u={u} />
            </div>
            <p className="mt-2 text-xs text-suave">
              {u.roles.map((r) => ROLES.find((x) => x.valor === r)?.nombre).join(' · ')}
            </p>
            <div className="mt-2">{acciones(u)}</div>
          </li>
        ))}
      </ul>

      {/* Escritorio: tabla */}
      <div className="hidden overflow-x-auto rounded-lg border border-borde bg-superficie md:block">
        <table className="w-full text-sm">
          <thead className="border-b border-borde text-left text-suave">
            <tr>
              <th scope="col" className="px-3 py-2 font-medium">
                Usuario
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Roles y permisos
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Estado
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                Último acceso
              </th>
              <th scope="col" className="px-3 py-2 font-medium">
                <span className="sr-only">Acciones</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {lista.isPending && (
              <tr>
                <td colSpan={5} className="px-3 py-6 text-center text-suave">
                  Cargando…
                </td>
              </tr>
            )}
            {lista.data?.map((u) => (
              <tr key={u.id} className="border-b border-borde last:border-0">
                <td className="px-3 py-2">
                  <p className="font-medium">{u.nombre}</p>
                  <p className="text-suave">@{u.usuario}</p>
                </td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-1">
                    {u.roles.map((r) => (
                      <Insignia key={r}>{ROLES.find((x) => x.valor === r)?.nombre ?? r}</Insignia>
                    ))}
                    {u.permisos.map((p) => (
                      <Insignia key={p} className="border-primario/50">
                        {PERMISOS.find((x) => x.valor === p)?.nombre ?? p}
                      </Insignia>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-2">
                  <Estado u={u} />
                </td>
                <td className="px-3 py-2 text-suave tabular-nums">
                  {u.ultimo_acceso_en ? fecha.format(new Date(u.ultimo_acceso_en)) : 'Nunca'}
                </td>
                <td className="px-3 py-2">{acciones(u)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Dialogo abierto={accion?.tipo === 'nuevo'} alCerrar={() => setAccion(null)} titulo="Nuevo usuario">
        <FormularioNuevo alTerminar={() => setAccion(null)} />
      </Dialogo>
      <Dialogo abierto={accion?.tipo === 'editar'} alCerrar={() => setAccion(null)} titulo="Editar usuario">
        {accion?.tipo === 'editar' && <FormularioEditar u={accion.u} alTerminar={() => setAccion(null)} />}
      </Dialogo>
      <Dialogo abierto={accion?.tipo === 'temporal'} alCerrar={() => setAccion(null)} titulo="Contraseña restablecida">
        {accion?.tipo === 'temporal' && (
          <div className="space-y-4">
            <Temporal usuario={accion.usuario} password={accion.password} />
            <Boton className="w-full" onClick={() => setAccion(null)}>
              Listo
            </Boton>
          </div>
        )}
      </Dialogo>
    </div>
  );
}
