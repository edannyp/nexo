/** Formatos de números y fechas para la consola (es-GT). */

const entero = new Intl.NumberFormat('es-GT', { maximumFractionDigits: 0 });
const compacto = new Intl.NumberFormat('es-GT', { notation: 'compact', maximumFractionDigits: 1 });
const mesCorto = new Intl.DateTimeFormat('es-GT', { month: 'short', year: '2-digit', timeZone: 'UTC' });
const fechaHora = new Intl.DateTimeFormat('es-GT', { dateStyle: 'medium', timeStyle: 'short' });

export const numero = (n: number | string) => entero.format(Number(n));
export const numeroCompacto = (n: number) => (Math.abs(n) >= 1000 ? compacto.format(n) : entero.format(n));

/** 0.0613 → "6.1 %"; por debajo de 0.1 % → "<0.1 %". */
export function porcentaje(fraccion: number | string | null | undefined, decimales = 1): string {
  if (fraccion === null || fraccion === undefined) return '—';
  const p = Number(fraccion) * 100;
  if (p > 0 && p < 0.1) return '<0.1 %';
  return `${p.toFixed(decimales)} %`;
}

/** Fracción de un total, sin dividir entre cero. */
export const fraccion = (parte: number, total: number) => (total > 0 ? parte / total : 0);

/** "2026-09-01" → "sept 26" (las fechas de mes vienen sin hora: se leen en UTC). */
export const mes = (iso: string) => mesCorto.format(new Date(`${iso.slice(0, 10)}T00:00:00Z`));
export const momento = (iso: string) => fechaHora.format(new Date(iso));
