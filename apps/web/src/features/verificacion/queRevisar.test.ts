import { describe, expect, it } from 'vitest';

import { queRevisar } from './Verificacion';

describe('qué revisar', () => {
  it('explica el cambio en el catálogo', () => {
    expect(
      queRevisar({
        origen: 'CAMBIO_CATALOGO',
        detalle: { parte_id: 5003, estado: 'FUSIONADA', fusionada_en_id: 9001 },
      }),
    ).toBe('La parte 5003 se fusionó en la 9001: confirma que el emparejamiento sigue siendo correcto.');
    expect(queRevisar({ origen: 'CAMBIO_CATALOGO', detalle: { parte_id: 5005, estado: 'NO_EXISTE' } })).toBe(
      'La parte 5005 ya no existe en el catálogo maestro.',
    );
  });

  it('muestra la nota de la manual', () => {
    expect(queRevisar({ origen: 'MANUAL', detalle: { nota: 'Revisar años', creada_por: 'sup1' } })).toBe(
      'Revisar años (sup1)',
    );
  });
});
