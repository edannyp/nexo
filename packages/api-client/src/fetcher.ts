/** Cliente HTTP de la API: misma origen (`/api`), cookies de sesión y errores RFC 9457 como `ProblemaError`. */

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

export async function nexoFetch<T>(url: string, options: RequestInit = {}): Promise<T> {
  const respuesta = await fetch(url, { credentials: 'same-origin', ...options });
  const tipo = respuesta.headers.get('content-type') ?? '';
  if (!respuesta.ok) {
    if (tipo.includes('json')) throw new ProblemaError((await respuesta.json()) as Problema);
    throw new ProblemaError({ type: 'about:blank', title: respuesta.statusText || 'Error de red', status: respuesta.status });
  }
  if (respuesta.status === 204 || !tipo.includes('json')) return undefined as T;
  return (await respuesta.json()) as T;
}
