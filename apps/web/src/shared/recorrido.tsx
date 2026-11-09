import { ChevronLeft, ChevronRight, CircleHelp, X } from 'lucide-react';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useState,
  type ReactNode,
  type CSSProperties,
} from 'react';
import { createPortal } from 'react-dom';

import { Boton } from './ui';

/** Un paso del recorrido: `donde` es un selector CSS del elemento a resaltar; sin él (o si no está visible), la tarjeta va al centro. */
export interface Paso {
  donde?: string;
  titulo: string;
  texto: string;
}

export interface DefinicionRecorrido {
  titulo: string;
  pasos: Paso[];
}

const Contexto = createContext<{ clave: string | null; fijar: (c: string | null) => void } | null>(null);

/** Guarda qué recorrido corresponde a la pantalla visible (lo fija cada pantalla con `useRecorrido`). */
export function RecorridoProveedor({ children }: { children: ReactNode }) {
  const [clave, fijar] = useState<string | null>(null);
  const valor = useMemo(() => ({ clave, fijar }), [clave]);
  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
}

/** La pantalla avisa cuál es su recorrido mientras está visible. */
export function useRecorrido(clave: string) {
  const ctx = useContext(Contexto);
  const fijar = ctx?.fijar;
  useEffect(() => {
    fijar?.(clave);
    return () => fijar?.(null);
  }, [clave, fijar]);
}

/** El primer elemento visible que coincide con el selector. */
function buscar(selector?: string): HTMLElement | null {
  if (!selector) return null;
  for (const el of document.querySelectorAll<HTMLElement>(selector)) {
    if (el.getClientRects().length > 0) return el;
  }
  return null;
}

const MARGEN = 8;
const ANCHO_TARJETA = 340;

