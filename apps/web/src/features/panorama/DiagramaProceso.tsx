import type { Estado } from '@nexo/api-client';
import { ChevronDown, Maximize2, Workflow } from 'lucide-react';
import { useState } from 'react';

import { numero } from '@/shared/formato';
import { Boton, Dialogo } from '@/shared/ui';

/*
 * Proceso del artículo en notación BPMN (context/workflow-estados.md, ADR 0012 y 0025): carriles por participante, eventos de inicio
 * y fin, tareas, decisiones y las vueltas a Pendiente en punteado. Cada etapa muestra cuántos artículos están hoy en ese estado.
 * SVG propio: colores del tema (claro y oscuro) y sin librería.
 */

const ANCHO = 1180;
const CARRIL = 130;
const ROTULO = 44; // columna con el nombre del carril
const CARRILES = ['SAP · ETL', 'Operador', 'Supervisor', 'Salida a SAP'];
const y = (carril: number) => carril * CARRIL + CARRIL / 2;

const COLOR: Record<Estado, string> = {
  PENDIENTE: 'var(--color-pendiente)',
  POR_VALIDAR: 'var(--color-por-validar)',
  RECHAZADO: 'var(--color-rechazado)',
  VALIDADO: 'var(--color-validado)',
  SINCRONIZADO: 'var(--color-sincronizado)',
};
const NOMBRE: Record<Estado, string> = {
  PENDIENTE: 'Pendiente',
  POR_VALIDAR: 'Por validar',
  RECHAZADO: 'Rechazado',
  VALIDADO: 'Validado',
  SINCRONIZADO: 'Sincronizado',
};

/** Tarea BPMN: rectángulo redondeado con texto en una o dos líneas y, si corresponde, el estado y su cantidad. */
function Tarea({
  x,
  cy,
  lineas,
  estado,
  cantidad,
  ancho = 150,
}: {
  x: number;
  cy: number;
  lineas: string[];
  estado?: Estado;
  cantidad?: number;
  ancho?: number;
}) {
  const alto = 58;
  return (
    <g>
      <rect
        x={x - ancho / 2}
        y={cy - alto / 2}
        width={ancho}
        height={alto}
        rx={10}
        className="fill-superficie stroke-texto/60"
        strokeWidth={1.5}
      />
      {lineas.map((l, k) => (
        <text
          key={l}
          x={x}
          y={cy + (k - (lineas.length - 1) / 2) * 15 + 4}
          textAnchor="middle"
          className="fill-texto text-[12px]"
        >
          {l}
        </text>
      ))}
      {estado && (
        <g transform={`translate(${x - ancho / 2 + 6}, ${cy + alto / 2 + 4})`}>
          <rect width={ancho - 12} height={18} rx={9} fill={COLOR[estado]} opacity={0.15} />
          <text
            x={(ancho - 12) / 2}
            y={13}
            textAnchor="middle"
            className="text-[11px] font-semibold"
            fill={COLOR[estado]}
          >
            {NOMBRE[estado]}
            {cantidad !== undefined ? ` · ${numero(cantidad)}` : ''}
          </text>
        </g>
      )}
    </g>
  );
}

/** Compuerta exclusiva (rombo con X) con su pregunta encima. */
function Decision({ x, cy, pregunta }: { x: number; cy: number; pregunta: string }) {
  const r = 22;
  return (
    <g>
      <polygon
        points={`${x},${cy - r} ${x + r},${cy} ${x},${cy + r} ${x - r},${cy}`}
        className="fill-superficie stroke-texto/60"
        strokeWidth={1.5}
      />
      <path
        d={`M${x - 7} ${cy - 7} L${x + 7} ${cy + 7} M${x + 7} ${cy - 7} L${x - 7} ${cy + 7}`}
        className="stroke-texto/60"
        strokeWidth={2}
      />
      <text x={x} y={cy - r - 8} textAnchor="middle" className="fill-suave text-[11px]">
        {pregunta}
      </text>
    </g>
  );
}

/** Evento de inicio (círculo fino) o de fin (círculo grueso), con su texto debajo. */
function Evento({ x, cy, fin, lineas }: { x: number; cy: number; fin?: boolean; lineas: string[] }) {
  return (
    <g>
      <circle cx={x} cy={cy} r={16} className="fill-superficie stroke-texto/70" strokeWidth={fin ? 4 : 1.5} />
      {lineas.map((l, k) => (
        <text key={l} x={x} y={cy + 32 + k * 13} textAnchor="middle" className="fill-suave text-[11px]">
          {l}
        </text>
      ))}
    </g>
  );
}

