import { describe, expect, it } from 'vitest';

import { textoHerencia } from './Equivalencia';

describe('mensaje de herencia', () => {
  it('omite lo que viene en cero', () => {
    expect(textoHerencia({ partes: 1, aplicaciones_sugeridas: 0 })).toBe(
      'Equivalencia confirmada. Heredado como sugerencias: 1 parte (revísalas en Aplicaciones y Emparejamiento).',
    );
    expect(textoHerencia({ partes: 0, aplicaciones_sugeridas: 0 })).toMatch(/no se heredó nada/);
    expect(textoHerencia(null)).toBe('Equivalencia confirmada.');
  });
});
