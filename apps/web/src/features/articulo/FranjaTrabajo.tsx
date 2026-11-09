import { ProblemaError, useAjustarDescripcion, useListarAplicaciones, type ArticuloDetalle } from '@nexo/api-client';
import { Pencil, RotateCcw, Star } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import { Aviso, Boton, Insignia } from '@/shared/ui';

import { Carrusel } from './Resumen';

/** El vehículo principal en una línea: «★ Toyota Hilux 1994 · DLX · 2.4L L4 22R». */
function PrincipalEnLinea({ itemCode }: { itemCode: string }) {
  const q = useListarAplicaciones(itemCode);
  const p = q.data?.grupos.find((g) => g.principal);
  return (
    <p className="flex items-start gap-1.5 text-sm">
      <Star className="mt-0.5 size-4 shrink-0 text-primario" aria-hidden />
      {q.isLoading ? (
        <span className="text-suave">Cargando…</span>
      ) : p ? (
        <span>
          <span className="font-medium">{p.titulo}</span> <span className="tabular-nums">{p.anios}</span>
          <span className="text-suave"> · {p.detalle}</span>
          {p.sugeridos > 0 && <span className="text-por-validar"> · falta confirmarlo</span>}
        </span>
      ) : (
        <span className="text-suave">Sin vehículo principal: elígelo en Aplicaciones.</span>
      )}
    </p>
  );
}

/**
 * Franja del modo Trabajar (ADR 0027), encima de las pestañas: la foto y lo que define al artículo, a la vista mientras se
 * trabaja: la descripción sugerida por Nexo (se ajusta aquí o vuelve a la automática), la de SAP y el vehículo principal.
 * `alGuardar` recibe el artículo actualizado.
 */
export function FranjaTrabajo({ a, alGuardar }: { a: ArticuloDetalle; alGuardar: (d: ArticuloDetalle) => void }) {
  const ajustar = useAjustarDescripcion();
  const [editando, setEditando] = useState(false);
  const problema = ajustar.error instanceof ProblemaError ? ajustar.error.problema : null;
  const enviar = (texto: string | null) =>
    ajustar.mutate(
      { itemCode: a.item_code, data: { version: a.version, texto } },
      { onSuccess: (d) => (alGuardar(d), setEditando(false)) },
    );
  const guardar = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const texto = String(new FormData(e.currentTarget).get('texto') ?? '').trim();
    if (texto) enviar(texto);
  };

  return (
    <section aria-label="Lo que define al artículo" className="grid gap-3 sm:grid-cols-[13rem_minmax(0,1fr)]">
      <div className="hidden sm:block">
        <Carrusel itemCode={a.item_code} />
      </div>
      <div className="space-y-3 rounded-lg border border-borde bg-superficie p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-xs font-medium tracking-wide text-suave uppercase">
            Descripción sugerida
            <Insignia className="font-normal normal-case">
              {a.descripcion_nexo_manual ? 'ajustada' : 'automática'}
            </Insignia>
          </h2>
          {!editando && (
            <div className="flex gap-1">
              {a.descripcion_nexo_manual && (
                <Boton
                  variante="fantasma"
                  className="h-8 px-2 text-xs"
                  cargando={ajustar.isPending}
                  onClick={() => enviar(null)}
                >
                  <RotateCcw className="size-4" aria-hidden /> Volver a la automática
                </Boton>
              )}
              <Boton variante="secundario" className="h-8 px-2 text-xs" onClick={() => setEditando(true)}>
                <Pencil className="size-4" aria-hidden /> Ajustar
              </Boton>
            </div>
          )}
        </div>
        {editando ? (
          <form onSubmit={guardar} className="flex flex-wrap items-center gap-2">
            <input
              name="texto"
              required
              maxLength={100}
              autoFocus
              defaultValue={a.descripcion_nexo ?? a.descripcion ?? ''}
              aria-label="Descripción de Nexo"
              className="h-10 min-w-0 flex-1 rounded-md border border-borde bg-superficie px-3 text-base uppercase sm:text-sm"
            />
            <Boton type="submit" cargando={ajustar.isPending}>
              Guardar
            </Boton>
            <Boton variante="fantasma" onClick={() => setEditando(false)}>
              Cancelar
            </Boton>
          </form>
        ) : a.descripcion_nexo ? (
          <p className="text-lg font-semibold">{a.descripcion_nexo}</p>
        ) : (
          <p className="text-sm text-suave">Se arma al elegir el vehículo principal.</p>
        )}
        <p className="text-sm">
          <span className="text-suave">SAP: </span>
          {a.descripcion ?? '—'}
        </p>
        <PrincipalEnLinea itemCode={a.item_code} />
        {problema && (
          <Aviso tono="error" titulo={problema.title}>
            {problema.detail}
          </Aviso>
        )}
      </div>
    </section>
  );
}
