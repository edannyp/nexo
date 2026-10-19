import type { Categoria, Linea } from '@nexo/api-client';

import { cn } from '@/shared/cn';

import { LINEAS, type Filtro } from './filtro';

const numero = new Intl.NumberFormat('es-GT');

/** "DEPOSITOS AUXILIARES" → "Depositos auxiliares" */
export const nombreCategoria = (n: string) => n.charAt(0) + n.slice(1).toLowerCase();

interface Props {
  categorias: Categoria[] | undefined;
  filtro: Filtro;
  onCambiar: (f: Filtro) => void;
  error?: boolean;
  className?: string;
}

const estiloSelect =
  'h-9 min-w-0 rounded-md border border-borde bg-superficie px-2 text-sm text-texto disabled:opacity-60 cursor-pointer';

/**
 * Selectores nativos: accesibles y cómodos en celular (abren el selector del sistema).
 * Cada línea muestra cuántos artículos activos tiene en la categoría elegida.
 */
export function FiltroGlobal({ categorias, filtro, onCambiar, error, className }: Props) {
  const actual = categorias?.find((c) => c.codigo === filtro.cat);
  const cargando = !categorias && !error;

  return (
    <div role="group" aria-label="Tipo de artículo" className={cn('flex items-center gap-2', className)}>
      <select
        aria-label="Categoría"
        className={cn(estiloSelect, 'flex-1 sm:flex-none sm:w-52')}
        value={filtro.cat}
        disabled={!categorias}
        onChange={(e) => onCambiar({ ...filtro, cat: e.target.value })}
      >
        {categorias ? (
          categorias.map((c) => (
            <option key={c.codigo} value={c.codigo}>
              {nombreCategoria(c.nombre)}
            </option>
          ))
        ) : (
          <option value={filtro.cat}>{cargando ? 'Cargando…' : 'Sin conexión'}</option>
        )}
      </select>
      <select
        aria-label="Línea"
        className={cn(estiloSelect, 'flex-1 sm:flex-none sm:w-44')}
        value={filtro.linea}
        disabled={!categorias}
        onChange={(e) => onCambiar({ ...filtro, linea: e.target.value as Linea })}
      >
        {LINEAS.map((l) => {
          const n = actual?.activos[l.valor];
          return (
            <option key={l.valor} value={l.valor}>
              {n === undefined ? l.nombre : `${l.nombre} (${numero.format(n)})`}
            </option>
          );
        })}
      </select>
    </div>
  );
}
