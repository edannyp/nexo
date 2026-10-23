import { describe, expect, it } from 'vitest';

import { aBusqueda, aParametros, busquedaExplorar, cuantosFiltros, validarExplorar } from './filtros';

describe('filtros de Explorar en la URL', () => {
  it('ida y vuelta: lo que se escribe en la URL se lee igual', () => {
    const f = validarExplorar({
      estado: 'PENDIENTE,RECHAZADO',
      con_foto: 'no',
      clase: 'A,SIN_VENTA',
      orden: 'faltantes',
      q: 'toyota',
    });
    expect(f).toEqual({
      q: 'toyota',
      estado: ['PENDIENTE', 'RECHAZADO'],
      con_foto: false,
      clase: ['A', 'SIN_VENTA'],
      orden: 'faltantes',
    });
    expect(validarExplorar(aBusqueda(f))).toEqual(f);
  });

  it('descarta valores inválidos y no envía nulos a la API', () => {
    expect(validarExplorar({ estado: 'BORRADO', con_foto: 'quizas', orden: 'precio' })).toEqual({});
    expect(aParametros({ con_foto: false })).toEqual({ con_foto: false });
  });

  it('cuenta los filtros activos sin contar la búsqueda ni el orden', () => {
    expect(cuantosFiltros({ q: 'x', orden: 'codigo', estado: ['PENDIENTE'], con_foto: true })).toBe(2);
  });

  it('la validación de la ruta devuelve la forma de la URL y acepta valores ya tipados', () => {
    expect(busquedaExplorar({ con_foto: false, clase: ['A', 'B'], estado: 'PENDIENTE' })).toEqual({
      con_foto: 'no',
      clase: 'A,B',
      estado: 'PENDIENTE',
    });
    expect(busquedaExplorar(busquedaExplorar({ con_foto: 'no' }))).toEqual({ con_foto: 'no' });
  });
});

describe('vehículo principal', () => {
  it('viaja en la URL y vuelve igual', () => {
    const f = validarExplorar({ con_principal: 'no', vehiculo: ' hilux ' });
    expect(f).toEqual({ con_principal: false, vehiculo: 'hilux' });
    expect(validarExplorar(aBusqueda(f))).toEqual(f);
  });
});
