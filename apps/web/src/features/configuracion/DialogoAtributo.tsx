import {
  useAgregarOpcion,
  useBorrarCampoPropio,
  useConfigurarAtributo,
  useHomologar,
  useListarColumnasSap,
  useQuitarOpcion,
  useRenombrarOpcion,
  useTraducirValor,
  useValoresSap,
  type AtributoConfig,
  type ConversionSap,
  type GrupoAtributo,
} from '@nexo/api-client';
import { Plus, Trash2 } from 'lucide-react';
import { useState, type FormEvent } from 'react';

import { Aviso, Boton, Dialogo, Insignia } from '@/shared/ui';

import { CONVERSIONES, GRUPOS, etiquetaDe, nombreTipo, textoError } from './comun';

const seccion = 'space-y-3 border-t border-borde pt-4';
const tituloSeccion = 'text-xs font-medium tracking-wide text-suave uppercase';
const control = 'h-9 w-full rounded-md border border-borde bg-superficie px-2 text-base sm:text-sm';

/** Lo general y la precarga desde SAP: se guardan juntos. */
function General({ pt, a, alCambiar }: { pt: number; a: AtributoConfig; alCambiar: () => void }) {
  const [etiqueta, setEtiqueta] = useState(a.etiqueta ?? '');
  const [grupo, setGrupo] = useState<GrupoAtributo>(a.grupo);
  const [orden, setOrden] = useState(a.orden == null ? '' : String(a.orden));
  const [obligatorio, setObligatorio] = useState(a.obligatorio);
  const [columna, setColumna] = useState(a.columna_sap ?? '');
  const [conversion, setConversion] = useState<ConversionSap | ''>(a.conversion ?? '');
  const [parte, setParte] = useState(a.parte ?? 1);
  const [hecho, setHecho] = useState(false);
  const columnas = useListarColumnasSap();
  const guardar = useConfigurarAtributo();
  const conversiones = CONVERSIONES.filter((c) => c.tipo === a.tipo);

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    setHecho(false);
    guardar.mutate(
      {
        partTerminologyId: pt,
        paid: a.paid,
        data: {
          etiqueta: a.propio ? etiqueta || a.nombre : etiqueta,
          grupo,
          orden: orden === '' ? null : Number(orden),
          obligatorio: a.habilitado && obligatorio,
          columna_sap: columna || null,
          ...(columna
            ? { conversion: conversion || null, parte: conversion === 'PARTE_DE_MEDIDA' ? parte : null }
            : {}),
        },
      },
      { onSuccess: () => (setHecho(true), alCambiar()) },
    );
  };

  return (
    <form onSubmit={enviar} className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_9rem_5rem]">
        <label className="space-y-1">
          <span className="text-sm font-medium">Nombre en la ficha</span>
          <input
            value={etiqueta}
            onChange={(e) => setEtiqueta(e.target.value)}
            maxLength={60}
            placeholder={a.nombre}
            className={control}
          />
        </label>
        <label className="space-y-1">
          <span className="text-sm font-medium">Grupo</span>
          <select value={grupo} onChange={(e) => setGrupo(e.target.value as GrupoAtributo)} className={control}>
            {GRUPOS.map((g) => (
              <option key={g.valor} value={g.valor}>
                {g.nombre}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-sm font-medium">Orden</span>
          <input
            type="number"
            min={0}
            max={999}
            value={orden}
            onChange={(e) => setOrden(e.target.value)}
            className={control}
          />
        </label>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          className="size-4"
          disabled={!a.habilitado}
          checked={a.habilitado && obligatorio}
          onChange={(e) => setObligatorio(e.target.checked)}
        />
        Obligatorio para enviar a revisión
        {!a.habilitado && <span className="text-xs text-suave">(primero agrégalo a la ficha)</span>}
      </label>

      <div className={seccion}>
        <h3 className={tituloSeccion}>Precarga desde SAP</h3>
        <p className="text-xs text-suave">
          El valor de SAP se propone como sugerencia en la ficha; el operador lo confirma o lo corrige.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-1">
            <span className="text-sm font-medium">Columna de SAP</span>
            <select
              value={columna}
              onChange={(e) => {
                setColumna(e.target.value);
                if (e.target.value && !conversion && conversiones.length === 1) setConversion(conversiones[0]!.valor);
              }}
              className={control}
            >
              <option value="">Sin precarga</option>
              {columnas.data?.map((c) => (
                <option key={c.columna} value={c.columna}>
                  {c.columna}
                  {c.campo_sap ? ` (${c.campo_sap})` : ''}
                </option>
              ))}
            </select>
          </label>
          {columna && (
            <label className="space-y-1">
              <span className="text-sm font-medium">Cómo se convierte</span>
              <select
                value={conversion}
                onChange={(e) => setConversion(e.target.value as ConversionSap)}
                className={control}
                required
              >
                <option value="">Elige…</option>
                {conversiones.map((c) => (
                  <option key={c.valor} value={c.valor}>
                    {c.nombre}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
        {columna && conversion === 'PARTE_DE_MEDIDA' && (
          <label className="flex items-center gap-2 text-sm">
            Toma
            <select
              value={parte}
              onChange={(e) => setParte(Number(e.target.value))}
              className="h-9 rounded-md border border-borde bg-superficie px-2"
            >
              <option value={1}>lo de antes del «*»</option>
              <option value={2}>lo de después del «*»</option>
            </select>
          </label>
        )}
      </div>

      {guardar.error && <Aviso tono="error" titulo={textoError(guardar.error) ?? ''} />}
      {hecho && !guardar.error && <Aviso tono="exito" titulo="Guardado." />}
      <Boton type="submit" cargando={guardar.isPending}>
        Guardar
      </Boton>
    </form>
  );
}

/** Opciones: las de AutoCare se traducen; las de un campo propio se agregan, renombran o quitan. */
function Opciones({ pt, a, alCambiar }: { pt: number; a: AtributoConfig; alCambiar: () => void }) {
  const [nueva, setNueva] = useState('');
  const traducir = useTraducirValor();
  const agregar = useAgregarOpcion();
  const renombrar = useRenombrarOpcion();
  const quitar = useQuitarOpcion();
  const error = [traducir.error, agregar.error, renombrar.error, quitar.error].find(Boolean);
  const listo = { onSuccess: alCambiar };

  return (
    <div className={seccion}>
      <h3 className={tituloSeccion}>Opciones ({a.opciones.length})</h3>
      {!a.propio && (
        <p className="text-xs text-suave">Las opciones son de AutoCare: aquí solo se traducen al español.</p>
      )}
      <ul className="space-y-1.5">
        {a.opciones.map((o) => (
          <li key={o.valid_value_id} className="flex items-center gap-2 text-sm">
            {a.propio ? (
              <input
                aria-label={`Opción ${o.valor}`}
                defaultValue={o.valor}
                maxLength={60}
                onBlur={(e) => {
                  const v = e.target.value.trim();
                  if (v && v !== o.valor)
                    renombrar.mutate(
                      { partTerminologyId: pt, paid: a.paid, validValueId: o.valid_value_id, data: { valor: v } },
                      listo,
                    );
                }}
                className={control}
              />
            ) : (
              <>
                <span className="w-2/5 min-w-0 truncate" title={o.valor}>
                  {o.valor}
                  {o.obsoleta && <span className="text-xs text-suave"> (obsoleta)</span>}
                </span>
                <input
                  aria-label={`Traducción de ${o.valor}`}
                  defaultValue={o.valor_es ?? ''}
                  placeholder="Traducción"
                  maxLength={80}
                  onBlur={(e) => {
                    const v = e.target.value.trim();
                    if (v !== (o.valor_es ?? ''))
                      traducir.mutate({ validValueId: o.valid_value_id, data: { valor_es: v || null } }, listo);
                  }}
                  className={control}
                />
              </>
            )}
            <span
              className="w-16 shrink-0 text-right text-xs text-suave tabular-nums"
              title="Artículos con esta opción"
            >
              {o.en_uso} art.
            </span>
            {a.propio && (
              <Boton
                variante="fantasma"
                className="h-8 px-2"
                disabled={o.en_uso > 0 || a.opciones.length === 1 || quitar.isPending}
                title={o.en_uso > 0 ? 'Está en uso: no se puede quitar' : 'Quitar opción'}
                aria-label={`Quitar ${o.valor}`}
                onClick={() =>
                  quitar.mutate({ partTerminologyId: pt, paid: a.paid, validValueId: o.valid_value_id }, listo)
                }
              >
                <Trash2 className="size-4" aria-hidden />
              </Boton>
            )}
          </li>
        ))}
      </ul>
      {a.propio && (
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (nueva.trim())
              agregar.mutate(
                { partTerminologyId: pt, paid: a.paid, data: { valor: nueva.trim() } },
                { onSuccess: () => (setNueva(''), alCambiar()) },
              );
          }}
        >
          <input
            aria-label="Nueva opción"
            value={nueva}
            onChange={(e) => setNueva(e.target.value)}
            maxLength={60}
            placeholder="Nueva opción"
            className={control}
          />
          <Boton type="submit" variante="secundario" className="h-9" cargando={agregar.isPending}>
            <Plus className="size-4" aria-hidden /> Agregar
          </Boton>
        </form>
      )}
      {error && <Aviso tono="error" titulo={textoError(error) ?? ''} />}
    </div>
  );
}

/** Homologación: qué valor de SAP equivale a qué opción. Muestra lo que trae SAP en la columna de precarga. */
function Homologacion({ pt, a, alCambiar }: { pt: number; a: AtributoConfig; alCambiar: () => void }) {
  const sap = useValoresSap(pt, a.paid, { query: { enabled: !!a.columna_sap } });
  const actual = new Map(a.opciones.flatMap((o) => o.homologados.map((h) => [h, o.valid_value_id] as const)));
  const [cambios, setCambios] = useState<Record<string, number | null>>({});
  const [manual, setManual] = useState('');
  const homologar = useHomologar();
  const valores = [...new Set([...(sap.data ?? []).map((v) => v.valor), ...actual.keys(), ...Object.keys(cambios)])];
  const articulos = new Map((sap.data ?? []).map((v) => [v.valor, v.articulos]));
  const elegido = (v: string) => (v in cambios ? cambios[v] : (actual.get(v) ?? null));
  const sinHomologar = valores.filter((v) => elegido(v) == null && articulos.has(v)).length;

  const guardar = () =>
    homologar.mutate(
      {
        partTerminologyId: pt,
        paid: a.paid,
        data: valores.flatMap((v) => {
          const id = elegido(v);
          return id == null ? [] : [{ valor_sap: v, valid_value_id: id }];
        }),
      },
      { onSuccess: () => (setCambios({}), alCambiar()) },
    );

  return (
    <div className={seccion}>
      <h3 className={tituloSeccion}>Homologación SAP → opción</h3>
      <p className="text-xs text-suave">
        Qué valor de SAP equivale a cada opción, para precargarlo. Vale para todos los tipos de parte con este atributo.
        {!a.columna_sap && ' Elige arriba una columna de SAP para ver los valores que trae.'}
      </p>
      {sinHomologar > 0 && (
        <Insignia className="border-por-validar/50 text-por-validar">
          {sinHomologar} valores de SAP sin homologar
        </Insignia>
      )}
      <ul className="max-h-72 space-y-1.5 overflow-y-auto">
        {valores.map((v) => (
          <li key={v} className="flex items-center gap-2 text-sm">
            <span className="w-2/5 min-w-0 truncate font-mono text-xs" title={v}>
              {v}
            </span>
            <span className="w-16 shrink-0 text-xs text-suave tabular-nums">
              {articulos.has(v) ? `${articulos.get(v)} art.` : ''}
            </span>
            <select
              aria-label={`Opción para ${v}`}
              value={elegido(v) ?? ''}
              onChange={(e) => setCambios((c) => ({ ...c, [v]: e.target.value ? Number(e.target.value) : null }))}
              className={control}
            >
              <option value="">Sin homologar</option>
              {a.opciones.map((o) => (
                <option key={o.valid_value_id} value={o.valid_value_id}>
                  {o.valor_es ? `${o.valor} (${o.valor_es})` : o.valor}
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const v = manual.trim().replace(/\s+/g, ' ').toUpperCase();
          if (v) setCambios((c) => ({ ...c, [v]: c[v] ?? null }));
          setManual('');
        }}
      >
        <input
          aria-label="Otro valor de SAP"
          value={manual}
          onChange={(e) => setManual(e.target.value)}
          maxLength={80}
          placeholder="Otro valor de SAP"
          className={control}
        />
        <Boton type="submit" variante="secundario" className="h-9">
          <Plus className="size-4" aria-hidden /> Agregar
        </Boton>
      </form>
      {homologar.error && <Aviso tono="error" titulo={textoError(homologar.error) ?? ''} />}
      <Boton
        variante="secundario"
        cargando={homologar.isPending}
        disabled={Object.keys(cambios).length === 0}
        onClick={guardar}
      >
        Guardar homologación
      </Boton>
    </div>
  );
}

/** Configurar un atributo: general, precarga, opciones, homologación y (en los propios) borrarlo. */
export function DialogoAtributo({
  pt,
  a,
  alCerrar,
  alCambiar,
}: {
  pt: number;
  a: AtributoConfig | null;
  alCerrar: () => void;
  alCambiar: () => void;
}) {
  const borrar = useBorrarCampoPropio();
  return (
    <Dialogo abierto={!!a} alCerrar={alCerrar} titulo={a ? etiquetaDe(a) : ''}>
      {a && (
        <div className="space-y-4">
          <p className="flex flex-wrap items-center gap-2 text-xs text-suave">
            <Insignia>{nombreTipo(a)}</Insignia>
            {a.propio ? (
              <Insignia className="border-primario/50 text-primario">Campo propio</Insignia>
            ) : (
              <span>
                AutoCare: {a.nombre} (PAID {a.paid})
              </span>
            )}
            <span>{a.en_uso} artículos con valor</span>
          </p>
          {a.estado === 'PROPUESTO' && (
            <Aviso tono="info" titulo={`Propuesto por ${a.solicitado_por ?? '—'}: aún no es oficial`}>
              {a.motivo_solicitud && <>«{a.motivo_solicitud}». </>}Ajusta aquí lo que haga falta y apruébalo o recházalo
              en la pestaña Solicitudes.
            </Aviso>
          )}
          {a.estado === 'RECHAZADO' && (
            <Aviso tono="info" titulo={`Rechazado por ${a.revisado_por ?? '—'}`}>
              {a.motivo_rechazo} Para usarlo, reconsidéralo en la pestaña Solicitudes.
            </Aviso>
          )}
          {a.obsoleto && (
            <Aviso tono="info" titulo="AutoCare ya no usa este atributo">
              Los artículos que ya lo tienen lo conservan, pero no se puede asignar de nuevo.
            </Aviso>
          )}
          <General pt={pt} a={a} alCambiar={alCambiar} />
          {a.tipo === 'LISTA' && <Opciones pt={pt} a={a} alCambiar={alCambiar} />}
          {a.tipo === 'LISTA' && <Homologacion key={a.columna_sap ?? ''} pt={pt} a={a} alCambiar={alCambiar} />}
          {a.propio && (
            <div className={seccion}>
              {a.en_uso > 0 ? (
                <p className="text-xs text-suave">
                  Está en uso: para dejar de usarlo, quítalo de la ficha (los valores capturados se conservan).
                </p>
              ) : (
                <Boton
                  variante="peligro"
                  cargando={borrar.isPending}
                  onClick={() =>
                    confirm(`¿Borrar el campo «${etiquetaDe(a)}»? Ningún artículo lo usa.`) &&
                    borrar.mutate(
                      { partTerminologyId: pt, paid: a.paid },
                      { onSuccess: () => (alCerrar(), alCambiar()) },
                    )
                  }
                >
                  <Trash2 className="size-4" aria-hidden /> Borrar campo
                </Boton>
              )}
              {borrar.error && <Aviso tono="error" titulo={textoError(borrar.error) ?? ''} />}
            </div>
          )}
        </div>
      )}
    </Dialogo>
  );
}
