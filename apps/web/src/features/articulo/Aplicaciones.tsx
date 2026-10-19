import {
  ProblemaError,
  useAgregarAplicaciones,
  useConfirmarAplicaciones,
  useListarAplicaciones,
  useListarConfiguraciones,
  useListarMarcas,
  useListarModelos,
  useQuitarAplicaciones,
  useRegistrarVehiculoExterno,
  type Aplicaciones as RespuestaAplicaciones,
  type ConfiguracionAgrupada,
  type GrupoAplicacion,
  type NuevaAplicacion,
  type SugerenciaSap,
} from '@nexo/api-client';
import { useQueryClient } from '@tanstack/react-query';
import { Check, CircleCheck, Plus, Search, Trash2 } from 'lucide-react';
import { useMemo, useState, type FormEvent } from 'react';

import { cn } from '@/shared/cn';
import { Aviso, Boton, Campo, Dialogo, Insignia } from '@/shared/ui';

import { faltantes, rangos } from './anios';

const ANIO_ACTUAL = new Date().getFullYear();
const MAX_ANIOS = 40;
const MAX_ITEMS = 200;

const control =
  'h-10 w-full rounded-md border border-borde bg-superficie px-3 text-base disabled:bg-superficie-2 disabled:text-suave sm:text-sm';

const ORIGEN: Record<string, string> = {
  MANUAL: 'agregada',
  HEREDADO_EQUIVALENTE: 'de un equivalente',
  CONSOLIDACION: 'del catálogo maestro',
  SAP: 'de SAP',
};

/** Tarjeta "SAP dice": el vehículo de SAP y un atajo para buscarlo en el catálogo. */
function TarjetaSap({ s, alBuscar }: { s: SugerenciaSap; alBuscar?: () => void }) {
  const anios = s.desde ? (s.hasta && s.hasta !== s.desde ? `${s.desde}–${s.hasta}` : String(s.desde)) : 'sin años';
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-borde bg-superficie p-3 text-sm">
      <div>
        <span className="text-suave">SAP dice: </span>
        <span className="font-medium">{[s.marca, s.modelo].filter(Boolean).join(' ') || 'sin vehículo'}</span>
        <span className="text-suave"> · {anios}</span>
        {s.marca && !s.marca_catalogo && (
          <span className="block text-xs text-suave">
            Esa marca no aparece en AutoCare ni en MercadoExterno con esos años.
          </span>
        )}
      </div>
      {alBuscar && (
        <Boton variante="secundario" onClick={alBuscar}>
          <Search className="size-4" aria-hidden /> Buscar en el catálogo
        </Boton>
      )}
    </div>
  );
}

function Grupo({
  g,
  editable,
  ocupado,
  alConfirmar,
  alQuitar,
}: {
  g: GrupoAplicacion;
  editable: boolean;
  ocupado: boolean;
  alConfirmar: (ids: number[]) => void;
  alQuitar: (ids: number[]) => void;
}) {
  const porConfirmar = g.items.filter((i) => !i.confirmado && i.completa);
  const incompletas = g.items.filter((i) => !i.completa);
  const origenes = [...new Set(g.items.filter((i) => !i.confirmado).map((i) => ORIGEN[i.origen] ?? i.origen))];
  return (
    <li className="flex flex-wrap items-start justify-between gap-2 px-4 py-3">
      <div className="min-w-0">
        <p className="text-sm font-medium">
          {g.titulo} <span className="text-suave tabular-nums">{g.anios}</span>
        </p>
        <p className="text-sm text-suave">{g.detalle}</p>
        <div className="mt-1 flex flex-wrap gap-1.5 text-xs">
          {g.confirmados > 0 && (
            <span className="flex items-center gap-1 text-validado">
              <CircleCheck className="size-3.5" aria-hidden /> {g.confirmados} confirmada{g.confirmados > 1 && 's'}
            </span>
          )}
          {g.sugeridos > 0 && (
            <span className="text-suave">
              {g.sugeridos} sugerida{g.sugeridos > 1 && 's'} ({origenes.join(', ')})
            </span>
          )}
          {incompletas.length > 0 && (
            <span className="text-por-validar">
              Falta {g.detalle.includes('Sin submodelo') ? 'submodelo' : 'motor'}: búscalo en el selector
            </span>
          )}
        </div>
      </div>
      {editable && (
        <div className="flex gap-1">
          {porConfirmar.length > 0 && (
            <Boton
              variante="secundario"
              className="h-8 px-2 text-xs"
              disabled={ocupado}
              onClick={() => alConfirmar(porConfirmar.map((i) => i.id))}
            >
              <Check className="size-4" aria-hidden /> Confirmar
            </Boton>
          )}
          <Boton
            variante="fantasma"
            className="h-8 px-2"
            disabled={ocupado}
            aria-label={`Quitar ${g.titulo} ${g.detalle} ${g.anios}`}
            title="Quitar"
            onClick={() =>
              confirm(`¿Quitar ${g.titulo} ${g.anios} (${g.detalle}) del artículo?`) &&
              alQuitar(g.items.map((i) => i.id))
            }
          >
            <Trash2 className="size-4" aria-hidden />
          </Boton>
        </div>
      )}
    </li>
  );
}

