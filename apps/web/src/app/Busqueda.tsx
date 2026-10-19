import { Search } from 'lucide-react';
import { useEffect, useRef } from 'react';

/** Búsqueda universal (Ctrl+K). En el esqueleto solo abre el cuadro; los resultados llegan en el paso 5. */
export function Busqueda() {
  const dialogo = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const atajo = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        dialogo.current?.showModal();
      }
    };
    window.addEventListener('keydown', atajo);
    return () => window.removeEventListener('keydown', atajo);
  }, []);

  return (
    <>
      <button
        type="button"
        onClick={() => dialogo.current?.showModal()}
        className="flex h-9 items-center gap-2 rounded-md border border-borde bg-superficie px-2 text-sm text-suave hover:text-texto md:w-64"
        aria-label="Buscar (Ctrl+K)"
      >
        <Search className="size-4" aria-hidden />
        <span className="hidden md:inline">Buscar…</span>
        <kbd className="ml-auto hidden rounded border border-borde px-1.5 text-xs md:inline">Ctrl K</kbd>
      </button>
      <dialog
        ref={dialogo}
        aria-label="Búsqueda universal"
        className="m-auto w-[min(36rem,calc(100vw-2rem))] rounded-lg border border-borde bg-superficie p-0 text-texto backdrop:bg-black/40"
        onClick={(e) => e.target === dialogo.current && dialogo.current?.close()}
      >
        <div className="flex items-center gap-2 border-b border-borde p-3">
          <Search className="size-5 text-suave" aria-hidden />
          <input
            autoFocus
            className="w-full bg-transparent outline-none placeholder:text-suave"
            placeholder="Código, OEM, vehículo, medidas (400x518x26)…"
          />
        </div>
        <p className="p-4 text-sm text-suave">
          La búsqueda universal llega en el paso 5 (bandejas). Aquí buscarás por código de artículo, número de parte,
          vehículo, medidas o descripción.
        </p>
      </dialog>
    </>
  );
}
