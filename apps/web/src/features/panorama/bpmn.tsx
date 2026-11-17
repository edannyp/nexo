/*
 * Piezas para dibujar procesos en notación BPMN con SVG propio: carriles por participante, eventos de inicio y fin, tareas,
 * decisiones y flujos (punteado = vuelta o camino alterno). Colores del tema (claro y oscuro) y sin librería.
 */
import { createContext, useContext, useId, type ReactNode } from 'react';

import { numero } from '@/shared/formato';

export const ANCHO = 1180;
const ROTULO = 44; // columna con el nombre del carril

/** Carril con su alto (en unidades del dibujo). */
export interface Carril {
  nombre: string;
  alto: number;
}

/** Centro vertical del carril `k`. */
export const centro = (carriles: Carril[], k: number) =>
  carriles.slice(0, k).reduce((s, c) => s + c.alto, 0) + (carriles[k]?.alto ?? 0) / 2;

// Ids de las flechas, únicos por dibujo (el mismo proceso puede estar en la tarjeta y en el diálogo a la vez)
const Marcadores = createContext({ flecha: 'flecha', punteada: 'flecha-punteada' });

/** El dibujo: marcadores de flecha y los carriles de fondo; el proceso va como hijos. */
export function Lienzo({ carriles, titulo, children }: { carriles: Carril[]; titulo: string; children: ReactNode }) {
  const id = useId().replace(/:/g, '');
  const ids = { flecha: `${id}-flecha`, punteada: `${id}-punteada` };
  const alto = carriles.reduce((s, c) => s + c.alto, 0);
  return (
    <svg viewBox={`0 0 ${ANCHO} ${alto}`} className="h-auto w-full min-w-[56rem]" role="img" aria-label={titulo}>
      <defs>
        {(
          [
            [ids.flecha, 'fill-texto/60'],
            [ids.punteada, 'fill-por-validar'],
          ] as const
        ).map(([m, clase]) => (
          <marker
            key={m}
            id={m}
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path d="M0 0 L10 5 L0 10 z" className={clase} />
          </marker>
        ))}
      </defs>
      {carriles.map((c, k) => {
        const top = centro(carriles, k) - c.alto / 2;
        return (
          <g key={c.nombre}>
            <rect
              x={0.5}
              y={top + 0.5}
              width={ANCHO - 1}
              height={c.alto}
              className={k % 2 ? 'fill-superficie-2/50 stroke-borde' : 'fill-superficie stroke-borde'}
            />
            <rect x={0.5} y={top + 0.5} width={ROTULO} height={c.alto} className="fill-superficie-2 stroke-borde" />
            <text
              transform={`translate(${ROTULO / 2 + 5}, ${top + c.alto / 2}) rotate(-90)`}
              textAnchor="middle"
              className="fill-texto text-[12px] font-semibold"
            >
              {c.nombre}
            </text>
          </g>
        );
      })}
      <Marcadores.Provider value={ids}>{children}</Marcadores.Provider>
    </svg>
  );
}

/** Tarea: rectángulo redondeado con una o dos líneas y, si corresponde, una cifra en vivo debajo. */
export function Tarea({
  x,
  cy,
  lineas,
  insignia,
  ancho = 150,
}: {
  x: number;
  cy: number;
  lineas: string[];
  insignia?: { texto: string; cantidad?: number; color: string };
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
      {insignia && (
        <g transform={`translate(${x - ancho / 2 + 6}, ${cy + alto / 2 + 4})`}>
          <rect width={ancho - 12} height={18} rx={9} fill={insignia.color} opacity={0.15} />
          <text
            x={(ancho - 12) / 2}
            y={13}
            textAnchor="middle"
            className="text-[11px] font-semibold"
            fill={insignia.color}
          >
            {insignia.texto}
            {insignia.cantidad !== undefined ? ` · ${numero(insignia.cantidad)}` : ''}
          </text>
        </g>
      )}
    </g>
  );
}

/** Compuerta exclusiva (rombo con X) con su pregunta encima (o debajo, si arriba pasa un flujo). */
export function Decision({ x, cy, pregunta, abajo }: { x: number; cy: number; pregunta: string; abajo?: boolean }) {
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
      <text x={x} y={abajo ? cy + r + 16 : cy - r - 8} textAnchor="middle" className="fill-suave text-[11px]">
        {pregunta}
      </text>
    </g>
  );
}

/** Evento de inicio (círculo fino) o de fin (círculo grueso), con su texto debajo. */
export function Evento({ x, cy, fin, lineas }: { x: number; cy: number; fin?: boolean; lineas: string[] }) {
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

/** Flujo de secuencia; `etiqueta` va junto al primer tramo. Punteado = vuelta o camino alterno. */
export function Flujo({
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
  const ids = useContext(Marcadores);
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
        markerEnd={`url(#${punteado ? ids.punteada : ids.flecha})`}
      />
      {etiqueta && (
        <text x={x0 + dx} y={y0 + dy} className={punteado ? 'fill-por-validar text-[11px]' : 'fill-suave text-[11px]'}>
          {etiqueta}
        </text>
      )}
    </g>
  );
}

/** Texto suelto (nota), en una o varias líneas. */
export function Nota({
  x,
  y,
  lineas,
  ancla = 'start',
  tono = 'suave',
}: {
  x: number;
  y: number;
  lineas: string[];
  ancla?: 'start' | 'middle' | 'end';
  tono?: 'suave' | 'aviso' | 'rechazado';
}) {
  const clase = { suave: 'fill-suave', aviso: 'fill-por-validar', rechazado: 'fill-rechazado font-semibold' }[tono];
  return (
    <>
      {lineas.map((l, k) => (
        <text key={l} x={x} y={y + k * 13} textAnchor={ancla} className={`${clase} text-[11px]`}>
          {l}
        </text>
      ))}
    </>
  );
}
