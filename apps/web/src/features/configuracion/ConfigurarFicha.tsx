import {
  getObtenerConfiguracionFichaQueryKey,
  useConfigurarAtributo,
  useListarCategorias,
  useObtenerConfiguracionFicha,
  type AtributoConfig,
} from '@nexo/api-client';
import { useQueryClient } from '@tanstack/react-query';
import { Plus, Search, Settings2 } from 'lucide-react';
import { useState, type ReactNode } from 'react';

import { useFiltro } from '@/app/contexto-filtro';
import { nombreCategoria } from '@/app/FiltroGlobal';
import { cn } from '@/shared/cn';
import { useRecorrido } from '@/shared/recorrido';
import { Aviso, Boton, Insignia } from '@/shared/ui';

import { etiquetaDe, nombreGrupo, nombreTipo, textoError } from './comun';
import { DialogoAtributo } from './DialogoAtributo';
import { DialogoNuevoCampo } from './DialogoNuevoCampo';

type Vista = 'ficha' | 'catalogo';

function Fila({ a, alAbrir, accion }: { a: AtributoConfig; alAbrir: () => void; accion?: ReactNode }) {
  return (
    <li className={cn('flex flex-wrap items-center gap-3 px-4 py-2.5', a.obsoleto && 'opacity-60')}>
      <button type="button" onClick={alAbrir} className="min-w-0 flex-1 text-left text-sm">
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="font-medium">{etiquetaDe(a)}</span>
          {a.obligatorio && (
            <span className="text-rechazado" title="Obligatorio">
              *
            </span>
          )}
          {a.propio && <Insignia className="border-primario/50 text-primario">Propio</Insignia>}
          {a.obsoleto && <Insignia>Obsoleto en AutoCare</Insignia>}
        </span>
        <span className="block text-xs text-suave">
          {nombreTipo(a)} · {nombreGrupo(a.grupo)}
          {!a.propio && a.etiqueta && ` · ${a.nombre}`}
          {a.columna_sap && ` · precarga de SAP: ${a.columna_sap}`}
          {a.en_uso > 0 && ` · ${a.en_uso} artículos con valor`}
        </span>
      </button>
      {accion}
      <Boton variante="fantasma" className="h-8 px-2" onClick={alAbrir} aria-label={`Configurar ${etiquetaDe(a)}`}>
        <Settings2 className="size-4" aria-hidden />
      </Boton>
    </li>
  );
}

/**
 * Configurar la ficha de atributos del tipo de parte elegido (ADR 0019, ADR 0029). Permiso CONFIGURAR_FICHA. Lo que está en la
 * ficha, el resto del catálogo de AutoCare para agregarlo, y los campos propios de Nexo.
 */
