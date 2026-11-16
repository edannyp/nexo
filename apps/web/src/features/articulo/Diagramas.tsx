import { useObtenerDiagramas, type ParteVinculada } from '@nexo/api-client';
import { Link } from '@tanstack/react-router';
import { Link2, Star, Unlink } from 'lucide-react';

import { useUsuario } from '@/app/contexto-usuario';
import { tienePermiso } from '@/app/sesion';
import { cn } from '@/shared/cn';
import { Aviso } from '@/shared/ui';

const n = (x?: string | null) => (x == null ? '—' : String(Number(x)));

function Enlace({ v }: { v: ParteVinculada }) {
  const p = v.parte;
  return (
    <li className="flex items-start gap-3 py-2.5">
      {p?.imagen_url ? (
        <img
          src={p.imagen_url}
          alt={`Diagrama de la parte ${v.parte_id}`}
          loading="lazy"
          className="h-14 w-20 shrink-0 rounded border border-borde bg-white object-contain"
        />
      ) : (
        <span className="grid h-14 w-20 shrink-0 place-items-center rounded border border-borde text-xs text-suave">
          Sin imagen
        </span>
      )}
      <div className="min-w-0 flex-1 text-sm">
        <p className="flex items-center gap-1.5 font-medium">
          {v.es_principal && <Star className="size-4 shrink-0 fill-current text-por-validar" aria-label="Principal" />}
          <span className="truncate">{p?.descripcion ?? `Parte ${v.parte_id}`}</span>
        </p>
        <p className="text-xs text-suave tabular-nums">
          Parte {v.parte_id}
          {p && ` · ${n(p.medidas.alto)}×${n(p.medidas.largo)}×${n(p.medidas.ancho)} mm`}
          {p?.numeros ? ` · ${p.numeros}` : ''}
        </p>
        <p className="text-xs text-suave">
          {v.es_principal ? 'Principal' : 'Secundaria'}
          {v.confirmado_por && ` · enlazó ${v.confirmado_por}`}
        </p>
        {p && p.estado !== 'ACTIVA' && (
          <p className="text-xs text-rechazado">
            {p.estado === 'FUSIONADA'
              ? `En el catálogo se fusionó en la parte ${p.fusionada_en_id}.`
              : 'El catálogo la descartó.'}
          </p>
        )}
      </div>
    </li>
  );
}

/**
 * Diagramas del artículo (ADR 0028): de solo lectura, a qué partes del catálogo maestro está enlazado. Emparejar ya no es parte
 * del proceso del artículo: se hace en la sección Emparejamiento, con el permiso EMPAREJAR_CATALOGO.
 */
export function Diagramas({ itemCode, className }: { itemCode: string; className?: string }) {
  const usuario = useUsuario();
  const q = useObtenerDiagramas(itemCode);
  const d = q.data;
  const puedeEmparejar = tienePermiso(usuario, 'EMPAREJAR_CATALOGO');

  return (
    <section
      data-recorrido="diagramas"
      aria-label="Diagramas"
      className={cn('rounded-lg border border-borde bg-superficie p-4', className)}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xs font-medium tracking-wide text-suave uppercase">Diagramas</h2>
        {puedeEmparejar && (
          <Link
            to="/emparejamiento/$itemCode"
            params={{ itemCode }}
            className="flex items-center gap-1 rounded-md border border-borde px-2 py-1 text-xs hover:bg-superficie-2"
          >
            <Link2 className="size-3.5" aria-hidden /> Emparejar
          </Link>
        )}
      </div>
      {q.isError && <Aviso tono="error" titulo={q.error.problema.title} />}
      {!d && !q.isError && <p className="mt-2 text-sm text-suave">Cargando…</p>}
      {d && d.vinculadas.length === 0 && (
        <p className="mt-3 flex items-center gap-2 text-sm text-suave">
          <Unlink className="size-4 shrink-0" aria-hidden /> Artículo sin enlace a diagramas
        </p>
      )}
      {d && d.vinculadas.length > 0 && (
        <>
          <ul className="mt-1 divide-y divide-borde">
            {d.vinculadas.map((v) => (
              <Enlace key={v.parte_id} v={v} />
            ))}
          </ul>
          {!d.catalogo_disponible && (
            <p className="text-xs text-suave">Catálogo maestro no disponible: se ven solo por su número.</p>
          )}
        </>
      )}
    </section>
  );
}