/** Flujo de secuencia; `etiqueta` va junto al primer tramo. Punteado = vuelve a Pendiente. */
function Flujo({
  puntos,
  etiqueta,
  dx = 6,
  dy = -6,
  punteado,
}: {
  puntos: [number, number][];
  etiqueta?: string;
  dx?: number;
  dy?: number;
  punteado?: boolean;
}) {
  const d = puntos.map(([px, py], k) => `${k ? 'L' : 'M'}${px} ${py}`).join(' ');
  const [x0, y0] = puntos[0] ?? [0, 0];
  return (
    <g>
      <path
        d={d}
        fill="none"
        className={punteado ? 'stroke-por-validar' : 'stroke-texto/60'}
        strokeWidth={1.5}
        strokeDasharray={punteado ? '6 4' : undefined}
        markerEnd={punteado ? 'url(#flecha-punteada)' : 'url(#flecha)'}
      />
      {etiqueta && (
        <text x={x0 + dx} y={y0 + dy} className={punteado ? 'fill-por-validar text-[11px]' : 'fill-suave text-[11px]'}>
          {etiqueta}
        </text>
      )}
    </g>
  );
}

function Diagrama({ porEstado }: { porEstado: Partial<Record<Estado, number>> }) {
  const n = (e: Estado) => porEstado[e] ?? 0;
  return (
    <svg
      viewBox={`0 0 ${ANCHO} ${CARRILES.length * CARRIL}`}
      className="h-auto w-full min-w-[56rem]"
      role="img"
      aria-label="Proceso del artículo en BPMN: SAP, operador, supervisor y salida a SAP"
    >
      <defs>
        <marker
          id="flecha"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path d="M0 0 L10 5 L0 10 z" className="fill-texto/60" />
        </marker>
        <marker
          id="flecha-punteada"
          viewBox="0 0 10 10"
          refX="9"
          refY="5"
          markerWidth="7"
          markerHeight="7"
          orient="auto-start-reverse"
        >
          <path d="M0 0 L10 5 L0 10 z" className="fill-por-validar" />
        </marker>
      </defs>

      {/* Carriles */}
      {CARRILES.map((c, k) => (
        <g key={c}>
          <rect
            x={0.5}
            y={k * CARRIL + 0.5}
            width={ANCHO - 1}
            height={CARRIL}
            className={k % 2 ? 'fill-superficie-2/50 stroke-borde' : 'fill-superficie stroke-borde'}
          />
          <rect
            x={0.5}
            y={k * CARRIL + 0.5}
            width={ROTULO}
            height={CARRIL}
            className="fill-superficie-2 stroke-borde"
          />
          <text
            transform={`translate(${ROTULO / 2 + 5}, ${y(k)}) rotate(-90)`}
            textAnchor="middle"
            className="fill-texto text-[12px] font-semibold"
          >
            {c}
          </text>
        </g>
      ))}

      {/* SAP · ETL */}
      <Evento x={95} cy={y(0)} lineas={['Artículo nuevo o', 'cambia en SAP']} />
      <Flujo
        puntos={[
          [111, y(0)],
          [180, y(0)],
        ]}
      />
      <Tarea x={260} cy={y(0)} lineas={['ETL diario:', 'foto completa de SAP']} />
      <Flujo
        puntos={[
          [335, y(0)],
          [393, y(0)],
        ]}
      />
      <Decision x={415} cy={y(0)} pregunta="¿Nuevo o cambió?" />
      <Flujo
        puntos={[
          [437, y(0)],
          [520, y(0)],
        ]}
        etiqueta="sin cambios"
        dx={8}
      />
      <text x={528} y={y(0) + 4} className="fill-suave text-[11px]">
        nada que hacer
      </text>

      {/* Operador */}
      <Flujo
        puntos={[
          [415, y(0) + 22],
          [415, y(1) - 29],
        ]}
        etiqueta="sí"
        dx={-18}
        dy={14}
      />
      <text x={425} y={y(0) + 40} className="fill-por-validar text-[11px]">
        nuevo, o cambió algo que importa:
      </text>
      <text x={425} y={y(0) + 53} className="fill-por-validar text-[11px]">
        va a Pendiente (lo hecho se conserva)
      </text>
      <Tarea
        x={415}
        cy={y(1)}
        lineas={['Tomar con «Siguiente»', '(se reserva 30 min)']}
        estado="PENDIENTE"
        cantidad={n('PENDIENTE')}
        ancho={168}
      />
      <Flujo
        puntos={[
          [499, y(1)],
          [548, y(1)],
        ]}
      />
      <Tarea x={640} cy={y(1)} lineas={['Ficha, ★ vehículo principal', 'y emparejamiento']} ancho={184} />
      <Flujo
        puntos={[
          [732, y(1)],
          [783, y(1)],
        ]}
      />
      <Tarea x={850} cy={y(1)} lineas={['Enviar a revisión']} ancho={134} />

      {/* Supervisor */}
      <Flujo
        puntos={[
          [850, y(1) + 29],
          [850, y(2) - 29],
        ]}
      />
      <Tarea
        x={850}
        cy={y(2)}
        lineas={['Revisar', '(otro supervisor)']}
        estado="POR_VALIDAR"
        cantidad={n('POR_VALIDAR')}
        ancho={134}
      />
      <Flujo
        puntos={[
          [917, y(2)],
          [968, y(2)],
        ]}
      />
      <Decision x={990} cy={y(2)} pregunta="¿Correcto?" />
      <Flujo
        puntos={[
          [990, y(2) - 22],
          [990, y(1) + 4],
          [917, y(1) + 4],
        ]}
      />
      <text x={998} y={y(1) + 34} className="fill-suave text-[11px]">
        no: rechazar con motivo;
      </text>
      <text x={998} y={y(1) + 47} className="fill-suave text-[11px]">
        el operador corrige y reenvía
      </text>
      <text x={998} y={y(1) - 4} className="fill-rechazado text-[11px] font-semibold">
        Rechazado · {numero(n('RECHAZADO'))}
      </text>
      <Flujo
        puntos={[
          [1012, y(2)],
          [1062, y(2)],
        ]}
        etiqueta="sí"
        dx={8}
      />
      <Tarea x={1110} cy={y(2)} lineas={['Validar']} estado="VALIDADO" cantidad={n('VALIDADO')} ancho={128} />

      {/* Salida a SAP */}
      <Flujo
        puntos={[
          [1110, y(2) + 29],
          [1110, y(3) - 29],
        ]}
      />
      <Tarea x={1110} cy={y(3)} lineas={['Actualizar SAP', '(proceso externo)']} ancho={128} />
      <Flujo
        puntos={[
          [1046, y(3)],
          [960, y(3)],
        ]}
      />
      <Evento x={942} cy={y(3)} fin lineas={['Sincronizado', numero(n('SINCRONIZADO'))]} />

      {/* Verificación (la resuelve un supervisor): lo validado se vuelve a mirar; con hallazgo, vuelve a Pendiente */}
      <Tarea x={560} cy={y(2)} lineas={['Verificación: foto nueva,', 'muestreo o cambio de catálogo']} ancho={210} />
      <Flujo
        puntos={[
          [924, y(3)],
          [560, y(3)],
          [560, y(2) + 31],
        ]}
        punteado
      />
      <Flujo
        puntos={[
          [455, y(2)],
          [415, y(2)],
          [415, y(1) + 52],
        ]}
        punteado
      />
      <text x={405} y={y(2) + 16} textAnchor="end" className="fill-por-validar text-[11px]">
        con hallazgo
      </text>
      <text x={405} y={y(2) + 29} textAnchor="end" className="fill-por-validar text-[11px]">
        → Pendiente
      </text>
    </svg>
  );
}

