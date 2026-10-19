import { describe, expect, it } from 'vitest';

import { mover } from './FotosDelArticulo';

describe('ordenar fotos', () => {
  it('mueve una posición sin salirse de la lista', () => {
    expect(mover([1, 2, 3], 0, 1)).toEqual([2, 1, 3]);
    expect(mover([1, 2, 3], 2, -1)).toEqual([1, 3, 2]);
    expect(mover([1, 2, 3], 0, -1)).toEqual([1, 2, 3]);
    expect(mover([1, 2, 3], 2, 1)).toEqual([1, 2, 3]);
  });
});
