/** Atajos de una tecla (J, K, N…): no deben dispararse mientras se escribe, pero sí con el foco en una casilla o un botón. */
const TIPOS_DE_TEXTO = new Set(['text', 'search', 'email', 'password', 'number', 'tel', 'url', 'date']);

export function escribiendo(e: KeyboardEvent): boolean {
  const el = e.target as HTMLElement | null;
  if (!el) return false;
  if (el.isContentEditable || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') return true;
  return el.tagName === 'INPUT' && TIPOS_DE_TEXTO.has((el as HTMLInputElement).type);
}

/** Atajo simple: sin Ctrl/Cmd/Alt y fuera de campos de texto. */
export const atajoSimple = (e: KeyboardEvent) => !e.ctrlKey && !e.metaKey && !e.altKey && !escribiendo(e);
