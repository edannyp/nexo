/** Filtros de Explorar en la URL (compartibles): `?estado=PENDIENTE,RECHAZADO&con_foto=no&orden=venta`. */
import type { Completitud, Estado, ListarArticulosParams, Orden, Reserva } from '@nexo/api-client';

export interface FiltrosExplorar {
  q?: string;
  estado?: Estado[];
  completitud?: Completitud;
  con_foto?: boolean;
  emparejado?: boolean;
  con_hallazgo?: boolean;
  con_principal?: boolean;
  vehiculo?: string;
  clase?: string[];
  reserva?: Reserva;
  orden?: Orden;
}

const ESTADOS: Estado[] = ['PENDIENTE', 'POR_VALIDAR', 'RECHAZADO', 'VALIDADO', 'SINCRONIZADO'];
const CLASES = ['A', 'B', 'C', 'SIN_VENTA'];
const ORDENES: Orden[] = ['venta', 'codigo', 'descripcion', 'estado', 'anio', 'reciente', 'faltantes'];

const lista = (v: unknown, validos: readonly string[]) => {
  const items = (Array.isArray(v) ? v.map(String) : String(v ?? '').split(',')).filter((x) => validos.includes(x));
  return items.length ? items : undefined;
};
const siNo = (v: unknown) => (v === 'si' || v === true ? true : v === 'no' || v === false ? false : undefined);
const uno = <T extends string>(v: unknown, validos: readonly T[]) => (validos.includes(v as T) ? (v as T) : undefined);

export function validarExplorar(s: Record<string, unknown>): FiltrosExplorar {
  const f: FiltrosExplorar = {
    q: typeof s.q === 'string' && s.q.trim() ? s.q : undefined,
    estado: lista(s.estado, ESTADOS) as Estado[] | undefined,
    completitud: uno(s.completitud, ['completa', 'incompleta'] as Completitud[]),
    con_foto: siNo(s.con_foto),
    emparejado: siNo(s.emparejado),
    con_hallazgo: siNo(s.con_hallazgo),
    con_principal: siNo(s.con_principal),
    vehiculo: typeof s.vehiculo === 'string' && s.vehiculo.trim() ? s.vehiculo.trim() : undefined,
    clase: lista(s.clase, CLASES),
    reserva: uno(s.reserva, ['mia', 'libre', 'otros'] as Reserva[]),
    orden: uno(s.orden, ORDENES),
  };
  return Object.fromEntries(Object.entries(f).filter(([, v]) => v !== undefined)) as FiltrosExplorar;
}

/** Para la URL: listas separadas por coma y sí/no en vez de true/false. */
export function aBusqueda(f: FiltrosExplorar): Record<string, string | undefined> {
  const b = (v?: boolean) => (v === undefined ? undefined : v ? 'si' : 'no');
  return {
    q: f.q,
    estado: f.estado?.join(','),
    completitud: f.completitud,
    con_foto: b(f.con_foto),
    emparejado: b(f.emparejado),
    con_hallazgo: b(f.con_hallazgo),
    con_principal: b(f.con_principal),
    vehiculo: f.vehiculo,
    clase: f.clase?.join(','),
    reserva: f.reserva,
    orden: f.orden,
  };
}

/**
 * Validación de la ruta: normaliza y devuelve la forma de la URL (textos), así el router la escribe igual que la lee.
 * (Si devolviera booleanos o listas, se serializarían como `false` o `A,B` sin pasar por aquí y se perderían al leer.)
 */
export function busquedaExplorar(s: Record<string, unknown>): Record<string, string> {
  return Object.fromEntries(Object.entries(aBusqueda(validarExplorar(s))).filter(([, v]) => v !== undefined)) as Record<
    string,
    string
  >;
}

/** Parámetros de la API (sin nulos: el cliente los enviaría como "null"). */
export function aParametros(f: FiltrosExplorar): ListarArticulosParams {
  return Object.fromEntries(Object.entries(f).filter(([, v]) => v !== undefined)) as ListarArticulosParams;
}

export const cuantosFiltros = (f: FiltrosExplorar) =>
  Object.entries(f).filter(([k, v]) => k !== 'orden' && k !== 'q' && v !== undefined).length;
