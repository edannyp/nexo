import { establecerCsrf, getObtenerSesionQueryKey, ProblemaError, useIniciarSesion } from '@nexo/api-client';
import { useQueryClient } from '@tanstack/react-query';
import { Navigate, useNavigate, useSearch } from '@tanstack/react-router';
import { Eye, EyeOff } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import { BotonTema } from '@/app/BotonTema';
import { useSesion } from '@/app/sesion';
import { Aviso, Boton, Campo } from '@/shared/ui';

/** Solo rutas internas: evita redirigir a otro sitio después de entrar. */
export const destinoSeguro = (d: unknown) =>
  typeof d === 'string' && d.startsWith('/') && !d.startsWith('//') && !d.startsWith('/entrar') ? d : '/';

export function Entrar() {
  const sesion = useSesion();
  const { redirigir } = useSearch({ from: '/entrar' });
  const navegar = useNavigate();
  const consultas = useQueryClient();
  const entrar = useIniciarSesion();
  const [ver, setVer] = useState(false);

  if (sesion.estado === 'autenticado') return <Navigate to={destinoSeguro(redirigir)} />;

  const enviar = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const datos = new FormData(e.currentTarget);
    entrar.mutate(
      { data: { usuario: String(datos.get('usuario')), password: String(datos.get('password')) } },
      {
        onSuccess: (info) => {
          establecerCsrf(info.csrf);
          consultas.setQueryData(getObtenerSesionQueryKey(), info);
          void navegar({ to: info.usuario.debe_cambiar_password ? '/cambiar-contrasena' : destinoSeguro(redirigir) });
        },
      },
    );
  };

  const problema = entrar.error instanceof ProblemaError ? entrar.error.problema : null;

  return (
    <div className="flex min-h-dvh flex-col bg-fondo">
      <div className="flex justify-end p-3">
        <BotonTema />
      </div>
      <main className="flex flex-1 items-start justify-center px-4 pt-[8vh] sm:items-center sm:pt-0">
        <div className="w-full max-w-sm">
          <div className="mb-6 text-center">
            <img src="/favicon.svg" alt="" className="mx-auto size-12" />
            <h1 className="mt-3 text-2xl font-semibold tracking-tight">Nexo</h1>
            <p className="text-sm text-suave">Puente de gobernanza del artículo</p>
          </div>
          <form
            onSubmit={enviar}
            className="space-y-4 rounded-lg border border-borde bg-superficie p-5 shadow-sm"
            noValidate
          >
            {problema && (
              <Aviso tono="error" titulo={problema.title}>
                {problema.detail}
              </Aviso>
            )}
            {entrar.isError && !problema && <Aviso tono="error" titulo="No se pudo conectar con el servidor" />}
            <Campo etiqueta="Usuario" name="usuario" autoComplete="username" autoCapitalize="none" required autoFocus />
            <div className="relative">
              <Campo
                etiqueta="Contraseña"
                name="password"
                type={ver ? 'text' : 'password'}
                autoComplete="current-password"
                required
                className="[&_input]:pr-11"
              />
              <button
                type="button"
                onClick={() => setVer((v) => !v)}
                className="absolute right-1 bottom-1 grid size-8 place-items-center rounded-md text-suave hover:text-texto"
                aria-label={ver ? 'Ocultar contraseña' : 'Mostrar contraseña'}
              >
                {ver ? <EyeOff className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
              </button>
            </div>
            <Boton type="submit" className="w-full" cargando={entrar.isPending}>
              Entrar
            </Boton>
          </form>
          <p className="mt-4 text-center text-xs text-suave">
            ¿Olvidaste tu contraseña? Pide a un administrador que la restablezca.
          </p>
        </div>
      </main>
    </div>
  );
}
