import {
  getObtenerPreferenciasQueryKey,
  useGuardarPreferencias,
  useListarCategorias,
  useObtenerPreferencias,
  type UsuarioSesion,
} from '@nexo/api-client';
import { useQueryClient } from '@tanstack/react-query';
import { Outlet, useNavigate, useRouter, useSearch } from '@tanstack/react-router';
import { LoaderCircle } from 'lucide-react';
import { useEffect, useMemo } from 'react';

import { Aviso, Boton } from '@/shared/ui';

import { BotonTema } from './BotonTema';
import { Busqueda } from './Busqueda';
import { FiltroContexto } from './contexto-filtro';
import { UsuarioContexto } from './contexto-usuario';
import { FiltroGlobal } from './FiltroGlobal';
import { filtroGuardado, guardarFiltro, resolverFiltro, type Filtro } from './filtro';
import { MenuUsuario } from './MenuUsuario';
import { NavegacionInferior, NavegacionLateral } from './Navegacion';
import { SECCIONES } from './navegacion';
import { puedeVer, useSesion } from './sesion';

function Marca() {
  return (
    <span className="flex items-center gap-2 font-semibold tracking-tight">
      <img src="/favicon.svg" alt="" className="size-7" />
      <span className="hidden sm:inline">Nexo</span>
    </span>
  );
}

/** Puerta de la APP: sin sesión → Entrar; con contraseña temporal → Cambiar contraseña. */
export function Armazon() {
  const sesion = useSesion();
  const router = useRouter();
  const pendiente =
    sesion.estado === 'anonimo'
      ? 'entrar'
      : sesion.estado === 'autenticado' && sesion.usuario.debe_cambiar_password
        ? 'cambiar'
        : null;

  // Redirección en un efecto que corre una sola vez por cambio de estado. La ubicación se lee del router en ese momento:
  // durante la navegación el router ya informa la nueva, y usarla al dibujar generaba un bucle de redirecciones.
  useEffect(() => {
    if (pendiente === 'entrar') {
      void router.navigate({ to: '/entrar', search: { redirigir: router.state.location.href }, replace: true });
    } else if (pendiente === 'cambiar') {
      void router.navigate({ to: '/cambiar-contrasena', replace: true });
    }
  }, [pendiente, router]);

  if (sesion.estado === 'cargando' || pendiente) {
    return (
      <div className="grid min-h-dvh place-items-center" role="status">
        <LoaderCircle className="size-6 animate-spin text-suave" aria-label="Cargando" />
      </div>
    );
  }
  if (sesion.estado === 'error') {
    return (
      <div className="mx-auto max-w-md p-6">
        <Aviso tono="error" titulo="No se pudo conectar con el servidor">
          Revisa tu conexión a la red interna e intenta de nuevo.
        </Aviso>
        <Boton className="mt-4" variante="secundario" onClick={() => window.location.reload()}>
          Reintentar
        </Boton>
      </div>
    );
  }
  if (sesion.estado !== 'autenticado') return null; // (la redirección del efecto ya está en curso)
  return <ArmazonAutenticado usuario={sesion.usuario} />;
}

/** Barra superior fija (filtro global, búsqueda, tema, usuario) + navegación según rol + contenido. */
function ArmazonAutenticado({ usuario }: { usuario: UsuarioSesion }) {
  const busqueda = useSearch({ from: '__root__' });
  const navegar = useNavigate();
  const consultas = useQueryClient();
  const categorias = useListarCategorias({ query: { staleTime: 60_000 } });
  const preferencias = useObtenerPreferencias({ query: { staleTime: Infinity } });
  const guardarPreferencias = useGuardarPreferencias();

  // Prioridad: URL > preferencia guardada en el servidor > última elección en este navegador > Radiadores · Importados
  const filtro = resolverFiltro(busqueda, preferencias.data ?? filtroGuardado());
  const ctx = useMemo(
    () => ({
      filtro,
      cambiar: (f: Filtro) => {
        guardarFiltro(f);
        consultas.setQueryData(getObtenerPreferenciasQueryKey(), f);
        guardarPreferencias.mutate({ data: f });
        void navegar({ to: '.', search: (prev) => ({ ...prev, ...f }) });
      },
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [filtro.cat, filtro.linea, navegar],
  );
  const secciones = SECCIONES.filter((s) => puedeVer(usuario, s));

  return (
    <UsuarioContexto.Provider value={usuario}>
      <FiltroContexto.Provider value={ctx}>
        <div className="flex min-h-dvh flex-col">
          <a href="#contenido" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50">
            Saltar al contenido
          </a>
          <header className="sticky top-0 z-10 border-b border-borde bg-superficie/95 backdrop-blur">
            <div className="flex h-14 items-center gap-3 px-4">
              <Marca />
              <FiltroGlobal
                className="hidden md:flex"
                categorias={categorias.data}
                error={categorias.isError}
                filtro={ctx.filtro}
                onCambiar={ctx.cambiar}
              />
              <div className="ml-auto flex items-center gap-1">
                <Busqueda />
                <BotonTema />
                <MenuUsuario />
              </div>
            </div>
            {/* En celular el filtro ocupa su propia fila, a todo lo ancho */}
            <FiltroGlobal
              className="px-4 pb-3 md:hidden"
              categorias={categorias.data}
              error={categorias.isError}
              filtro={ctx.filtro}
              onCambiar={ctx.cambiar}
            />
          </header>
          <div className="flex flex-1">
            <NavegacionLateral secciones={secciones} />
            <main id="contenido" className="min-w-0 flex-1 p-4 pb-24 lg:p-6">
              <Outlet />
            </main>
          </div>
          <NavegacionInferior secciones={secciones} />
        </div>
      </FiltroContexto.Provider>
    </UsuarioContexto.Provider>
  );
}
