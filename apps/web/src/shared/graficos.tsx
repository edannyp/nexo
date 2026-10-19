/**
 * Gráficos de la consola, en HTML/SVG propio (sin librerías). Reglas de la guía de visualización:
 * un solo tono para magnitud, escala ordinal de la misma rampa, barras finas con extremo redondeado y base recta,
 * separación de 2 px entre segmentos, texto con tokens de texto (nunca del color del dato), detalle al pasar el cursor
 * o con el foco del teclado, y los valores siempre accesibles sin el detalle (etiquetas, leyenda o tabla).
 */
import { useId, useState, type ReactNode } from 'react';

import { cn } from './cn';
import { numero, numeroCompacto, porcentaje } from './formato';

/** Fila de barra horizontal: etiqueta, barra proporcional y valor al final. */
export function FilaBarra({
  etiqueta,
  valor,
  maximo,
  texto,
  icono,
}: {
  etiqueta: ReactNode;
  valor: number;
  maximo: number;
  texto?: string;
  icono?: ReactNode;
}) {
  const ancho = maximo > 0 ? Math.max((valor / maximo) * 100, valor > 0 ? 1.5 : 0) : 0;
  return (
    <div className="grid grid-cols-[minmax(7rem,9rem)_1fr_auto] items-center gap-3 text-sm">
      <span className="flex items-center gap-2 truncate">
        {icono}
        {etiqueta}
      </span>
      <span className="h-3 rounded-r-[4px] bg-transparent" aria-hidden>
        <span className="block h-full rounded-r-[4px] bg-viz-barra" style={{ width: `${ancho}%` }} />
      </span>
      <span className="min-w-12 text-right tabular-nums">{texto ?? numero(valor)}</span>
    </div>
  );
}

export interface Segmento {
  etiqueta: string;
  valor: number;
  clase: string; // clase de color de fondo (bg-viz-…)
}

/** Barra apilada sobre un riel: segmentos con separación de 2 px; el riel representa el resto del total. */
export function BarraApilada({
  segmentos,
  total,
  etiqueta,
}: {
  segmentos: Segmento[];
  total: number;
  etiqueta: string;
}) {
  const descripcion = segmentos.map((s) => `${s.etiqueta}: ${numero(s.valor)}`).join(', ');
  return (
    <div
      className="flex h-3 gap-0.5 overflow-hidden rounded-r-[4px] bg-borde"
      role="img"
      aria-label={`${etiqueta}. ${descripcion} de ${numero(total)}`}
      title={`${descripcion} de ${numero(total)}`}
    >
      {segmentos
        .filter((s) => s.valor > 0)
        .map((s) => (
          <span
            key={s.etiqueta}
            className={cn('h-full last:rounded-r-[4px]', s.clase)}
            style={{ width: `${(s.valor / total) * 100}%` }}
          />
        ))}
    </div>
  );
}

/** Leyenda con muestra del mismo tipo que la marca (rectángulo para barras). */
export function Leyenda({ items }: { items: { etiqueta: string; clase: string }[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-suave">
      {items.map((i) => (
        <li key={i.etiqueta} className="flex items-center gap-1.5">
          <span className={cn('size-2.5 rounded-[2px]', i.clase)} aria-hidden />
          {i.etiqueta}
        </li>
      ))}
    </ul>
  );
}

/** Medidor: parte de un total, con el riel en un paso claro de la misma rampa. */
export function Medidor({ etiqueta, valor, total }: { etiqueta: string; valor: number; total: number }) {
  const f = total > 0 ? valor / total : 0;
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span>{etiqueta}</span>
        <span className="text-suave">
          <span className="font-medium text-texto">{porcentaje(f, 0)}</span> · {numero(valor)} de {numero(total)}
        </span>
      </div>
      <div
        className="h-2 rounded-full bg-viz-riel"
        role="meter"
        aria-label={etiqueta}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={valor}
      >
        <div className="h-full rounded-full bg-viz-barra" style={{ width: `${f * 100}%` }} />
      </div>
    </div>
  );
}

/** Ticks limpios del eje: 0, la mitad y un máximo redondeado. */
function ticks(maximo: number): number[] {
  if (maximo <= 0) return [0];
  const paso = 10 ** Math.floor(Math.log10(maximo));
  const tope = Math.ceil(maximo / paso) * paso;
  return [0, tope / 2, tope];
}

/**
 * Columnas de una sola serie (p. ej. unidades por mes). Cada columna es su propio objetivo de cursor y de foco, y muestra
 * el detalle; "Ver tabla" da los mismos valores sin depender del cursor.
 */
