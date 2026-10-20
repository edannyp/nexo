import { describe, expect, it } from 'vitest';

import { FILTRO_DEFECTO, resolverFiltro, validarBusqueda } from './filtro';

describe('filtro global', () => {
  it('por defecto es Radiadores · Importados', () => {
    expect(resolverFiltro({}, {})).toEqual({ cat: '25', linea: 'IMPORTADO' });
    expect(FILTRO_DEFECTO).toEqual({ cat: '25', linea: 'IMPORTADO' });
  });

  it('la URL gana sobre la última elección guardada', () => {
    expect(resolverFiltro({ cat: '18' }, { cat: '07', linea: 'FABRICADO' })).toEqual({ cat: '18', linea: 'FABRICADO' });
  });

  it('descarta parámetros inválidos sin romper la navegación', () => {
    expect(validarBusqueda({ cat: 'xx', linea: 'USADO' })).toEqual({});
    expect(validarBusqueda({ cat: 7, linea: 'FABRICADO' })).toEqual({ cat: '07', linea: 'FABRICADO' });
  });
});
