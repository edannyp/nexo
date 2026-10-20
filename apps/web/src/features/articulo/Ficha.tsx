import {
  ProblemaError,
  useGuardarFicha,
  useObtenerFicha,
  type AtributoFicha,
  type Cambio,
  type ValorAtributo,
} from '@nexo/api-client';
import { useBlocker } from '@tanstack/react-router';
import { Check, CircleCheck, Undo2 } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { cn } from '@/shared/cn';
import { momento, numero } from '@/shared/formato';
import { Aviso, Boton } from '@/shared/ui';

import { aMilimetros, aNumero, UNIDADES, type Unidad } from './unidades';

const GRUPOS: Record<string, string> = {
  MEDIDAS: 'Medidas',
  CONSTRUCCION: 'Construcción',
  MATERIALES: 'Materiales',
  CONEXIONES: 'Conexiones',
  INCLUYE: 'Incluye',
  OTROS: 'Otros',
};

/** Lo que el operador escribió o eligió (aún sin guardar). */
interface Borrador {
  texto: string; // para número o texto libre
  unidad: Unidad;
  valid_value_id?: number;
  quitar?: boolean;
}

const opcionTexto = (o: { valor: string; valor_es?: string | null }) =>
  o.valor_es ? `${o.valor} (${o.valor_es})` : o.valor;

/** Texto legible de un valor guardado. */
function mostrar(a: AtributoFicha, v?: ValorAtributo | null): string {
  if (!v) return '';
  if (v.valid_value_id != null) {
    const o = a.opciones.find((x) => x.valid_value_id === v.valid_value_id);
    return o ? opcionTexto(o) : String(v.valid_value_id);
  }
  if (v.valor_num != null)
    return `${numero(v.valor_num).replace(/,/g, '')}${v.uom_code ? ` ${v.uom_code.toLowerCase()}` : ''}`;
  return v.valor_texto ?? '';
}

function borradorDe(v?: ValorAtributo | null): Borrador {
  return {
    texto: v?.valor_num != null ? String(Number(v.valor_num)) : (v?.valor_texto ?? ''),
    unidad: 'mm',
    valid_value_id: v?.valid_value_id ?? undefined,
  };
}

/** Convierte el borrador al valor que espera la API, o un mensaje si no es válido. */
function aCambio(a: AtributoFicha, b: Borrador): Cambio | { error: string } | null {
  if (b.quitar) return null;
  if (a.tipo === 'lista')
    return b.valid_value_id ? { paid: a.paid, valid_value_id: b.valid_value_id } : { error: 'Elige una opción.' };
  if (a.tipo === 'numero') {
    if (a.requiere_uom) {
      const mm = aMilimetros(b.texto, b.unidad);
      return mm === null
        ? { error: 'Escribe una medida, por ejemplo 375 o 37.5 cm.' }
        : { paid: a.paid, valor_num: mm, uom_code: a.uom_defecto ?? 'MM' };
    }
    const n = aNumero(b.texto);
    return n === null ? { error: 'Escribe un número.' } : { paid: a.paid, valor_num: n };
  }
  return b.texto.trim() ? { paid: a.paid, valor_texto: b.texto.trim() } : { error: 'Escribe un valor.' };
}

function Estado({ a }: { a: AtributoFicha }) {
  if (a.confirmado) {
    return (
      <span
        className="flex items-center gap-1 text-xs text-validado"
        title={a.confirmado_en ? momento(a.confirmado_en) : undefined}
      >
        <CircleCheck className="size-3.5" aria-hidden /> {a.confirmado_por ?? 'Confirmado'}
      </span>
    );
  }
  if (a.valor)
    return (
      <span className="text-xs text-suave">Sugerido ({a.origen === 'SAP' ? 'SAP' : a.origen?.toLowerCase()})</span>
    );
  return <span className="text-xs text-suave">Sin dato</span>;
}

