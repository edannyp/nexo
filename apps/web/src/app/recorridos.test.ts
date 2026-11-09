import { describe, expect, it } from 'vitest';

import { RECORRIDOS } from './recorridos';

// Las claves que usan las pantallas (useRecorrido): si se agrega una pantalla o pestaña, su recorrido tiene que existir
const PANTALLAS = [
  'panorama',
  'trabajar',
  'validar',
  'explorar',
  'articulo-resumen',
  'articulo-ficha',
  'articulo-aplicaciones',
  'articulo-emparejamiento',
  'articulo-equivalencia',
  'verificacion',
  'fabricados',
  'catalogo',
  'fotos',
  'calidad-sap',
  'ventas',
  'usuarios',
];

describe('recorridos guiados', () => {
  it.each(PANTALLAS)('%s tiene título y pasos con texto', (clave) => {
    const r = RECORRIDOS[clave];
    expect(r?.titulo).toBeTruthy();
    expect(r?.pasos.length).toBeGreaterThan(1);
    for (const p of r?.pasos ?? []) expect(p.titulo && p.texto).toBeTruthy();
  });

  it('no sobra ninguno', () => {
    expect(Object.keys(RECORRIDOS).sort()).toEqual([...PANTALLAS].sort());
  });
});
