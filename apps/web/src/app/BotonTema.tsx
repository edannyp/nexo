import { Monitor, Moon, Sun } from 'lucide-react';

import { useTema, type Tema } from '@/shared/tema';

const SIGUIENTE: Record<Tema, Tema> = { sistema: 'claro', claro: 'oscuro', oscuro: 'sistema' };
const ICONO = { sistema: Monitor, claro: Sun, oscuro: Moon };
const NOMBRE = { sistema: 'del sistema', claro: 'claro', oscuro: 'oscuro' };

/** Alterna sistema → claro → oscuro. */
export function BotonTema() {
  const [tema, cambiar] = useTema();
  const Icono = ICONO[tema];
  return (
    <button
      type="button"
      onClick={() => cambiar(SIGUIENTE[tema])}
      className="grid size-9 place-items-center rounded-md text-suave hover:bg-superficie-2 hover:text-texto"
      aria-label={`Tema ${NOMBRE[tema]}. Cambiar a ${NOMBRE[SIGUIENTE[tema]]}`}
      title={`Tema ${NOMBRE[tema]}`}
    >
      <Icono className="size-5" aria-hidden />
    </button>
  );
}
