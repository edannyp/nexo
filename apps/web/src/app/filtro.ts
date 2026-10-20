/**
 * Filtro global (ADR 0010): toda la APP trabaja sobre un tipo de artículo = categoría + línea.
 * Prioridad: URL (compartible) > última elección del usuario > Radiadores · Importados.
 */
import type { Linea } from '@nexo/api-client';

import { guardar, leer } from '@/shared/almacen';

export interface Filtro {
  cat: string;
  linea: Linea;
}

export interface BusquedaFiltro {
  cat?: string;
  linea?: Linea;
}

export const FILTRO_DEFECTO: Filtro = { cat: '25', linea: 'IMPORTADO' };
export const LINEAS: { valor: Linea; nombre: string }[] = [
  { valor: 'IMPORTADO', nombre: 'Importados' },
  { valor: 'FABRICADO', nombre: 'Fabricados' },
];

const CLAVE = 'nexo.filtro';

const esLinea = (v: unknown): v is Linea => v === 'IMPORTADO' || v === 'FABRICADO';
const esCategoria = (v: unknown): v is string => typeof v === 'string' && /^\d{2}$/.test(v);

/** Valida los parámetros de la URL: lo que no es válido se descarta (no rompe la navegación). */
export function validarBusqueda(busqueda: Record<string, unknown>): BusquedaFiltro {
  const cat = typeof busqueda.cat === 'number' ? String(busqueda.cat).padStart(2, '0') : busqueda.cat;
  return {
    ...(esCategoria(cat) ? { cat } : {}),
    ...(esLinea(busqueda.linea) ? { linea: busqueda.linea } : {}),
  };
}

export function filtroGuardado(): BusquedaFiltro {
  try {
    return validarBusqueda(JSON.parse(leer(CLAVE) ?? '{}') as Record<string, unknown>);
  } catch {
    return {};
  }
}

export function guardarFiltro(f: Filtro): void {
  guardar(CLAVE, JSON.stringify(f));
}

export function resolverFiltro(url: BusquedaFiltro, guardado: BusquedaFiltro): Filtro {
  return {
    cat: url.cat ?? guardado.cat ?? FILTRO_DEFECTO.cat,
    linea: url.linea ?? guardado.linea ?? FILTRO_DEFECTO.linea,
  };
}
