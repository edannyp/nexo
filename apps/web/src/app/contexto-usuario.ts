import type { UsuarioSesion } from '@nexo/api-client';
import { createContext, useContext } from 'react';

export const UsuarioContexto = createContext<UsuarioSesion | null>(null);

/** Usuario autenticado. Solo se usa dentro del armazón, que garantiza que hay sesión. */
export function useUsuario(): UsuarioSesion {
  const u = useContext(UsuarioContexto);
  if (!u) throw new Error('useUsuario debe usarse dentro del armazón de la APP');
  return u;
}
