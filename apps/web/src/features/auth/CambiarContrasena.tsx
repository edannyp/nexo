import { establecerCsrf, getObtenerSesionQueryKey, ProblemaError, useCambiarPassword } from '@nexo/api-client';
import { useQueryClient } from '@tanstack/react-query';
import { Link, Navigate, useNavigate } from '@tanstack/react-router';
import { useState, type FormEvent } from 'react';

import { useSesion } from '@/app/sesion';
import { Aviso, Boton, Campo } from '@/shared/ui';

const MINIMO = 12;

/** Cambio de contraseña: obligatorio con la temporal (alta o restablecimiento) y voluntario desde el menú de usuario. */
export function CambiarContrasena() {
  const sesion = useSesion();
  const navegar = useNavigate();
  const consultas = useQueryClient();
  const cambiar = useCambiarPassword();
  const [errores, setErrores] = useState<Record<string, string>>({});

  if (sesion.estado === 'anonimo') return <Navigate to="/entrar" />;
  if (sesion.estado !== 'autenticado') return null;
  const obligatorio = sesion.usuario.debe_cambiar_password;

  const enviar = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const d = new FormData(e.currentTarget);
    const actual = String(d.get('actual'));
    const nueva = String(d.get('nueva'));
    const locales: Record<string, string> = {};
    if (nueva.length < MINIMO) locales.nueva = `Debe tener al menos ${MINIMO} caracteres.`;
    if (nueva !== String(d.get('confirmacion'))) locales.confirmacion = 'No coincide con la nueva contraseña.';
    setErrores(locales);
    if (Object.keys(locales).length) return;

    cambiar.mutate(
      { data: { actual, nueva } },
      {
        onSuccess: (info) => {
          establecerCsrf(info.csrf);
          consultas.setQueryData(getObtenerSesionQueryKey(), info);
          void navegar({ to: '/' });
        },
        onError: (err) => {
          if (err instanceof ProblemaError && err.problema.errors) {
            setErrores(Object.fromEntries(err.problema.errors.map((x) => [x.campo, x.mensaje])));
          }
        },
      },
    );
  };

  const general =
    cambiar.error instanceof ProblemaError && !cambiar.error.problema.errors ? cambiar.error.problema : null;

  return (
    <main className="flex min-h-dvh items-start justify-center bg-fondo px-4 pt-[8vh] sm:items-center sm:pt-0">
      <div className="w-full max-w-sm">
        <h1 className="text-xl font-semibold">Cambiar contraseña</h1>
        <p className="mt-1 text-sm text-suave">
          {obligatorio
            ? 'Por seguridad, reemplaza la contraseña temporal antes de continuar.'
            : 'Al cambiarla se cierran tus sesiones en otros equipos.'}
        </p>
        <form onSubmit={enviar} className="mt-5 space-y-4 rounded-lg border border-borde bg-superficie p-5" noValidate>
          {general && (
            <Aviso tono="error" titulo={general.title}>
              {general.detail}
            </Aviso>
          )}
          <Campo
            etiqueta={obligatorio ? 'Contraseña temporal' : 'Contraseña actual'}
            name="actual"
            type="password"
            autoComplete="current-password"
            required
            error={errores.actual}
            autoFocus
          />
          <Campo
            etiqueta="Nueva contraseña"
            name="nueva"
            type="password"
            autoComplete="new-password"
            required
            error={errores.nueva}
            ayuda={`Al menos ${MINIMO} caracteres. Una frase de varias palabras es fácil de recordar y difícil de adivinar.`}
          />
          <Campo
            etiqueta="Confirmar nueva contraseña"
            name="confirmacion"
            type="password"
            autoComplete="new-password"
            required
            error={errores.confirmacion}
          />
          <Boton type="submit" className="w-full" cargando={cambiar.isPending}>
            Guardar contraseña
          </Boton>
          {!obligatorio && (
            <Link to="/" className="block text-center text-sm text-suave hover:text-texto">
              Cancelar
            </Link>
          )}
        </form>
      </div>
    </main>
  );
}
