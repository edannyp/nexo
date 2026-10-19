/** [1986, 1987, 1988, 1990] → '1986–1988, 1990' (igual que la API). */
export function rangos(anios: number[]): string {
  const orden = [...new Set(anios)].sort((a, b) => a - b);
  const partes: string[] = [];
  let ini: number | undefined;
  let prev: number | undefined;
  for (const a of [...orden, Number.NaN]) {
    if (ini !== undefined && prev !== undefined && a === prev + 1) {
      prev = a;
      continue;
    }
    if (ini !== undefined && prev !== undefined) partes.push(ini === prev ? String(ini) : `${ini}–${prev}`);
    ini = prev = a;
  }
  return partes.join(', ');
}

/** Años del rango que no aparecen en la lista: los que le faltan a una configuración. */
export function faltantes(anios: number[], desde: number, hasta: number): number[] {
  const hay = new Set(anios);
  return Array.from({ length: hasta - desde + 1 }, (_, i) => desde + i).filter((a) => !hay.has(a));
}
