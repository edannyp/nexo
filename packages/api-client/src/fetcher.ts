/** Cliente HTTP de la API: misma origen (`/api`), cookie de sesión, token CSRF y errores RFC 9457 como `ProblemaError`. */

export interface Problema {
  type: string;
  title: string;
  status: number;
  detail?: string;
  errors?: { campo: string; mensaje: string }[];
}

export class ProblemaError extends Error {
  constructor(public readonly problema: Problema) {
    super(problema.detail ?? problema.title);
    this.name = 'ProblemaError';
  }
}

/** Orval usa este tipo como error de todos los hooks: la API siempre responde problem+json y el cliente lanza ProblemaError. */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export type ErrorType<_E> = ProblemaError;

const METODOS_SEGUROS = new Set(['GET', 'HEAD', 'OPTIONS']);
let csrf: string | null = null;
let alVencerSesion: (() => void) | null = null;

/** Token CSRF de la sesión (lo devuelven `iniciarSesion`, `obtenerSesion` y `cambiarPassword`). */
export function establecerCsrf(token: string | null): void {
  csrf = token;
}

/** Qué hacer cuando la API responde 401 (sesión vencida o cerrada desde otro lado). */
export function alPerderSesion(accion: () => void): void {
  alVencerSesion = accion;
}

export async function nexoFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const metodo = (options.method ?? 'GET').toUpperCase();
  const headers = new Headers(options.headers);
  if (csrf && !METODOS_SEGUROS.has(metodo)) headers.set('X-CSRF-Token', csrf);

  const respuesta = await fetch(url, { credentials: 'same-origin', ...options, headers });
  const tipo = respuesta.headers.get('content-type') ?? '';
  if (!respuesta.ok) {
    const problema: Problema = tipo.includes('json')
      ? ((await respuesta.json()) as Problema)
      : { type: 'about:blank', title: respuesta.statusText || 'Error de red', status: respuesta.status };
    if (respuesta.status === 401 && !url.endsWith('/api/v1/sesion')) alVencerSesion?.();
    throw new ProblemaError(problema);
  }
  if (respuesta.status === 204 || !tipo.includes('json')) return undefined as T;
  return (await respuesta.json()) as T;
}
