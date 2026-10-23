import type { Aplicaciones, ConfiguracionAgrupada } from '@nexo/api-client';
import { describe, expect, it } from 'vitest';

import { itemsParaAgregar } from './Aplicaciones';

const config = (sub: number, motor: number, bvs: number[]): ConfiguracionAgrupada => ({
  sub_model_id: sub,
  submodelo: 'DLX',
  motor: `motor ${motor}`,
  anios: bvs.map((b, i) => ({
    anio: 1986 + i,
    base_vehicle_id: b,
    engine_config_id: motor,
    regiones: ['USA'],
    catalogo: 'AUTOCARE',
  })),
  completa: true,
  catalogo: 'AUTOCARE',
});

const item = (bv: number, confirmado: boolean) => ({
  id: bv,
  anio: null,
  base_vehicle_id: bv,
  sub_model_id: 20,
  engine_config_id: 4704,
  equipment_base_id: null,
  origen: 'HEREDADO_EQUIVALENTE',
  confirmado,
  completa: true,
});

const actuales = {
  grupos: [
    {
      titulo: '',
      principal: false,
      detalle: '',
      anios: '',
      confirmados: 1,
      sugeridos: 1,
      items: [item(1, true), item(2, false)],
    },
  ],
} as Aplicaciones;

describe('aplicaciones por agregar', () => {
  it('cada año de lo marcado, sin lo ya confirmado (lo sugerido sí va: así se confirma)', () => {
    const lista = [config(20, 4704, [1, 2, 3]), config(21, 4705, [1])];
    expect(itemsParaAgregar(lista, new Set(['20-motor 4704']), actuales).map((i) => i.base_vehicle_id)).toEqual([2, 3]);
    expect(itemsParaAgregar(lista, new Set(), actuales)).toEqual([]);
  });
});
