import { describe, expect, it } from 'vitest';

import { faltantes, rangos } from './anios';

describe('años', () => {
  it('junta años seguidos en rangos', () => {
    expect(rangos([1990, 1986, 1987, 1988, 1987])).toBe('1986–1988, 1990');
    expect(rangos([2013])).toBe('2013');
    expect(rangos([])).toBe('');
  });

  it('dice qué años faltan en el rango pedido', () => {
    expect(faltantes([1986, 1988], 1986, 1989)).toEqual([1987, 1989]);
    expect(faltantes([2010, 2011], 2010, 2011)).toEqual([]);
  });
});
