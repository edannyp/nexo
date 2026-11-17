import type { Panorama } from '@nexo/api-client';
import { ChevronDown, Maximize2, Workflow } from 'lucide-react';
import { useState } from 'react';

import { Boton, Dialogo } from '@/shared/ui';

import { DibujoProceso, PROCESOS, type Proceso } from './procesos';

const CLAVE_ABIERTO = 'nexo.panorama.diagrama-abierto';
const CLAVE_PROCESO = 'nexo.panorama.proceso';

/** Lee una preferencia de este navegador; si el almacenamiento falla, usa el valor por defecto. */
function leer(clave: string): string | null {
  try {
    return localStorage.getItem(clave);
  } catch {
    return null;
  }
}
function guardar(clave: string, valor: string) {
  try {
    localStorage.setItem(clave, valor);
  } catch {
    /* sin almacenamiento: solo dura esta visita */
  }
}

/** Pestañas para elegir el proceso (en la tarjeta y en la vista en grande). */
function Pestanas({ proceso, alElegir }: { proceso: Proceso; alElegir: (p: Proceso) => void }) {
  return (
    <div role="tablist" aria-label="Proceso" className="flex flex-wrap gap-1">
      {PROCESOS.map((p) => (
        <button
          key={p.id}
          role="tab"
          type="button"
          aria-selected={proceso === p.id}
          onClick={() => alElegir(p.id)}
          className="rounded-md px-3 py-1 text-sm text-suave hover:bg-superficie-2 aria-selected:bg-superficie-2 aria-selected:font-medium aria-selected:text-texto"
        >
          {p.nombre}
        </button>
      ))}
    </div>
  );
}

/**
 * Tarjeta «Procesos» de Panorama: el del artículo y el de la ficha de atributos, en BPMN con cifras del tipo
 * elegido. Plegable (cerrada al entrar, recuerda la última elección y el último proceso visto); «Ver en grande» abre un diálogo.
 */
export function DiagramaProceso({ d }: { d: Panorama }) {
  const [abierto, setAbierto] = useState(() => leer(CLAVE_ABIERTO) === '1');
  const [proceso, setProceso] = useState<Proceso>(() => {
    const p = leer(CLAVE_PROCESO);
    return PROCESOS.some((x) => x.id === p) ? (p as Proceso) : 'articulo';
  });
  const [grande, setGrande] = useState(false);
  const alternar = () =>
    setAbierto((a) => {
      guardar(CLAVE_ABIERTO, a ? '0' : '1');
      return !a;
    });
  const elegir = (p: Proceso) => {
    guardar(CLAVE_PROCESO, p);
    setProceso(p);
  };
  const actual = PROCESOS.find((p) => p.id === proceso) ?? PROCESOS[0]!;

  return (
    <section data-recorrido="panorama-proceso" className="rounded-lg border border-borde bg-superficie">
      <div className="flex items-center gap-3 px-4 py-3">
        <button
          type="button"
          onClick={alternar}
          aria-expanded={abierto}
          aria-controls="panorama-diagrama"
          className="-m-1 flex min-w-0 flex-1 items-center gap-3 rounded-md p-1 text-left hover:bg-superficie-2"
        >
          <span className="grid size-9 shrink-0 place-items-center rounded-md bg-primario/10 text-primario">
            <Workflow className="size-5" aria-hidden />
          </span>
          <span className="min-w-0">
            <span className="block text-sm font-medium">Procesos</span>
            <span className="block text-xs text-suave">
              Artículo y ficha de atributos.{' '}
              {abierto ? 'Las cifras son las de hoy en el tipo elegido.' : 'Despliega para ver los diagramas.'}
            </span>
          </span>
          <ChevronDown
            className={`ml-auto size-4 shrink-0 text-suave transition-transform ${abierto ? 'rotate-180' : ''}`}
            aria-hidden
          />
          <span className="sr-only">{abierto ? 'Ocultar diagramas' : 'Mostrar diagramas'}</span>
        </button>
        <Boton
          variante="fantasma"
          className="h-8 shrink-0 px-2 text-xs"
          onClick={() => setGrande(true)}
          title="Ver el diagrama en grande"
        >
          <Maximize2 className="size-4" aria-hidden /> <span className="hidden sm:inline">Ver en grande</span>
        </Boton>
      </div>
      {abierto && (
        <div id="panorama-diagrama" className="space-y-2 border-t border-borde p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Pestanas proceso={proceso} alElegir={elegir} />
            <p className="text-xs text-suave">{actual.resumen}</p>
          </div>
          <div className="overflow-x-auto">
            <DibujoProceso proceso={proceso} d={d} />
          </div>
        </div>
      )}
      <Dialogo abierto={grande} alCerrar={() => setGrande(false)} titulo={`Proceso: ${actual.nombre} (BPMN)`} amplio>
        <div className="space-y-3">
          <Pestanas proceso={proceso} alElegir={elegir} />
          <div className="overflow-x-auto">
            <DibujoProceso proceso={proceso} d={d} />
          </div>
          <p className="text-xs text-suave">
            ○ inicio · ◉ fin · rectángulo: tarea · rombo: decisión · línea punteada: vuelta o camino alterno.{' '}
            {actual.nota}
          </p>
        </div>
      </Dialogo>
    </section>
  );
}
