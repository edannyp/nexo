import { describe, expect, it } from 'vitest';

import { atajoSimple } from './teclado';

const evento = (el: HTMLElement, extra: Partial<KeyboardEventInit> = {}) => {
  document.body.append(el);
  const e = new KeyboardEvent('keydown', { key: 'j', ...extra });
  Object.defineProperty(e, 'target', { value: el });
  return e;
};

describe('atajos de una tecla', () => {
  it('funcionan con el foco en una casilla o un botón', () => {
    const casilla = Object.assign(document.createElement('input'), { type: 'checkbox' });
    expect(atajoSimple(evento(casilla))).toBe(true);
    expect(atajoSimple(evento(document.createElement('button')))).toBe(true);
  });

  it('no se disparan mientras se escribe ni con Ctrl', () => {
    expect(atajoSimple(evento(Object.assign(document.createElement('input'), { type: 'search' })))).toBe(false);
    expect(atajoSimple(evento(document.createElement('textarea')))).toBe(false);
    expect(atajoSimple(evento(document.createElement('div'), { ctrlKey: true }))).toBe(false);
  });
});
