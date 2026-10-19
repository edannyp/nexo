/** Preferencias locales del navegador. Pueden no estar disponibles (modo privado, bloqueo): nunca deben romper la APP. */

export function leer(clave: string): string | null {
  try {
    return localStorage.getItem(clave);
  } catch {
    return null;
  }
}

export function guardar(clave: string, valor: string): void {
  try {
    localStorage.setItem(clave, valor);
  } catch {
    /* sin almacenamiento: la preferencia dura solo esta sesión */
  }
}
