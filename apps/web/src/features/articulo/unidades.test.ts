import { describe, expect, it } from 'vitest';

import { aMilimetros, aNumero } from './unidades';

describe('medidas a milímetros', () => {
  it('acepta la unidad escrita o la elegida', () => {
    expect(aMilimetros('37.5 cm')).toBe(375);
    expect(aMilimetros('37,5', 'cm')).toBe(375);
    expect(aMilimetros('375')).toBe(375);
    expect(aMilimetros('14.8"')).toBe(375.92);
    expect(aMilimetros('14.8 in')).toBe(375.92);
    expect(aMilimetros('400 mm', 'cm')).toBe(400); // el sufijo escrito gana
  });

  it('rechaza lo que no es una medida', () => {
    expect(aMilimetros('')).toBeNull();
    expect(aMilimetros('abc')).toBeNull();
    expect(aMilimetros('40x50')).toBeNull();
  });

  it('números sin unidad', () => {
    expect(aNumero('2')).toBe(2);
    expect(aNumero('2,5')).toBe(2.5);
    expect(aNumero('dos')).toBeNull();
  });
});
