import { establecerCsrf, useObtenerSesion, type Permiso, type Rol, type UsuarioSesion } from '@nexo/api-client';
import { useEffect } from 'react';

import type { Seccion } from './navegacion';

export type EstadoSesion =
  | { estado: 'cargando' }
  | { estado: 'anonimo' }
  | { estado: 'error' }
  | { estado: 'autenticado'; usuario: UsuarioSesion };

/** Sesión actual. 401 = sin sesión (no es un error); el token CSRF queda listo para las escrituras. */
export function useSesion(): EstadoSesion {
  const q = useObtenerSesion({ query: { retry: false, staleTime: Infinity, refetchOnWindowFocus: false } });
  useEffect(() => establecerCsrf(q.data?.csrf ?? null), [q.data?.csrf]);

  if (q.isPending) return { estado: 'cargando' };
  if (q.data) return { estado: 'autenticado', usuario: q.data.usuario };
  return q.error?.problema.status === 401 ? { estado: 'anonimo' } : { estado: 'error' };
}

export const tieneRol = (u: UsuarioSesion, roles: readonly Rol[]) => u.roles.some((r) => roles.includes(r));
export const tienePermiso = (u: UsuarioSesion, p: Permiso) => u.permisos.includes(p);

/** Si la sección se muestra al usuario: sin restricción, por rol o por permiso especial. */
export function puedeVer(u: UsuarioSesion, s: Seccion): boolean {
  if (s.permiso) return tienePermiso(u, s.permiso);
  return !s.roles || tieneRol(u, s.roles);
}

export const iniciales = (nombre: string) =>
  nombre
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('');
