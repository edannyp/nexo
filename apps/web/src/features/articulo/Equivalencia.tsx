import {
  ProblemaError,
  useCapturarCodigoEquivalente,
  useConfirmarEquivalencia,
  useObtenerEquivalencia,
  useValidarCodigoEquivalente,
  type Estado,
} from '@nexo/api-client';
import { Link } from '@tanstack/react-router';
import { Check, CircleCheck, GitMerge, ShieldCheck } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import { cn } from '@/shared/cn';
import { EtiquetaEstado } from '@/shared/estados';
import { momento } from '@/shared/formato';
import { Aviso, Boton, Insignia } from '@/shared/ui';

export const ESTADOS_CODIGO = [
  ['SIN_CODIGO', 'Sin código'],
  ['ESPERA_FOTO', 'Espera foto'],
  ['LISTO_PARA_VALIDAR', 'Listo para validar'],
  ['VALIDADO', 'Validado'],
] as const;

/** Mensaje tras confirmar, sin cifras en cero. */
export function textoHerencia(h?: { partes: number; aplicaciones_sugeridas: number } | null): string {
  if (!h) return 'Equivalencia confirmada.';
  const partes = [
    h.partes ? `${h.partes} ${h.partes === 1 ? 'parte' : 'partes'}` : '',
    h.aplicaciones_sugeridas
      ? `${h.aplicaciones_sugeridas} ${h.aplicaciones_sugeridas === 1 ? 'aplicación' : 'aplicaciones'}`
      : '',
  ].filter(Boolean);
  return partes.length
    ? `Equivalencia confirmada. Heredado como sugerencias: ${partes.join(' y ')} (revísalas en Aplicaciones y Emparejamiento).`
    : 'Equivalencia confirmada. El importado aún no tiene parte ni aplicaciones confirmadas: no se heredó nada.';
}

const n = (x?: string | null) => (x == null ? '—' : String(Number(x)));

/** Pasos del código equivalente, con el actual resaltado. */
export function PasosCodigo({ estado }: { estado: string }) {
  const actual = ESTADOS_CODIGO.findIndex(([e]) => e === estado);
  return (
    <ol className="flex flex-wrap gap-1.5 text-xs" aria-label="Estado del código equivalente">
      {ESTADOS_CODIGO.map(([e, etiqueta], i) => (
        <li
          key={e}
          aria-current={i === actual ? 'step' : undefined}
          className={cn(
            'rounded-full border px-2.5 py-1',
            i === actual
              ? 'border-primario bg-primario/10 font-medium text-texto'
              : i < actual
                ? 'border-validado/40 text-validado'
                : 'border-borde text-suave',
          )}
        >
          {etiqueta}
        </li>
      ))}
    </ol>
  );
}