function Campo({
  a,
  b,
  editable,
  error,
  alCambiar,
}: {
  a: AtributoFicha;
  b: Borrador;
  editable: boolean;
  error?: string;
  alCambiar: (b: Borrador) => void;
}) {
  const base = cn(
    'h-9 w-full rounded-md border bg-superficie px-2 text-base disabled:bg-superficie-2 disabled:text-suave sm:text-sm',
    error ? 'border-rechazado' : 'border-borde',
  );
  const etiqueta = `${a.etiqueta} (valor en Nexo)`;
  if (a.tipo === 'lista') {
    return (
      <select
        aria-label={etiqueta}
        disabled={!editable}
        value={b.quitar ? '' : (b.valid_value_id ?? '')}
        onChange={(e) =>
          alCambiar({ ...b, quitar: false, valid_value_id: e.target.value ? Number(e.target.value) : undefined })
        }
        className={base}
      >
        <option value="">—</option>
        {a.opciones.map((o) => (
          <option key={o.valid_value_id} value={o.valid_value_id}>
            {opcionTexto(o)}
          </option>
        ))}
      </select>
    );
  }
  if (a.tipo === 'numero' && a.requiere_uom) {
    const mm = aMilimetros(b.texto, b.unidad);
    return (
      <div className="space-y-0.5">
        <div className="flex gap-1">
          <input
            aria-label={etiqueta}
            inputMode="decimal"
            disabled={!editable}
            value={b.quitar ? '' : b.texto}
            onChange={(e) => alCambiar({ ...b, quitar: false, texto: e.target.value })}
            className={cn(base, 'tabular-nums')}
          />
          <select
            aria-label={`Unidad de ${a.etiqueta}`}
            disabled={!editable}
            value={b.unidad}
            onChange={(e) => alCambiar({ ...b, unidad: e.target.value as Unidad })}
            className={cn(base, 'w-20')}
          >
            {UNIDADES.map((u) => (
              <option key={u.codigo} value={u.codigo}>
                {u.nombre}
              </option>
            ))}
          </select>
        </div>
        {mm !== null && (b.unidad !== 'mm' || /[a-z"]/i.test(b.texto)) && (
          <p className="text-xs text-suave">= {mm} mm</p>
        )}
      </div>
    );
  }
  return (
    <>
      <input
        aria-label={etiqueta}
        inputMode={a.tipo === 'numero' ? 'decimal' : undefined}
        list={a.sugerencias.length ? `sug-${a.paid}` : undefined}
        disabled={!editable}
        value={b.quitar ? '' : b.texto}
        onChange={(e) => alCambiar({ ...b, quitar: false, texto: e.target.value })}
        className={cn(base, a.tipo === 'numero' && 'tabular-nums')}
      />
      {a.sugerencias.length > 0 && (
        <datalist id={`sug-${a.paid}`}>
          {a.sugerencias.map((s) => (
            <option key={s} value={s} />
          ))}
        </datalist>
      )}
    </>
  );
}

/** Pestaña Ficha (propuesta UX §6.4): botón Guardar, sugerencias de SAP, campos inteligentes y aviso de cambios sin guardar. */
export function Ficha({
  itemCode,
  alCambiarPendientes,
}: {
  itemCode: string;
  alCambiarPendientes: (n: number) => void;
}) {
  const q = useObtenerFicha(itemCode);
  const guardar = useGuardarFicha();
  const [borradores, setBorradores] = useState<Record<number, Borrador>>({});
  const f = q.data;
  const pendientes = Object.keys(borradores).length;

  useEffect(() => alCambiarPendientes(pendientes), [pendientes, alCambiarPendientes]);
  // Aviso al salir de la pantalla (u otra ruta) con cambios sin guardar
  useBlocker({
    shouldBlockFn: () => pendientes > 0 && !confirm('Tienes cambios sin guardar en la ficha. ¿Salir sin guardar?'),
    enableBeforeUnload: () => pendientes > 0,
  });

  const errores = useMemo(() => {
    const e: Record<number, string> = {};
    if (!f) return e;
    for (const [paid, b] of Object.entries(borradores)) {
      const a = f.atributos.find((x) => x.paid === Number(paid));
      const c = a && aCambio(a, b);
      if (c && 'error' in c) e[Number(paid)] = c.error;
    }
    return e;
  }, [borradores, f]);

  const enviar = () => {
    if (!f || !pendientes || Object.keys(errores).length) return;
    const cambios: Cambio[] = [];
    const quitar: number[] = [];
    for (const [paid, b] of Object.entries(borradores)) {
      const a = f.atributos.find((x) => x.paid === Number(paid));
      if (!a) continue;
      const c = aCambio(a, b);
      if (c === null) quitar.push(a.paid);
      else if (!('error' in c)) cambios.push(c);
    }
    guardar.mutate({ itemCode, data: { version: f.version, cambios, quitar } }, { onSuccess: () => setBorradores({}) });
  };

  // Ctrl+S guarda
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        enviar();
      }
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
  });

  if (q.isError) return <Aviso tono="error" titulo={q.error.problema.title} />;
  if (!f) return <p className="text-sm text-suave">Cargando la ficha…</p>;

  const poner = (paid: number, b: Borrador) => setBorradores((x) => ({ ...x, [paid]: b }));
  const deshacer = (paid: number) =>
    setBorradores((x) => Object.fromEntries(Object.entries(x).filter(([k]) => Number(k) !== paid)));
  const aceptar = (a: AtributoFicha) => a.valor && poner(a.paid, borradorDe(a.valor));
  const sugeridos = f.atributos.filter((a) => a.valor && !a.confirmado && !borradores[a.paid]);
  const grupos = [...new Set(f.atributos.map((a) => a.grupo))];
  const problema = guardar.error instanceof ProblemaError ? guardar.error.problema : null;

  return (
    <div className="space-y-4 pb-20">
      {!f.editable && (
        <Aviso tono="info" titulo="Solo lectura">
          {f.razon_no_editable}
        </Aviso>
      )}
      {problema && (
        <Aviso tono="error" titulo={problema.title}>
          {problema.detail}{' '}
          {problema.status === 409 && (
            <button type="button" className="underline" onClick={() => (setBorradores({}), void q.refetch())}>
              Recargar
            </button>
          )}
        </Aviso>
      )}

      {f.editable && sugeridos.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-borde bg-superficie p-3 text-sm">
          <span className="text-suave">{sugeridos.length} valores sugeridos desde SAP sin confirmar.</span>
          <Boton variante="secundario" onClick={() => sugeridos.forEach(aceptar)}>
            <Check className="size-4" aria-hidden /> Aceptar todo lo sugerido
          </Boton>
        </div>
      )}

      {grupos.map((g) => (
        <section key={g} className="rounded-lg border border-borde bg-superficie">
          <h2 className="border-b border-borde px-4 py-2 text-xs font-medium tracking-wide text-suave uppercase">
            {GRUPOS[g] ?? g}
          </h2>
          <div className="hidden grid-cols-[minmax(9rem,1.2fr)_minmax(6rem,0.8fr)_minmax(12rem,1.6fr)_minmax(8rem,1fr)_auto] gap-3 px-4 pt-2 text-xs text-suave md:grid">
            <span>Atributo</span>
            <span>SAP</span>
            <span>En Nexo</span>
            <span>Estado</span>
            <span className="w-20" />
          </div>
          <ul className="divide-y divide-borde">
            {f.atributos
              .filter((a) => a.grupo === g)
              .map((a) => {
                const b = borradores[a.paid] ?? borradorDe(a.valor);
                const sucio = !!borradores[a.paid];
                return (
                  <li
                    key={a.paid}
                    className={cn(
                      'grid gap-2 px-4 py-3 md:grid-cols-[minmax(9rem,1.2fr)_minmax(6rem,0.8fr)_minmax(12rem,1.6fr)_minmax(8rem,1fr)_auto] md:items-center md:gap-3',
                      sucio && 'bg-por-validar/5',
                    )}
                  >
                    <div>
                      <span className="text-sm font-medium">
                        {a.etiqueta}
                        {a.obligatorio && (
                          <span className="text-rechazado" title="Obligatorio">
                            {' '}
                            *
                          </span>
                        )}
                      </span>
                      <span className="block text-xs text-suave">{a.nombre_pies}</span>
                    </div>
                    <div className="text-sm text-suave">
                      <span className="md:hidden">SAP: </span>
                      {a.valor_sap ?? '—'}
                    </div>
                    <div>
                      <Campo
                        a={a}
                        b={b}
                        editable={f.editable}
                        error={errores[a.paid]}
                        alCambiar={(nb) => poner(a.paid, nb)}
                      />
                      {errores[a.paid] && <p className="mt-0.5 text-xs text-rechazado">{errores[a.paid]}</p>}
                      {!sucio && a.valor && !a.confirmado && (
                        <p className="mt-0.5 text-xs text-suave">Sugerido: {mostrar(a, a.valor)}</p>
                      )}
                    </div>
                    <div>
                      {sucio ? <span className="text-xs text-por-validar">Sin guardar</span> : <Estado a={a} />}
                    </div>
                    <div className="flex w-20 gap-1">
                      {f.editable && !sucio && a.valor && !a.confirmado && (
                        <Boton
                          variante="secundario"
                          className="h-8 px-2"
                          onClick={() => aceptar(a)}
                          aria-label={`Aceptar ${a.etiqueta}`}
                          title="Aceptar lo sugerido"
                        >
                          <Check className="size-4" aria-hidden />
                        </Boton>
                      )}
                      {sucio && (
                        <Boton
                          variante="fantasma"
                          className="h-8 px-2"
                          onClick={() => deshacer(a.paid)}
                          aria-label={`Deshacer ${a.etiqueta}`}
                          title="Deshacer"
                        >
                          <Undo2 className="size-4" aria-hidden />
                        </Boton>
                      )}
                      {f.editable && !sucio && a.valor && (
                        <Boton
                          variante="fantasma"
                          className="h-8 px-2 text-xs"
                          onClick={() => poner(a.paid, { ...b, quitar: true })}
                          title="Dejar sin valor"
                        >
                          Quitar
                        </Boton>
                      )}
                    </div>
                  </li>
                );
              })}
          </ul>
        </section>
      ))}

      {/* Barra de guardado: fija abajo mientras haya cambios */}
      {f.editable && pendientes > 0 && (
        <div className="fixed inset-x-0 bottom-14 z-20 border-t border-borde bg-superficie/95 px-4 py-3 backdrop-blur lg:bottom-0 lg:left-56">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-3">
            <span className="text-sm">
              <span className="font-medium">{pendientes}</span>{' '}
              {pendientes === 1 ? 'cambio sin guardar' : 'cambios sin guardar'}
              {Object.keys(errores).length > 0 && (
                <span className="text-rechazado"> · corrige los campos marcados</span>
              )}
            </span>
            <div className="flex gap-2">
              <Boton variante="fantasma" onClick={() => setBorradores({})}>
                Descartar
              </Boton>
              <Boton onClick={enviar} cargando={guardar.isPending} disabled={Object.keys(errores).length > 0}>
                Guardar{' '}
                <kbd className="ml-1 hidden rounded border border-current/40 px-1 text-xs sm:inline">Ctrl S</kbd>
              </Boton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