/** Tarjeta de Panorama con el proceso (plegable) y la vista en grande. */
const CLAVE_ABIERTO = 'nexo.panorama.diagrama-abierto';

/** Recuerda (solo en este navegador) si el usuario dejó el diagrama abierto; si el almacenamiento falla, arranca cerrado. */
function leerAbierto() {
  try {
    return localStorage.getItem(CLAVE_ABIERTO) === '1';
  } catch {
    return false;
  }
}

/**
 * Tarjeta plegable: cerrada al entrar (no empuja los gráficos hacia abajo) y recuerda la última elección.
 * «Ver en grande» abre el diagrama en un diálogo sin necesidad de desplegarlo.
 */
export function DiagramaProceso({ porEstado }: { porEstado: Partial<Record<Estado, number>> }) {
  const [abierto, setAbierto] = useState(leerAbierto);
  const [grande, setGrande] = useState(false);
  const alternar = () =>
    setAbierto((a) => {
      try {
        localStorage.setItem(CLAVE_ABIERTO, a ? '0' : '1');
      } catch {
        /* sin almacenamiento: solo dura esta visita */
      }
      return !a;
    });
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
            <span className="block text-sm font-medium">Proceso del artículo</span>
            <span className="block text-xs text-suave">
              De SAP a SAP, con doble control.{' '}
              {abierto ? 'Las cifras son los artículos que hay hoy en cada etapa.' : 'Despliega para ver el diagrama.'}
            </span>
          </span>
          <ChevronDown
            className={`ml-auto size-4 shrink-0 text-suave transition-transform ${abierto ? 'rotate-180' : ''}`}
            aria-hidden
          />
          <span className="sr-only">{abierto ? 'Ocultar diagrama' : 'Mostrar diagrama'}</span>
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
        <div id="panorama-diagrama" className="overflow-x-auto border-t border-borde p-3">
          <Diagrama porEstado={porEstado} />
        </div>
      )}
      <Dialogo abierto={grande} alCerrar={() => setGrande(false)} titulo="Proceso del artículo (BPMN)" amplio>
        <div className="overflow-x-auto">
          <Diagrama porEstado={porEstado} />
        </div>
        <p className="mt-3 text-xs text-suave">
          ○ inicio · ◉ fin · rectángulo: tarea · rombo: decisión · línea punteada: vuelve a Pendiente. Para enviar a
          revisión hacen falta el tipo de parte, el vehículo principal confirmado y los atributos obligatorios.
        </p>
      </Dialogo>
    </section>
  );
}