/** Pestaña Equivalencia (propuesta UX §6.4, ADR 0018 y 0005): código equivalente, su validación con foto y el importado equivalente. */
export function Equivalencia({ itemCode }: { itemCode: string }) {
  const q = useObtenerEquivalencia(itemCode);
  const capturar = useCapturarCodigoEquivalente();
  const validar = useValidarCodigoEquivalente();
  const confirmar = useConfirmarEquivalencia();
  const [heredar, setHeredar] = useState(true);
  const [hecho, setHecho] = useState<string>();
  const e = q.data;

  if (q.isError) return <Aviso tono="error" titulo={q.error.problema.title} />;
  if (!e) return <p className="text-sm text-suave">Cargando la equivalencia…</p>;

  const error = [capturar.error, validar.error, confirmar.error].find((x) => x instanceof ProblemaError);
  const guardar = (codigo: string) =>
    capturar.mutate(
      { itemCode, data: { codigo: codigo.trim() || null } },
      {
        onSuccess: (r) =>
          setHecho(r.codigo_equivalente ? `Código guardado: ${r.codigo_equivalente}.` : 'Código quitado.'),
      },
    );
  const enviar = (ev: FormEvent<HTMLFormElement>) => {
    ev.preventDefault();
    guardar(String(new FormData(ev.currentTarget).get('codigo') ?? ''));
  };
  const i = e.importado;

  return (
    <div className="space-y-4">
      {error instanceof ProblemaError && (
        <Aviso tono="error" titulo={error.problema.title}>
          {error.problema.detail}
        </Aviso>
      )}
      {hecho && !error && <Aviso tono="exito" titulo={hecho} />}

      <section className="space-y-3 rounded-lg border border-borde bg-superficie p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-xs font-medium tracking-wide text-suave uppercase">Código equivalente</h2>
          <PasosCodigo estado={e.estado_codigo} />
        </div>
        <form key={e.codigo_equivalente ?? ''} onSubmit={enviar} className="flex flex-wrap gap-2">
          <input
            name="codigo"
            aria-label="Código equivalente"
            defaultValue={e.codigo_equivalente ?? ''}
            disabled={!e.puede_capturar}
            placeholder="ItemCode del importado, OEM o código de proveedor"
            autoCapitalize="characters"
            className="h-10 min-w-0 flex-1 rounded-md border border-borde bg-superficie px-3 text-base uppercase disabled:bg-superficie-2 sm:text-sm"
          />
          {e.puede_capturar && (
            <Boton type="submit" variante="secundario" cargando={capturar.isPending}>
              Guardar
            </Boton>
          )}
        </form>
        {e.puede_capturar && e.sugerencias.length > 0 && (
          <p className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-suave">Código anterior en SAP:</span>
            {e.sugerencias.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => guardar(s)}
                className="rounded-full border border-borde px-2 py-0.5 hover:bg-superficie-2"
              >
                {s}
              </button>
            ))}
          </p>
        )}
        <p className="text-xs text-suave">
          {[
            e.capturado_por &&
              `Capturado por ${e.capturado_por}${e.capturado_en ? `, ${momento(e.capturado_en)}` : ''}`,
            e.validado_por && `Validado por ${e.validado_por}${e.validado_en ? `, ${momento(e.validado_en)}` : ''}`,
            e.estado_codigo !== 'SIN_CODIGO' && `Fotos validadas: ${e.fotos_validadas}`,
            e.estado_codigo === 'ESPERA_FOTO' &&
              'Para validarlo hace falta una foto propia validada (súbela en Fotos; se valida en Verificación)',
          ]
            .filter(Boolean)
            .join(' · ')}
        </p>
        {e.puede_validar && (
          <Boton
            cargando={validar.isPending}
            onClick={() => validar.mutate({ itemCode }, { onSuccess: () => setHecho('Código equivalente validado.') })}
          >
            <ShieldCheck className="size-4" aria-hidden /> Validar código
          </Boton>
        )}
      </section>

      <section className="rounded-lg border border-borde bg-superficie">
        <h2 className="border-b border-borde px-4 py-2 text-xs font-medium tracking-wide text-suave uppercase">
          Importado equivalente
        </h2>
        {!i ? (
          <p className="px-4 py-6 text-center text-sm text-suave">
            Si el código es el ItemCode de un importado de la misma categoría, aquí aparece para confirmarlo y heredar
            sus datos.
          </p>
        ) : (
          <div className={cn('grid gap-4 p-4', i.foto_url && 'sm:grid-cols-[10rem_minmax(0,1fr)]')}>
            {i.foto_url && (
              <img
                src={i.foto_url}
                alt={`Foto de ${i.item_code}`}
                className="aspect-square w-full rounded-md border border-borde object-cover"
              />
            )}
            <div className="space-y-2 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <Link to="/articulos/$itemCode" params={{ itemCode: i.item_code }} className="font-medium underline">
                  {i.item_code}
                </Link>
                <EtiquetaEstado estado={i.estado as Estado} />
                {i.equivalencia === 'CONFIRMADA' ? (
                  <span className="flex items-center gap-1 text-xs text-validado">
                    <CircleCheck className="size-3.5" aria-hidden /> Confirmada
                    {i.confirmada_por && ` por ${i.confirmada_por}`}
                  </span>
                ) : (
                  <Insignia>Sugerida</Insignia>
                )}
              </div>
              <p className="text-suave">{i.descripcion}</p>
              <p className="tabular-nums">
                Panal {n(i.medidas.alto)} × {n(i.medidas.largo)} × {n(i.medidas.ancho)} mm · {i.aplicaciones}{' '}
                aplicaciones confirmadas · {i.partes} {i.partes === 1 ? 'parte' : 'partes'} del catálogo
              </p>
              {i.equivalencia !== 'CONFIRMADA' &&
                (e.editable ? (
                  <div className="space-y-2 border-t border-borde pt-3">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        className="size-4"
                        checked={heredar}
                        onChange={(x) => setHeredar(x.target.checked)}
                      />
                      Heredar su parte y aplicaciones como sugerencias
                    </label>
                    <Boton
                      cargando={confirmar.isPending}
                      onClick={() =>
                        confirmar.mutate(
                          { itemCode, data: { version: e.version, heredar } },
                          {
                            onSuccess: (r) => setHecho(textoHerencia(r.heredado)),
                          },
                        )
                      }
                    >
                      <GitMerge className="size-4" aria-hidden /> Confirmar equivalencia
                    </Boton>
                  </div>
                ) : (
                  <p className="text-xs text-suave">
                    <Check className="mr-1 inline size-3.5" aria-hidden />
                    Para confirmarla: {e.razon_no_editable}
                  </p>
                ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
