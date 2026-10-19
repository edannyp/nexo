import { createContext, useContext } from 'react';

import type { Filtro } from './filtro';

export interface ContextoFiltro {
  filtro: Filtro;
  cambiar: (f: Filtro) => void;
}

export const FiltroContexto = createContext<ContextoFiltro | null>(null);

/** Filtro global vigente (categoría + línea). Todas las pantallas lo usan para sus consultas. */
export function useFiltro(): ContextoFiltro {
  const ctx = useContext(FiltroContexto);
  if (!ctx) throw new Error('useFiltro debe usarse dentro del armazón de la APP');
  return ctx;
}