/** Superpone el resaltado y la tarjeta del paso actual. Flechas ← → para moverse, Esc para salir. */
function Superposicion({ def, alCerrar }: { def: DefinicionRecorrido; alCerrar: () => void }) {
  const [i, setI] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const paso = def.pasos[i];
  const ultimo = i === def.pasos.length - 1;

  const medir = useCallback(() => setRect(buscar(paso?.donde)?.getBoundingClientRect() ?? null), [paso]);
  useLayoutEffect(() => {
    const el = buscar(paso?.donde);
    el?.scrollIntoView({ block: 'center', behavior: 'smooth' });
    const r = requestAnimationFrame(medir);
    const t = setTimeout(medir, 350); // después del desplazamiento suave
    window.addEventListener('resize', medir);
    window.addEventListener('scroll', medir, true);
    return () => {
      cancelAnimationFrame(r);
      clearTimeout(t);
      window.removeEventListener('resize', medir);
      window.removeEventListener('scroll', medir, true);
    };
  }, [paso, medir]);

  const ir = useCallback(
    (d: number) => setI((x) => Math.min(Math.max(x + d, 0), def.pasos.length - 1)),
    [def.pasos.length],
  );
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if (e.key === 'Escape') alCerrar();
      else if (e.key === 'ArrowRight' || e.key === 'Enter') {
        e.preventDefault();
        if (ultimo) alCerrar();
        else ir(1);
      } else if (e.key === 'ArrowLeft') ir(-1);
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  }, [alCerrar, ir, ultimo]);

  if (!paso) return null;

  // La tarjeta va debajo del elemento si cabe; si no, encima; en pantallas chicas, abajo a lo ancho
  const ancho = Math.min(ANCHO_TARJETA, window.innerWidth - 2 * MARGEN);
  let estilo: CSSProperties = {
    width: ancho,
    left: (window.innerWidth - ancho) / 2,
    top: '50%',
    transform: 'translateY(-50%)',
  };
  if (rect) {
    const izquierda = Math.min(Math.max(rect.left, MARGEN), window.innerWidth - ancho - MARGEN);
    const abajo = rect.bottom + 12;
    estilo =
      abajo + 220 < window.innerHeight
        ? { width: ancho, left: izquierda, top: abajo }
        : rect.top - 12 > 220
          ? { width: ancho, left: izquierda, bottom: window.innerHeight - rect.top + 12 }
          : { width: ancho, left: (window.innerWidth - ancho) / 2, bottom: MARGEN };
  }

  return createPortal(
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={`Recorrido: ${def.titulo}`}>
      {/* Fondo: oscurece todo salvo el elemento del paso (un recuadro con sombra enorme alrededor) */}
      {rect ? (
        <div
          className="pointer-events-none absolute rounded-lg ring-2 ring-primario transition-all duration-200"
          style={{
            left: rect.left - 6,
            top: rect.top - 6,
            width: rect.width + 12,
            height: rect.height + 12,
            boxShadow: '0 0 0 9999px rgb(0 0 0 / 0.55)',
          }}
        />
      ) : (
        <div className="absolute inset-0 bg-black/55" />
      )}
      {/* Clic fuera: no hace nada (evita cerrar por accidente); se sale con × o Esc */}
      <div className="absolute inset-0" />
      <section
        className="absolute rounded-lg border border-borde bg-superficie p-4 text-texto shadow-xl"
        style={estilo}
        aria-live="polite"
      >
        <div className="mb-1 flex items-start justify-between gap-2">
          <p className="text-xs text-suave tabular-nums">
            {def.titulo} · paso {i + 1} de {def.pasos.length}
          </p>
          <button
            type="button"
            onClick={alCerrar}
            aria-label="Cerrar el recorrido"
            className="-mt-1 -mr-1 grid size-7 place-items-center rounded-md hover:bg-superficie-2"
          >
            <X className="size-4" aria-hidden />
          </button>
        </div>
        <h2 className="font-semibold">{paso.titulo}</h2>
        <p className="mt-1 text-sm whitespace-pre-line">{paso.texto}</p>
        <div className="mt-4 flex items-center justify-between gap-2">
          <div className="flex gap-1" aria-hidden>
            {def.pasos.map((_, k) => (
              <span
                key={k}
                className={k === i ? 'size-1.5 rounded-full bg-primario' : 'size-1.5 rounded-full bg-borde'}
              />
            ))}
          </div>
          <div className="flex gap-2">
            {i > 0 && (
              <Boton variante="fantasma" className="h-8 px-2 text-sm" onClick={() => ir(-1)}>
                <ChevronLeft className="size-4" aria-hidden /> Anterior
              </Boton>
            )}
            <Boton className="h-8 px-3 text-sm" onClick={() => (ultimo ? alCerrar() : ir(1))} autoFocus>
              {ultimo ? 'Terminar' : 'Siguiente'} {!ultimo && <ChevronRight className="size-4" aria-hidden />}
            </Boton>
          </div>
        </div>
      </section>
    </div>,
    document.body,
  );
}

/**
 * Botón «?» de la barra superior: abre el recorrido de la pantalla visible. `recorridos` trae el texto de todos (app/recorridos).
 * Solo se abre a pedido (no arranca solo).
 */
export function BotonAyuda({ recorridos }: { recorridos: Record<string, DefinicionRecorrido> }) {
  const ctx = useContext(Contexto);
  const [abierto, setAbierto] = useState(false);
  const def = ctx?.clave ? recorridos[ctx.clave] : undefined;
  if (!def) return null;
  return (
    <>
      <button
        type="button"
        onClick={() => setAbierto(true)}
        aria-label={`Ayuda: recorrido de ${def.titulo}`}
        title="Ayuda: recorrido de esta pantalla"
        className="grid size-9 place-items-center rounded-md text-suave hover:bg-superficie-2 hover:text-texto"
      >
        <CircleHelp className="size-5" aria-hidden />
      </button>
      {abierto && <Superposicion def={def} alCerrar={() => setAbierto(false)} />}
    </>
  );
}
