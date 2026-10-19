import { Link } from '@tanstack/react-router';
import { Lock, Menu, X } from 'lucide-react';
import { useRef } from 'react';

import { cn } from '@/shared/cn';

import { SECCIONES, type Seccion } from './navegacion';

const enlace =
  'flex items-center gap-3 rounded-md px-3 py-2 text-sm text-suave hover:bg-superficie-2 hover:text-texto ' +
  'data-[status=active]:bg-superficie-2 data-[status=active]:font-medium data-[status=active]:text-texto';

function Entrada({ s, alPulsar }: { s: Seccion; alPulsar?: () => void }) {
  return (
    <Link to={s.ruta} activeOptions={{ exact: s.ruta === '/' }} className={enlace} onClick={alPulsar}>
      <s.icono className="size-4 shrink-0" aria-hidden />
      <span className="truncate">{s.etiqueta}</span>
      {s.restringida && <Lock className="ml-auto size-3.5" aria-label="Requiere permiso" />}
    </Link>
  );
}

/** Escritorio (lg+): menú lateral fijo. */
export function NavegacionLateral() {
  return (
    <nav aria-label="Secciones" className="hidden w-56 shrink-0 border-r border-borde p-3 lg:block">
      <ul className="sticky top-17 space-y-0.5">
        {SECCIONES.map((s) => (
          <li key={s.ruta}>
            <Entrada s={s} />
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** Celular y tableta: menú inferior con las entradas principales y "Más" para el resto. */
export function NavegacionInferior() {
  const mas = useRef<HTMLDialogElement>(null);
  const cerrar = () => mas.current?.close();
  const principales = SECCIONES.filter((s) => s.movil);
  const resto = SECCIONES.filter((s) => !s.movil);

  return (
    <>
      <nav
        aria-label="Secciones"
        className="fixed inset-x-0 bottom-0 z-20 border-t border-borde bg-superficie pb-[env(safe-area-inset-bottom)] lg:hidden"
      >
        <ul className="grid grid-cols-5">
          {principales.map((s) => (
            <li key={s.ruta}>
              <Link
                to={s.ruta}
                activeOptions={{ exact: s.ruta === '/' }}
                className="flex flex-col items-center gap-0.5 py-2 text-[11px] text-suave data-[status=active]:text-primario"
              >
                <s.icono className="size-5" aria-hidden />
                {s.etiqueta}
              </Link>
            </li>
          ))}
          <li>
            <button
              type="button"
              onClick={() => mas.current?.showModal()}
              className="flex w-full flex-col items-center gap-0.5 py-2 text-[11px] text-suave"
            >
              <Menu className="size-5" aria-hidden />
              Más
            </button>
          </li>
        </ul>
      </nav>
      <dialog
        ref={mas}
        aria-label="Más secciones"
        className={cn(
          'mt-auto mb-0 w-full max-w-none rounded-t-xl border border-borde bg-superficie p-3 text-texto backdrop:bg-black/40',
          'pb-[calc(0.75rem+env(safe-area-inset-bottom))]',
        )}
        onClick={(e) => e.target === mas.current && cerrar()}
      >
        <div className="mb-2 flex items-center justify-between px-3">
          <span className="text-sm font-medium">Más secciones</span>
          <button type="button" onClick={cerrar} aria-label="Cerrar" className="grid size-9 place-items-center">
            <X className="size-5" aria-hidden />
          </button>
        </div>
        <ul className="space-y-0.5">
          {resto.map((s) => (
            <li key={s.ruta}>
              <Entrada s={s} alPulsar={cerrar} />
            </li>
          ))}
        </ul>
      </dialog>
    </>
  );
}