export function ConfigurarFicha() {
  useRecorrido('configurar-ficha');
  const { filtro } = useFiltro();
  const categorias = useListarCategorias();
  const categoria = categorias.data?.find((c) => c.codigo === filtro.cat);
  const pt = categoria?.part_terminology_id ?? 0;
  const q = useObtenerConfiguracionFicha(pt, { query: { enabled: pt > 0 } });
  const consultas = useQueryClient();
  const refrescar = () => void consultas.invalidateQueries({ queryKey: getObtenerConfiguracionFichaQueryKey(pt) });
  const cambiar = useConfigurarAtributo({ mutation: { onSuccess: refrescar } });
  const [vista, setVista] = useState<Vista>('ficha');
  const [texto, setTexto] = useState('');
  const [abierto, setAbierto] = useState<number | null>(null);
  const [creando, setCreando] = useState(false);

  const atributos = q.data?.atributos ?? [];
  const enFicha = atributos.filter((a) => a.habilitado);
  const catalogo = atributos
    .filter((a) => !a.habilitado)
    .filter(
      (a) => !texto.trim() || `${a.nombre} ${a.etiqueta ?? ''}`.toLowerCase().includes(texto.trim().toLowerCase()),
    );
  const elegido = atributos.find((a) => a.paid === abierto) ?? null;
  const siguienteOrden = Math.max(0, ...enFicha.map((a) => a.orden ?? 0)) + 1;

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Ficha de atributos</h1>
          <p className="text-sm text-suave">
            {categoria ? nombreCategoria(categoria.nombre) : '…'}
            {pt > 0 && ` · tipo de parte ${pt} de AutoCare`}. Qué atributos se capturan, cuáles son obligatorios y de
            dónde se precargan.
          </p>
        </div>
        {pt > 0 && (
          <Boton onClick={() => setCreando(true)}>
            <Plus className="size-4" aria-hidden /> Nuevo campo propio
          </Boton>
        )}
      </header>

      {categoria && !categoria.part_terminology_id && (
        <Aviso tono="info" titulo="Esta categoría no tiene tipo de parte de AutoCare">
          Sin tipo de parte no hay ficha que configurar. Elige otra categoría arriba.
        </Aviso>
      )}
      {q.isError && <Aviso tono="error" titulo={q.error.problema.title} />}
      {cambiar.error && <Aviso tono="error" titulo={textoError(cambiar.error) ?? ''} />}
      {pt > 0 && !q.data && !q.isError && <p className="text-sm text-suave">Cargando…</p>}

      {q.data && (
        <>
          <div role="tablist" aria-label="Qué atributos ver" className="flex gap-1 border-b border-borde">
            {(
              [
                ['ficha', `En la ficha (${enFicha.length})`],
                ['catalogo', `Catálogo AutoCare (${atributos.length - enFicha.length})`],
              ] as const
            ).map(([id, etiqueta]) => (
              <button
                key={id}
                role="tab"
                type="button"
                aria-selected={vista === id}
                onClick={() => setVista(id)}
                className="-mb-px border-b-2 border-transparent px-3 py-2 text-sm text-suave aria-selected:border-primario aria-selected:font-medium aria-selected:text-texto"
              >
                {etiqueta}
              </button>
            ))}
          </div>

          {vista === 'ficha' ? (
            <section aria-label="Atributos en la ficha" className="rounded-lg border border-borde bg-superficie">
              <p className="border-b border-borde px-4 py-2 text-xs text-suave">
                En el orden en que los ve el operador. * = obligatorio para enviar a revisión.
              </p>
              {enFicha.length === 0 ? (
                <p className="p-6 text-center text-sm text-suave">
                  La ficha está vacía: agrega atributos del catálogo.
                </p>
              ) : (
                <ul className="divide-y divide-borde">
                  {enFicha.map((a) => (
                    <Fila
                      key={a.paid}
                      a={a}
                      alAbrir={() => setAbierto(a.paid)}
                      accion={
                        <div className="flex items-center gap-3">
                          <label className="flex items-center gap-1.5 text-xs text-suave">
                            <input
                              type="checkbox"
                              className="size-4"
                              checked={a.obligatorio}
                              disabled={cambiar.isPending}
                              onChange={(e) =>
                                cambiar.mutate({
                                  partTerminologyId: pt,
                                  paid: a.paid,
                                  data: { obligatorio: e.target.checked },
                                })
                              }
                            />
                            Obligatorio
                          </label>
                          <Boton
                            variante="secundario"
                            className="h-8 px-2 text-xs"
                            disabled={cambiar.isPending}
                            onClick={() =>
                              confirm(
                                `¿Quitar «${etiquetaDe(a)}» de la ficha? Los valores ya capturados se conservan, pero dejan de verse.`,
                              ) && cambiar.mutate({ partTerminologyId: pt, paid: a.paid, data: { habilitado: false } })
                            }
                          >
                            Quitar
                          </Boton>
                        </div>
                      }
                    />
                  ))}
                </ul>
              )}
            </section>
          ) : (
            <section aria-label="Catálogo AutoCare" className="rounded-lg border border-borde bg-superficie">
              <div className="border-b border-borde p-3">
                <label className="relative block">
                  <Search className="absolute top-2.5 left-2.5 size-4 text-suave" aria-hidden />
                  <input
                    type="search"
                    aria-label="Buscar atributo"
                    placeholder="Buscar por nombre (en inglés, como en AutoCare)"
                    value={texto}
                    onChange={(e) => setTexto(e.target.value)}
                    className="h-9 w-full rounded-md border border-borde bg-superficie pr-2 pl-8 text-base sm:text-sm"
                  />
                </label>
              </div>
              {catalogo.length === 0 ? (
                <p className="p-6 text-center text-sm text-suave">
                  {texto ? 'Nada coincide.' : 'Todos los atributos del catálogo ya están en la ficha.'}
                </p>
              ) : (
                <ul className="divide-y divide-borde">
                  {catalogo.map((a) => (
                    <Fila
                      key={a.paid}
                      a={a}
                      alAbrir={() => setAbierto(a.paid)}
                      accion={
                        !a.obsoleto && (
                          <Boton
                            variante="secundario"
                            className="h-8 px-2 text-xs"
                            disabled={cambiar.isPending}
                            onClick={() =>
                              cambiar.mutate({
                                partTerminologyId: pt,
                                paid: a.paid,
                                data: { habilitado: true, ...(a.orden == null ? { orden: siguienteOrden } : {}) },
                              })
                            }
                          >
                            <Plus className="size-3.5" aria-hidden /> Agregar a la ficha
                          </Boton>
                        )
                      }
                    />
                  ))}
                </ul>
              )}
            </section>
          )}
        </>
      )}

      {pt > 0 && (
        <>
          <DialogoAtributo
            key={abierto ?? 0}
            pt={pt}
            a={elegido}
            alCerrar={() => setAbierto(null)}
            alCambiar={refrescar}
          />
          <DialogoNuevoCampo
            key={creando ? 'abierto' : 'cerrado'}
            pt={pt}
            abierto={creando}
            alCerrar={() => setCreando(false)}
            alCrear={(a) => {
              setCreando(false);
              setVista('ficha');
              refrescar();
              setAbierto(a.paid);
            }}
          />
        </>
      )}
    </div>
  );
}
