import { useListarCategorias } from '@nexo/api-client';
import { Outlet, useNavigate, useSearch } from '@tanstack/react-router';
import { useMemo } from 'react';

import { BotonTema } from './BotonTema';
import { Busqueda } from './Busqueda';
import { FiltroContexto } from './contexto-filtro';
import { FiltroGlobal } from './FiltroGlobal';
import { filtroGuardado, guardarFiltro, resolverFiltro, type Filtro } from './filtro';
import { NavegacionInferior, NavegacionLateral } from './Navegacion';

function Marca() {
  return (
    <span className="flex items-center gap-2 font-semibold tracking-tight">
      <img src="/favicon.svg" alt="" className="size-7" />
      <span className="hidden sm:inline">Nexo</span>
    </span>
  );
}

/** Armazón de la APP: barra superior fija (filtro global, búsqueda, tema) + navegación + contenido. */
export function Armazon() {
  const busqueda = useSearch({ from: '__root__' });
  const navegar = useNavigate();
  const categorias = useListarCategorias({ query: { staleTime: 60_000 } });

  const filtro = resolverFiltro(busqueda, filtroGuardado());
  const ctx = useMemo(
    () => ({
      filtro,
      cambiar: (f: Filtro) => {
        guardarFiltro(f);
        void navegar({ to: '.', search: (prev) => ({ ...prev, ...f }) });
      },
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [filtro.cat, filtro.linea, navegar],
  );

  return (
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
          <NavegacionLateral />
          <main id="contenido" className="min-w-0 flex-1 p-4 pb-24 lg:p-6">
            <Outlet />
          </main>
        </div>
        <NavegacionInferior />
      </div>
    </FiltroContexto.Provider>
  );
}
