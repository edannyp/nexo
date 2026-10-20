import { establecerCsrf, useCerrarSesion } from '@nexo/api-client';
import { useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from '@tanstack/react-router';
import { KeyRound, LogOut } from 'lucide-react';

import { useUsuario } from './contexto-usuario';
import { iniciales } from './sesion';

const NOMBRE_ROL: Record<string, string> = {
  OPERADOR: 'Operador',
  SUPERVISOR: 'Supervisor',
  ADMINISTRADOR: 'Administrador',
  FOTOS: 'Fotos',
};

/** Menú del usuario (popover nativo): quién soy, cambiar contraseña, salir. */
export function MenuUsuario() {
  const usuario = useUsuario();
  const consultas = useQueryClient();
  const navegar = useNavigate();
  const salir = useCerrarSesion();

  const cerrarSesion = () =>
    salir.mutate(undefined, {
      onSettled: () => {
        establecerCsrf(null);
        consultas.clear();
        void navegar({ to: '/entrar' });
      },
    });

  return (
    <>
      <button
        type="button"
        popoverTarget="menu-usuario"
        className="grid size-9 place-items-center rounded-full bg-primario text-xs font-semibold text-primario-texto"
        aria-label={`Menú de ${usuario.nombre}`}
      >
        {iniciales(usuario.nombre)}
      </button>
      <div
        id="menu-usuario"
        popover="auto"
        className="fixed inset-auto top-14 right-3 m-0 w-64 rounded-lg border border-borde bg-superficie p-2 text-texto shadow-lg"
      >
        <div className="border-b border-borde px-2 pt-1 pb-2">
          <p className="font-medium">{usuario.nombre}</p>
          <p className="text-sm text-suave">@{usuario.usuario}</p>
          <p className="mt-1 text-xs text-suave">{usuario.roles.map((r) => NOMBRE_ROL[r] ?? r).join(' · ')}</p>
        </div>
        <Link
          to="/cambiar-contrasena"
          className="mt-1 flex items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-superficie-2"
        >
          <KeyRound className="size-4" aria-hidden /> Cambiar contraseña
        </Link>
        <button
          type="button"
          onClick={cerrarSesion}
          className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-superficie-2"
        >
          <LogOut className="size-4" aria-hidden /> Cerrar sesión
        </button>
      </div>
    </>
  );
}