/** Lo que el selector propone agregar: cada año (vehículo base) de cada configuración marcada, sin lo que ya está confirmado. */
export function itemsParaAgregar(
  configuraciones: ConfiguracionAgrupada[],
  marcadas: Set<string>,
  r: RespuestaAplicaciones,
): NuevaAplicacion[] {
  const confirmadas = new Set(
    r.grupos.flatMap((g) =>
      g.items.filter((i) => i.confirmado).map((i) => `${i.base_vehicle_id}-${i.sub_model_id}-${i.engine_config_id}`),
    ),
  );
  return configuraciones
    .filter((c) => marcadas.has(llave(c)))
    .flatMap((c) =>
      c.anios.map((a) => ({
        base_vehicle_id: a.base_vehicle_id,
        sub_model_id: c.sub_model_id,
        engine_config_id: a.engine_config_id,
      })),
    )
    .filter((i) => !confirmadas.has(`${i.base_vehicle_id}-${i.sub_model_id}-${i.engine_config_id}`));
}

const llave = (c: ConfiguracionAgrupada) => `${c.sub_model_id}-${c.motor}`;

interface Busqueda {
  desde: number;
  hasta: number;
  marcaTexto: string;
  modeloId?: number;
}

function busquedaInicial(s?: SugerenciaSap | null): Busqueda {
  const desde = s?.desde ?? ANIO_ACTUAL;
  return {
    desde,
    hasta: Math.min(s?.hasta ?? desde, desde + MAX_ANIOS),
    marcaTexto: s?.marca_catalogo?.nombre ?? '',
    modeloId: s?.marca_catalogo ? s.modelos_candidatos[0]?.id : undefined,
  };
}

