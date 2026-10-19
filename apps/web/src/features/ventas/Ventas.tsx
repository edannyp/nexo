import { useAnalizarVentas } from '@nexo/api-client';
import { useState } from 'react';

import { useFiltro } from '@/app/contexto-filtro';
import { cn } from '@/shared/cn';
import { EtiquetaEstado } from '@/shared/estados';
import { mes, momento, numero, porcentaje } from '@/shared/formato';
import { Columnas, Minigrafico, Tendencia } from '@/shared/graficos';
import { Aviso } from '@/shared/ui';

const CLASES = ['Todas', 'A', 'B', 'C'] as const;

/** Análisis de ventas del tipo elegido (ADR 0022): unidades, nunca montos. Requiere el permiso VER_ANALISIS_VENTAS. */
export function Ventas() {
  const { filtro } = useFiltro();
  const q = useAnalizarVentas(filtro, { query: { placeholderData: (previo) => previo } });
  const [clase, setClase] = useState<(typeof CLASES)[number]>('Todas');
  const d = q.data;
  const articulos = d?.articulos.filter((a) => clase === 'Todas' || a.clase === clase) ?? [];

  return (
    <div className="space-y-4">
      <header>
        <h1 className="text-xl font-semibold">Ventas</h1>
        <p className="text-sm text-suave">
          Unidades vendidas (todas las sucursales). Sin montos.{' '}
          {d?.actualizado_en && <>Actualizado: {momento(d.actualizado_en)}</>}
        </p>
      </header>

      {q.isError && (
        <Aviso tono="error" titulo="No se pudo cargar el análisis">
          {q.error.problema.title}
        </Aviso>
      )}

      {d && (
        <div className={cn('space-y-4', q.isPlaceholderData && 'opacity-60')}>
          <section className="rounded-lg border border-borde bg-superficie p-4">
            <Columnas
              titulo="Unidades por mes · últimos 24 meses"
              unidad="Unidades"
              datos={d.serie.map((p) => ({ etiqueta: mes(p.mes), valor: Number(p.unidades) }))}
            />
          </section>

          <section className="rounded-lg border border-borde bg-superficie p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-medium">Artículos que más venden · últimos {d.meses} meses</h2>
              <div className="flex gap-1" role="group" aria-label="Filtrar por clase">
                {CLASES.map((c) => (
                  <button
                    key={c}
                    type="button"
                    aria-pressed={clase === c}
                    onClick={() => setClase(c)}
                    className="rounded-md border border-borde px-2.5 py-1 text-xs aria-pressed:border-primario aria-pressed:bg-superficie-2"
                  >
                    {c === 'Todas' ? c : `Clase ${c}`}
                  </button>
                ))}
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[44rem] text-sm">
                <thead className="text-left text-xs text-suave">
                  <tr>
                    <th className="py-1.5 pr-2 font-medium">Artículo</th>
                    <th className="py-1.5 pr-2 font-medium">Estado</th>
                    <th className="py-1.5 pr-2 text-right font-medium">Clase</th>
                    <th className="py-1.5 pr-2 text-right font-medium">Unidades</th>
                    <th className="py-1.5 pr-2 text-right font-medium">Part.</th>
                    <th className="py-1.5 pr-2 text-right font-medium">Tendencia</th>
                    <th className="py-1.5 pr-2 font-medium">12 meses</th>
                    <th className="py-1.5 font-medium" title="Clasificación ABC-XYZ global de la empresa">
                      ABC-XYZ
                    </th>
                  </tr>
                </thead>
                <tbody className="tabular-nums">
                  {articulos.map((a) => (
                    <tr key={a.articulo_id} className="border-t border-borde">
                      <td className="py-1.5 pr-2">
                        <span className="font-medium">{a.item_code}</span>
                        <span className="block max-w-64 truncate text-xs text-suave">{a.descripcion}</span>
                      </td>
                      <td className="py-1.5 pr-2">
                        <EtiquetaEstado estado={a.estado} />
                      </td>
                      <td className="py-1.5 pr-2 text-right">{a.clase ?? '—'}</td>
                      <td className="py-1.5 pr-2 text-right">{numero(a.unidades)}</td>
                      <td className="py-1.5 pr-2 text-right">{porcentaje(a.participacion)}</td>
                      <td className="py-1.5 pr-2 text-right">
                        <Tendencia valor={a.tendencia} />
                      </td>
                      <td className="py-1.5 pr-2">
                        <Minigrafico
                          valores={a.serie.map(Number)}
                          etiqueta={`Últimos 12 meses: ${a.serie.map((v) => numero(v)).join(', ')}`}
                        />
                      </td>
                      <td className="py-1.5 text-suave">{a.abcxyz_empresa ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
