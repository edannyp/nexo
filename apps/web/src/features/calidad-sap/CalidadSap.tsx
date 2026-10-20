import { getExportarHallazgosSapUrl, useListarHallazgosSap } from '@nexo/api-client';
import { Download, TriangleAlert } from 'lucide-react';
import { useState } from 'react';

import { useFiltro } from '@/app/contexto-filtro';
import { cn } from '@/shared/cn';
import { momento, numero } from '@/shared/formato';
import { Aviso } from '@/shared/ui';

/**
 * Hallazgos de calidad de SAP del tipo elegido: lo que debe corregirse EN SAP (Nexo no escribe en SAP).
 * Se cierran solos cuando el siguiente lote del ETL trae el dato corregido.
 */
export function CalidadSap() {
  const { filtro } = useFiltro();
  const q = useListarHallazgosSap(filtro, { query: { placeholderData: (previo) => previo } });
  const [grupo, setGrupo] = useState<string | null>(null);
  const clave = (t: string, c: string) => `${t}|${c}`;
  const visibles = q.data?.hallazgos.filter((h) => grupo === null || clave(h.tipo, h.campo_sap) === grupo) ?? [];

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Calidad SAP</h1>
          <p className="text-sm text-suave">
            Datos que hay que corregir en SAP. Desaparecen solos cuando el siguiente lote trae el dato corregido.
          </p>
        </div>
        <a
          href={getExportarHallazgosSapUrl(filtro)}
          className="inline-flex h-10 items-center gap-2 rounded-md border border-borde bg-superficie px-4 text-sm font-medium hover:bg-superficie-2"
          download
        >
          <Download className="size-4" aria-hidden /> Descargar para Excel
        </a>
      </header>

      {q.isError && (
        <Aviso tono="error" titulo="No se pudieron cargar los hallazgos">
          {q.error.problema.title}
        </Aviso>
      )}

      {q.data && (
        <div className={cn('space-y-4', q.isPlaceholderData && 'opacity-60')}>
          {q.data.grupos.length === 0 ? (
            <Aviso tono="exito" titulo="Sin hallazgos abiertos para este tipo de artículo" />
          ) : (
            <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por tipo de hallazgo">
              <button
                type="button"
                onClick={() => setGrupo(null)}
                aria-pressed={grupo === null}
                className="rounded-full border border-borde px-3 py-1 text-sm aria-pressed:border-primario aria-pressed:bg-superficie-2"
              >
                Todos · {numero(q.data.hallazgos.length)}
              </button>
              {q.data.grupos.map((g) => (
                <button
                  key={clave(g.tipo, g.campo_sap)}
                  type="button"
                  onClick={() => setGrupo(clave(g.tipo, g.campo_sap))}
                  aria-pressed={grupo === clave(g.tipo, g.campo_sap)}
                  title={g.descripcion}
                  className="rounded-full border border-borde px-3 py-1 text-sm aria-pressed:border-primario aria-pressed:bg-superficie-2"
                >
                  {g.descripcion.split(' (')[0]} <span className="text-suave">({g.campo_sap})</span> · {numero(g.n)}
                </button>
              ))}
            </div>
          )}

          {/* Celular: tarjetas · escritorio: tabla */}
          <ul className="space-y-2 md:hidden">
            {visibles.map((h) => (
              <li key={h.id} className="rounded-lg border border-borde bg-superficie p-3 text-sm">
                <p className="font-medium">{h.item_code}</p>
                <p className="truncate text-suave">{h.descripcion_articulo}</p>
                <p className="mt-1 flex items-center gap-1.5">
                  <TriangleAlert className="size-3.5 text-rechazado" aria-hidden />
                  {h.campo_sap}: <code className="rounded bg-superficie-2 px-1">{h.valor ?? '(vacío)'}</code>
                </p>
              </li>
            ))}
          </ul>
          {visibles.length > 0 && (
            <div className="hidden overflow-x-auto rounded-lg border border-borde bg-superficie md:block">
              <table className="w-full text-sm">
                <thead className="border-b border-borde text-left text-suave">
                  <tr>
                    <th className="px-3 py-2 font-medium">Artículo</th>
                    <th className="px-3 py-2 font-medium">Campo SAP</th>
                    <th className="px-3 py-2 font-medium">Valor en SAP</th>
                    <th className="px-3 py-2 font-medium">Detectado</th>
                  </tr>
                </thead>
                <tbody>
                  {visibles.map((h) => (
                    <tr key={h.id} className="border-b border-borde last:border-0">
                      <td className="px-3 py-2">
                        <span className="font-medium">{h.item_code}</span>
                        <span className="block max-w-md truncate text-xs text-suave">{h.descripcion_articulo}</span>
                      </td>
                      <td className="px-3 py-2">{h.campo_sap}</td>
                      <td className="px-3 py-2">
                        <code className="rounded bg-superficie-2 px-1">{h.valor ?? '(vacío)'}</code>
                      </td>
                      <td className="px-3 py-2 text-suave">{momento(h.detectado_en)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