/** Selector: años → marca → modelo → configuraciones (submodelo + motor) de AutoCare y MercadoExterno. */
function Selector({
  r,
  inicial,
  ocupado,
  alAgregar,
  alRegistrar,
}: {
  r: RespuestaAplicaciones;
  inicial: Busqueda;
  ocupado: boolean;
  alAgregar: (items: NuevaAplicacion[], alTerminar: () => void) => void;
  alRegistrar: (b: Busqueda) => void;
}) {
  const [b, setB] = useState<Busqueda>(inicial);
  const [marcadas, setMarcadas] = useState<Set<string>>(new Set());
  const aniosValidos = b.desde >= 1900 && b.hasta >= b.desde && b.hasta - b.desde <= MAX_ANIOS;
  const rango = { desde: b.desde, hasta: b.hasta };

  const marcas = useListarMarcas(rango, { query: { enabled: aniosValidos, staleTime: 3_600_000 } });
  const marca = marcas.data?.find((m) => m.nombre.toLowerCase() === b.marcaTexto.trim().toLowerCase());
  const modelos = useListarModelos(
    { marca_id: marca?.id ?? 0, ...rango },
    { query: { enabled: aniosValidos && !!marca, staleTime: 3_600_000 } },
  );
  const modelo = modelos.data?.find((m) => m.id === b.modeloId);
  const configs = useListarConfiguraciones(
    { marca_id: marca?.id ?? 0, modelo_id: modelo?.id ?? 0, ...rango },
    { query: { enabled: aniosValidos && !!marca && !!modelo } },
  );

  // Candidatos de SAP primero en la lista de modelos
  const candidatos = new Set(
    r.sugerencia_sap?.marca_catalogo?.id === marca?.id ? r.sugerencia_sap?.modelos_candidatos.map((m) => m.id) : [],
  );
  const lista = configs.data ?? [];
  const items = itemsParaAgregar(lista, marcadas, r);
  const poner = (x: Partial<Busqueda>) => (setB((v) => ({ ...v, ...x })), setMarcadas(new Set()));
  const alternar = (c: ConfiguracionAgrupada) =>
    setMarcadas((m) => {
      const n = new Set(m);
      if (n.has(llave(c))) n.delete(llave(c));
      else n.add(llave(c));
      return n;
    });

  return (
    <section aria-label="Agregar aplicaciones" className="space-y-3 rounded-lg border border-borde bg-superficie p-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-[6rem_6rem_1fr_1fr]">
        <label className="space-y-1 text-sm">
          <span className="font-medium">Desde</span>
          <input
            type="number"
            inputMode="numeric"
            className={cn(control, 'tabular-nums')}
            value={b.desde || ''}
            onChange={(e) => poner({ desde: Number(e.target.value) })}
          />
        </label>
        <label className="space-y-1 text-sm">
          <span className="font-medium">Hasta</span>
          <input
            type="number"
            inputMode="numeric"
            className={cn(control, 'tabular-nums')}
            value={b.hasta || ''}
            onChange={(e) => poner({ hasta: Number(e.target.value) })}
          />
        </label>
        <label className="col-span-2 space-y-1 text-sm sm:col-span-1">
          <span className="font-medium">Marca</span>
          <input
            list="marcas-vehiculo"
            className={control}
            placeholder={marcas.isLoading ? 'Cargando marcas…' : 'Escribe la marca'}
            value={b.marcaTexto}
            onChange={(e) => poner({ marcaTexto: e.target.value, modeloId: undefined })}
          />
          <datalist id="marcas-vehiculo">
            {marcas.data?.map((m) => (
              <option key={m.id} value={m.nombre} />
            ))}
          </datalist>
        </label>
        <label className="col-span-2 space-y-1 text-sm sm:col-span-1">
          <span className="font-medium">Modelo</span>
          <select
            className={control}
            disabled={!marca}
            value={b.modeloId ?? ''}
            onChange={(e) => poner({ modeloId: e.target.value ? Number(e.target.value) : undefined })}
          >
            <option value="">
              {marca ? (modelos.isLoading ? 'Cargando…' : 'Elige el modelo') : 'Primero la marca'}
            </option>
            {candidatos.size > 0 && (
              <optgroup label="Parecidos a SAP">
                {r.sugerencia_sap?.modelos_candidatos.map((m) => (
                  <option key={`c${m.id}`} value={m.id}>
                    {m.nombre}
                  </option>
                ))}
              </optgroup>
            )}
            <optgroup label="Todos">
              {modelos.data?.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.nombre}
                </option>
              ))}
            </optgroup>
          </select>
        </label>
      </div>
      {!aniosValidos && <p className="text-sm text-rechazado">Revisa los años (máximo {MAX_ANIOS}).</p>}
      {marcas.isError && <Aviso tono="error" titulo={marcas.error.problema.title} />}

      {modelo && (
        <div className="space-y-2">
          {configs.isLoading && <p className="text-sm text-suave">Buscando configuraciones…</p>}
          {configs.data && lista.length === 0 && (
            <p className="text-sm text-suave">No hay configuraciones de {modelo.nombre} entre esos años.</p>
          )}
          {lista.length > 0 && (
            <ul className="divide-y divide-borde rounded-md border border-borde">
              {lista.map((c) => {
                const faltan = faltantes(
                  c.anios.map((a) => a.anio),
                  b.desde,
                  b.hasta,
                );
                return (
                  <li key={llave(c)}>
                    <label className="flex cursor-pointer items-start gap-3 px-3 py-2 hover:bg-superficie-2">
                      <input
                        type="checkbox"
                        className="mt-1 size-4"
                        checked={marcadas.has(llave(c))}
                        onChange={() => alternar(c)}
                      />
                      <span className="min-w-0 flex-1 text-sm">
                        <span className="font-medium">{c.submodelo}</span> · {c.motor}
                        {c.catalogo === 'MERCADO_EXTERNO' && <Insignia className="ml-1.5">MercadoExterno</Insignia>}
                        <span className="block text-xs text-suave tabular-nums">
                          {rangos(c.anios.map((a) => a.anio))}
                          {!c.completa && faltan.length > 0 && (
                            <span className="text-por-validar"> · no existe en {rangos(faltan)}</span>
                          )}
                          {' · '}
                          {[...new Set(c.anios.flatMap((a) => a.regiones))].join(', ')}
                        </span>
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <button type="button" className="text-sm text-suave underline" onClick={() => alRegistrar(b)}>
          ¿No está el vehículo? Regístralo en MercadoExterno
        </button>
        <Boton
          disabled={!items.length || items.length > MAX_ITEMS}
          cargando={ocupado}
          onClick={() => alAgregar(items, () => setMarcadas(new Set()))}
        >
          <Plus className="size-4" aria-hidden />
          {items.length > MAX_ITEMS
            ? `Máximo ${MAX_ITEMS} a la vez`
            : `Agregar${items.length ? ` ${items.length} ${items.length === 1 ? 'año' : 'años'}` : ''}`}
        </Boton>
      </div>
    </section>
  );
}

const COMBUSTIBLES = [
  ['GAS', 'Gasolina'],
  ['DIESEL', 'Diésel'],
  ['HYBRID', 'Híbrido'],
  ['ELECTRIC', 'Eléctrico'],
  ['FLEX', 'Flex'],
  ['LPG', 'Gas LP'],
];

/** Alta de un vehículo que no está en AutoCare (ADR 0014): queda en MercadoExterno y se agrega al artículo. */
function RegistrarVehiculo({
  inicial,
  alCerrar,
  alRegistrado,
}: {
  inicial: Busqueda;
  alCerrar: () => void;
  alRegistrado: (items: NuevaAplicacion[]) => void;
}) {
  const consultas = useQueryClient();
  const registrar = useRegistrarVehiculoExterno();
  const [error, setError] = useState<string>();
  const problema = registrar.error instanceof ProblemaError ? registrar.error.problema : null;

  const enviar = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const d = new FormData(e.currentTarget);
    const t = (k: string) => String(d.get(k) ?? '').trim();
    const litros = t('litros').replace(',', '.');
    if (!litros && !t('designacion')) return setError('Indica los litros o el código del motor.');
    setError(undefined);
    registrar.mutate(
      {
        data: {
          marca: t('marca'),
          modelo: t('modelo'),
          desde: Number(t('desde')),
          hasta: Number(t('hasta')),
          submodelo: t('submodelo') || 'Base',
          litros: litros || null,
          cilindros: t('cilindros') ? Number(t('cilindros')) : null,
          combustible: t('combustible') || null,
          aspiracion: t('aspiracion') || null,
          designacion: t('designacion') || null,
          fuente: t('fuente'),
          regiones: t('regiones')
            ? t('regiones')
                .split(/[\s,]+/)
                .filter(Boolean)
            : null,
        },
      },
      {
        onSuccess: (nuevas) => {
          void consultas.invalidateQueries({ predicate: (q) => String(q.queryKey[0]).startsWith('/api/v1/vehiculos') });
          alRegistrado(
            nuevas.flatMap((c) =>
              c.anios.map((a) => ({
                base_vehicle_id: a.base_vehicle_id,
                sub_model_id: c.sub_model_id,
                engine_config_id: a.engine_config_id,
              })),
            ),
          );
        },
      },
    );
  };

  return (
    <form onSubmit={enviar} className="space-y-3">
      <p className="text-sm text-suave">
        Solo si no existe en AutoCare. Queda en MercadoExterno con la fuente como evidencia y se agrega a este artículo.
      </p>
      <div className="grid grid-cols-2 gap-3">
        <Campo etiqueta="Marca" name="marca" required defaultValue={inicial.marcaTexto} />
        <Campo etiqueta="Modelo" name="modelo" required />
        <Campo etiqueta="Desde" name="desde" type="number" required defaultValue={inicial.desde} />
        <Campo etiqueta="Hasta" name="hasta" type="number" required defaultValue={inicial.hasta} />
        <Campo etiqueta="Submodelo" name="submodelo" placeholder="Base" />
        <Campo etiqueta="Código del motor" name="designacion" placeholder="4G63" />
        <Campo etiqueta="Litros" name="litros" inputMode="decimal" placeholder="2.0" />
        <Campo etiqueta="Cilindros" name="cilindros" type="number" min={1} max={16} />
        <label className="space-y-1.5 text-sm">
          <span className="block font-medium">Combustible</span>
          <select name="combustible" className={control} defaultValue="">
            <option value="">—</option>
            {COMBUSTIBLES.map(([v, n]) => (
              <option key={v} value={v}>
                {n}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1.5 text-sm">
          <span className="block font-medium">Aspiración</span>
          <select name="aspiracion" className={control} defaultValue="">
            <option value="">—</option>
            <option value="Naturally Aspirated">Natural</option>
            <option value="Turbocharged">Turbo</option>
          </select>
        </label>
      </div>
      <Campo
        etiqueta="Regiones"
        name="regiones"
        placeholder="GTM, SLV"
        ayuda="Abreviaturas VCdb, separadas por coma."
      />
      <Campo
        etiqueta="Fuente"
        name="fuente"
        required
        minLength={5}
        placeholder="https://…"
        ayuda="Página o ficha técnica que demuestra que el vehículo existe."
      />
      {(error || problema) && (
        <Aviso tono="error" titulo={error ?? problema?.title ?? ''}>
          {problema?.errors?.[0]?.mensaje ?? problema?.detail}
        </Aviso>
      )}
      <div className="flex justify-end gap-2">
        <Boton variante="fantasma" onClick={alCerrar}>
          Cancelar
        </Boton>
        <Boton type="submit" cargando={registrar.isPending}>
          Registrar y agregar
        </Boton>
      </div>
    </form>
  );
}

/** Pestaña Aplicaciones (propuesta UX §6.4, decisión 4): lo que SAP dice, lo sugerido por confirmar y el selector de vehículos. */
export function Aplicaciones({ itemCode }: { itemCode: string }) {
  const q = useListarAplicaciones(itemCode);
  const agregar = useAgregarAplicaciones();
  const confirmar = useConfirmarAplicaciones();
  const quitar = useQuitarAplicaciones();
  const [elegido, setSelector] = useState<Busqueda | null>(null);
  const [registro, setRegistro] = useState<Busqueda | null>(null);
  const [hecho, setHecho] = useState<string>();
  const r = q.data;

  // Sin aplicaciones y con el vehículo de SAP encontrado, el selector arranca abierto
  const sugerido = useMemo(() => busquedaInicial(r?.sugerencia_sap), [r?.sugerencia_sap]);
  const abrirSolo = !!(r?.editable && r.catalogo_disponible && !r.grupos.length && r.sugerencia_sap?.marca_catalogo);
  const selector = elegido ?? (abrirSolo ? sugerido : null);

  if (q.isError) return <Aviso tono="error" titulo={q.error.problema.title} />;
  if (!r) return <p className="text-sm text-suave">Cargando las aplicaciones…</p>;

  const ocupado = agregar.isPending || confirmar.isPending || quitar.isPending;
  const error = [agregar.error, confirmar.error, quitar.error].find((e) => e instanceof ProblemaError);
  const listo = (texto: string) => ({ onSuccess: () => setHecho(texto) });
  const alAgregar = (items: NuevaAplicacion[], alTerminar?: () => void) => {
    setSelector(selector); // si se abrió solo, queda abierto aunque ya haya aplicaciones
    agregar.mutate(
      { itemCode, data: { version: r.version, items } },
      {
        onSuccess: () => (
          setHecho(`${items.length} ${items.length === 1 ? 'año agregado' : 'años agregados'}.`),
          alTerminar?.()
        ),
      },
    );
  };
  const porConfirmar = r.grupos.flatMap((g) => g.items.filter((i) => !i.confirmado && i.completa).map((i) => i.id));
  const total = r.grupos.reduce((n, g) => n + g.items.length, 0);

  return (
    <div className="space-y-4">
      {!r.editable && (
        <Aviso tono="info" titulo="Solo lectura">
          {r.razon_no_editable}
        </Aviso>
      )}
      {!r.catalogo_disponible && (
        <Aviso tono="info" titulo="Catálogo de vehículos no disponible">
          La API no tiene acceso a AutoCare o MercadoExterno: se ven los IDs, pero no se puede buscar ni agregar.
        </Aviso>
      )}
      {error instanceof ProblemaError && (
        <Aviso tono="error" titulo={error.problema.title}>
          {error.problema.detail}{' '}
          {error.problema.status === 409 && (
            <button type="button" className="underline" onClick={() => void q.refetch()}>
              Recargar
            </button>
          )}
        </Aviso>
      )}
      {hecho && !error && <Aviso tono="exito" titulo={hecho} />}

      {r.sugerencia_sap && (
        <TarjetaSap
          s={r.sugerencia_sap}
          alBuscar={r.editable && r.catalogo_disponible && !selector ? () => setSelector(sugerido) : undefined}
        />
      )}

      {r.editable && porConfirmar.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-borde bg-superficie p-3 text-sm">
          <span className="text-suave">{porConfirmar.length} aplicaciones sugeridas listas para confirmar.</span>
          <Boton
            variante="secundario"
            disabled={ocupado}
            onClick={() =>
              confirmar.mutate(
                { itemCode, data: { version: r.version, ids: porConfirmar } },
                listo('Sugeridas confirmadas.'),
              )
            }
          >
            <Check className="size-4" aria-hidden /> Confirmar todas
          </Boton>
        </div>
      )}

      <section className="rounded-lg border border-borde bg-superficie">
        <h2 className="flex items-center justify-between border-b border-borde px-4 py-2 text-xs font-medium tracking-wide text-suave uppercase">
          <span>Aplicaciones ({total})</span>
          {r.editable && r.catalogo_disponible && !selector && (
            <Boton variante="fantasma" className="h-7 px-2 text-xs normal-case" onClick={() => setSelector(sugerido)}>
              <Plus className="size-4" aria-hidden /> Agregar
            </Boton>
          )}
        </h2>
        {r.grupos.length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-suave">Este artículo aún no tiene aplicaciones.</p>
        ) : (
          <ul className="divide-y divide-borde">
            {r.grupos.map((g) => (
              <Grupo
                key={`${g.titulo}|${g.detalle}`}
                g={g}
                editable={r.editable}
                ocupado={ocupado}
                alConfirmar={(ids) =>
                  confirmar.mutate({ itemCode, data: { version: r.version, ids } }, listo('Aplicaciones confirmadas.'))
                }
                alQuitar={(ids) =>
                  quitar.mutate({ itemCode, data: { version: r.version, ids } }, listo('Aplicación quitada.'))
                }
              />
            ))}
          </ul>
        )}
      </section>

      {r.editable && r.catalogo_disponible && selector && (
        <Selector
          r={r}
          inicial={selector}
          ocupado={agregar.isPending}
          alAgregar={alAgregar}
          alRegistrar={(b) => setRegistro(b)}
        />
      )}

      <Dialogo abierto={!!registro} alCerrar={() => setRegistro(null)} titulo="Registrar vehículo">
        {registro && (
          <RegistrarVehiculo
            inicial={registro}
            alCerrar={() => setRegistro(null)}
            alRegistrado={(items) => (setRegistro(null), alAgregar(items))}
          />
        )}
      </Dialogo>
    </div>
  );
}
