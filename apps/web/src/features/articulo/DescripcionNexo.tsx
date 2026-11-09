import { ProblemaError, useAjustarDescripcion, type ArticuloDetalle } from '@nexo/api-client';
import { Pencil, RotateCcw } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import { Aviso, Boton, Insignia } from '@/shared/ui';

/**
 * Descripción de Nexo en el modo Trabajar (ADR 0027): la automática se puede ajustar a mano (queda fija) o volver a la automática.
 * `alGuardar` recibe el artículo actualizado.
 */
export function DescripcionNexo({ a, alGuardar }: { a: ArticuloDetalle; alGuardar: (d: ArticuloDetalle) => void }) {
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
    <section aria-label="Descripción de Nexo" className="rounded-lg border border-borde bg-superficie px-4 py-3">
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
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="min-w-0 text-sm">
            <span className="text-suave">Descripción Nexo: </span>
            {a.descripcion_nexo ? (
              <span className="font-medium">{a.descripcion_nexo}</span>
            ) : (
              <span className="text-suave">se arma al elegir el vehículo principal</span>
            )}
            <Insignia className="ml-2 align-middle">{a.descripcion_nexo_manual ? 'ajustada' : 'automática'}</Insignia>
          </p>
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
        </div>
      )}
      {problema && (
        <Aviso tono="error" titulo={problema.title}>
          {problema.detail}
        </Aviso>
      )}
    </section>
  );
}