export function Columnas({
  datos,
  titulo,
  unidad,
}: {
  datos: { etiqueta: string; valor: number }[];
  titulo: string;
  unidad: string;
}) {
  const [activo, setActivo] = useState<number | null>(null);
  const [tabla, setTabla] = useState(false);
  const id = useId();
  const marcas = ticks(Math.max(...datos.map((d) => d.valor), 0));
  const tope = marcas[marcas.length - 1] ?? 1;
  const ultimo = datos.length - 1;

  return (
    <figure className="space-y-3">
      <figcaption className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium" id={id}>
          {titulo}
        </span>
        <button
          type="button"
          onClick={() => setTabla((t) => !t)}
          className="text-xs text-suave underline hover:text-texto"
        >
          {tabla ? 'Ver gráfico' : 'Ver tabla'}
        </button>
      </figcaption>
      {tabla ? (
        <div className="max-h-72 overflow-auto">
          <table className="w-full text-sm" aria-labelledby={id}>
            <thead className="text-left text-suave">
              <tr>
                <th className="py-1 font-medium">Mes</th>
                <th className="py-1 text-right font-medium">{unidad}</th>
              </tr>
            </thead>
            <tbody className="tabular-nums">
              {datos.map((d) => (
                <tr key={d.etiqueta} className="border-t border-borde">
                  <td className="py-1">{d.etiqueta}</td>
                  <td className="py-1 text-right">{numero(d.valor)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="grid grid-cols-[auto_1fr] gap-2">
          {/* Eje Y: ticks redondos y compactos */}
          <div
            className="flex h-48 flex-col-reverse justify-between text-right text-xs text-suave tabular-nums"
            aria-hidden
          >
            {marcas.map((t) => (
              <span key={t} className="-my-1.5 leading-3">
                {numeroCompacto(t)}
              </span>
            ))}
          </div>
          <div>
            <div className="relative h-48" role="list" aria-labelledby={id}>
              {/* Líneas guía: finas, sólidas y discretas */}
              {marcas.map((t) => (
                <span
                  key={t}
                  className="absolute inset-x-0 border-t border-borde"
                  style={{ bottom: `${(t / tope) * 100}%` }}
                  aria-hidden
                />
              ))}
              <div className="absolute inset-0 flex items-end gap-0.5">
                {datos.map((d, i) => (
                  <div
                    key={d.etiqueta}
                    role="listitem"
                    tabIndex={0}
                    aria-label={`${d.etiqueta}: ${numero(d.valor)} ${unidad.toLowerCase()}`}
                    onPointerEnter={() => setActivo(i)}
                    onPointerLeave={() => setActivo(null)}
                    onFocus={() => setActivo(i)}
                    onBlur={() => setActivo(null)}
                    className="group relative flex h-full flex-1 cursor-default items-end justify-center outline-none"
                  >
                    <span
                      className={cn(
                        'w-full max-w-6 rounded-t-[4px] bg-viz-barra transition-opacity',
                        activo !== null && activo !== i && 'opacity-50',
                      )}
                      style={{ height: `${(d.valor / tope) * 100}%` }}
                    />
                    {activo === i && (
                      <span
                        role="tooltip"
                        className={cn(
                          'absolute bottom-full z-10 mb-1 rounded-md border border-borde bg-superficie px-2 py-1 text-xs whitespace-nowrap shadow',
                          i > datos.length * 0.7 ? 'right-0' : i < datos.length * 0.3 ? 'left-0' : '',
                        )}
                      >
                        <strong className="tabular-nums">{numero(d.valor)}</strong>{' '}
                        <span className="text-suave">{d.etiqueta}</span>
                      </span>
                    )}
                    {/* Etiqueta directa solo en la última columna (el dato más reciente) */}
                    {i === ultimo && activo === null && (
                      <span className="absolute -top-5 text-xs font-medium tabular-nums">
                        {numeroCompacto(d.valor)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
            {/* Eje X: primera, intermedia y última etiqueta */}
            <div className="mt-1 flex justify-between text-xs text-suave" aria-hidden>
              <span>{datos[0]?.etiqueta}</span>
              <span>{datos[Math.floor(ultimo / 2)]?.etiqueta}</span>
              <span>{datos[ultimo]?.etiqueta}</span>
            </div>
          </div>
        </div>
      )}
    </figure>
  );
}

/** Minigráfico de 12 puntos: línea en tono atenuado y el último punto resaltado. */
export function Minigrafico({ valores, etiqueta }: { valores: number[]; etiqueta: string }) {
  const max = Math.max(...valores, 1);
  const w = 72;
  const h = 20;
  const x = (i: number) => (valores.length > 1 ? (i / (valores.length - 1)) * (w - 6) + 3 : w / 2);
  const y = (v: number) => h - 3 - (v / max) * (h - 6);
  const puntos = valores.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
  const ultimo = valores.length - 1;
  return (
    <svg width={w} height={h} role="img" aria-label={etiqueta} className="overflow-visible">
      <polyline
        points={puntos}
        fill="none"
        stroke="var(--suave)"
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {ultimo >= 0 && (
        <circle
          cx={x(ultimo)}
          cy={y(valores[ultimo] ?? 0)}
          r={3}
          fill="var(--viz-barra)"
          stroke="var(--superficie)"
          strokeWidth={2}
        />
      )}
    </svg>
  );
}

/** Tendencia con flecha, signo y texto (nunca solo color): subir es bueno en ventas. */
export function Tendencia({ valor }: { valor: number | string | null | undefined }) {
  if (valor === null || valor === undefined) return <span className="text-suave">—</span>;
  const v = Number(valor);
  const texto = `${v > 0 ? '+' : ''}${porcentaje(v, 0)}`;
  if (Math.abs(v) < 0.005) return <span className="text-suave">= {texto}</span>;
  return (
    <span
      className={cn('tabular-nums', v > 0 ? 'text-validado' : 'text-rechazado')}
      aria-label={`${v > 0 ? 'Sube' : 'Baja'} ${texto}`}
    >
      {v > 0 ? '↑' : '↓'} {texto}
    </span>
  );
}
