/** Medidas: el operador escribe en la unidad que tenga a mano; Nexo guarda en la unidad del atributo (MM). */

export const UNIDADES = [
  { codigo: 'mm', nombre: 'mm', factor: 1 },
  { codigo: 'cm', nombre: 'cm', factor: 10 },
  { codigo: 'in', nombre: 'pulg', factor: 25.4 },
] as const;
export type Unidad = (typeof UNIDADES)[number]['codigo'];

const SUFIJO: Record<string, Unidad> = { mm: 'mm', cm: 'cm', in: 'in', pulg: 'in', '"': 'in', "''": 'in' };

/**
 * "37.5 cm" → 375 · "375" (con unidad mm) → 375 · '14.8"' → 375.92 · "37,5" (con unidad cm) → 375.
 * Un sufijo escrito gana sobre la unidad elegida. Devuelve null si no es un número válido.
 */
export function aMilimetros(texto: string, unidad: Unidad = 'mm'): number | null {
  const m = texto
    .trim()
    .toLowerCase()
    .match(/^(\d+(?:[.,]\d+)?)\s*(mm|cm|in|pulg|"|'')?$/);
  if (!m?.[1]) return null;
  const valor = Number(m[1].replace(',', '.'));
  const u = m[2] ? SUFIJO[m[2]] : unidad;
  const factor = UNIDADES.find((x) => x.codigo === u)?.factor ?? 1;
  return Math.round(valor * factor * 100) / 100;
}

/** Número entero o decimal sin unidad (p. ej. filas): "2" → 2, "2,5" → 2.5. */
export function aNumero(texto: string): number | null {
  const m = texto.trim().match(/^\d+(?:[.,]\d+)?$/);
  return m ? Number(m[0].replace(',', '.')) : null;
}
