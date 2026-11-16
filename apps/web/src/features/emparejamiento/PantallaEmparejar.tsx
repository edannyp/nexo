import { useObtenerArticulo } from '@nexo/api-client';
import { Link, useParams, useSearch } from '@tanstack/react-router';
import { ArrowLeft, ExternalLink } from 'lucide-react';

import { rutaSeccion } from '@/app/navegacion';
import { EtiquetaEstado } from '@/shared/estados';
import { useRecorrido } from '@/shared/recorrido';
import { Aviso } from '@/shared/ui';

import { Emparejador } from './Emparejador';

/** Emparejar un artículo (ADR 0028): encabezado con lo que lo identifica y el emparejador. Sin reserva ni cambio de estado. */
export function PantallaEmparejar() {
  useRecorrido('emparejar');
  const { itemCode } = useParams({ strict: false }) as { itemCode: string };
  const { parte } = useSearch({ strict: false }) as { parte?: number };
  const q = useObtenerArticulo(itemCode);
  const a = q.data;

  return (
    <div className="space-y-4">
      <header className="space-y-1 border-b border-borde pb-3">
        <Link
          to={rutaSeccion('/emparejamiento')}
          className="inline-flex items-center gap-1 text-xs text-suave hover:text-texto"
        >
          <ArrowLeft className="size-3.5" aria-hidden /> Emparejamiento
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h1 className="flex flex-wrap items-center gap-x-3 gap-y-1 text-lg font-semibold">
              {itemCode.toUpperCase()}
              {a && <EtiquetaEstado estado={a.estado} />}
              {a && !a.activo && <span className="text-sm font-normal text-rechazado">Inactivo</span>}
            </h1>
            {a && (
              <p className="text-sm text-suave">
                {a.descripcion_nexo ?? a.descripcion}
                {a.descripcion_nexo && a.descripcion && a.descripcion !== a.descripcion_nexo && (
                  <span className="block text-xs">SAP: {a.descripcion}</span>
                )}
              </p>
            )}
          </div>
          <Link
            to="/articulos/$itemCode"
            params={{ itemCode }}
            className="flex items-center gap-1 rounded-md border border-borde px-2 py-1 text-xs hover:bg-superficie-2"
          >
            Ver artículo <ExternalLink className="size-3.5" aria-hidden />
          </Link>
        </div>
      </header>
      {q.isError ? (
        <Aviso tono="error" titulo={q.error.problema.title} />
      ) : (
        <Emparejador key={itemCode} itemCode={itemCode} parteInicial={parte} />
      )}
    </div>
  );
}
