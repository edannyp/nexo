import {
  getObtenerArticuloQueryKey,
  ProblemaError,
  useHistorialArticulo,
  useObtenerArticulo,
  useRenovarReserva,
  useReservarArticulo,
  useSoltarReserva,
  useTomarSiguiente,
  useTransicionar,
  type AccionEstado,
  type ArticuloDetalle,
  type Bandeja,
} from '@nexo/api-client';
import { useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { ArrowLeft, Lock, LockOpen, TriangleAlert } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';

import { useFiltro } from '@/app/contexto-filtro';
import { rutaSeccion } from '@/app/navegacion';
import { cn } from '@/shared/cn';
import { ESTADOS, EtiquetaEstado } from '@/shared/estados';
import { momento, porcentaje } from '@/shared/formato';
import { Tendencia } from '@/shared/graficos';
import { Aviso, Boton, Dialogo } from '@/shared/ui';

import { Aplicaciones } from './Aplicaciones';
import { Emparejamiento } from './Emparejamiento';
import { Equivalencia } from './Equivalencia';
import { Ficha } from './Ficha';
import { FotosDelArticulo } from '@/features/fotos/FotosDelArticulo';

const LATIDO_MS = 5 * 60_000;
const PESTANAS = [
  { id: 'ficha', etiqueta: 'Ficha' },
  { id: 'aplicaciones', etiqueta: 'Aplicaciones' },
  { id: 'emparejamiento', etiqueta: 'Emparejamiento y diagramas' },
  { id: 'equivalencia', etiqueta: 'Equivalencia', soloFabricado: true },
  { id: 'fotos', etiqueta: 'Fotos' },
  { id: 'sap', etiqueta: 'Datos SAP' },
  { id: 'historial', etiqueta: 'Historial' },
] as const;
type Pestana = (typeof PESTANAS)[number]['id'];

const PLANTILLAS: Record<string, string[]> = {
  RECHAZADO: [
    'Años no coinciden',
    'Falta o sobra una aplicación',
    'Medidas incorrectas',
    'Emparejamiento incorrecto',
    'Atributo mal confirmado',
  ],
  PENDIENTE: ['Corrección solicitada', 'Verificación con hallazgo', 'Cambio en el catálogo'],
};

/** Cuenta regresiva de la reserva (mm:ss), actualizada cada segundo. */
function useRestante(hasta?: string | null): number | null {
  const [ahora, setAhora] = useState(() => Date.now());
  useEffect(() => {
    if (!hasta) return;
    const t = setInterval(() => setAhora(Date.now()), 1000);
    return () => clearInterval(t);
  }, [hasta]);
  return hasta ? Math.max(0, new Date(hasta).getTime() - ahora) : null;
}

const mmss = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, '0')}`;

function DialogoMotivo({
  accion,
  alCerrar,
  alConfirmar,
  enviando,
  error,
}: {
  accion: AccionEstado | null;
  alCerrar: () => void;
  alConfirmar: (motivo: string) => void;
  enviando: boolean;
  error?: string;
}) {
  const [motivo, setMotivo] = useState('');
  const enviar = (e: FormEvent) => {
    e.preventDefault();
    if (motivo.trim()) alConfirmar(motivo.trim());
  };
  return (
    <Dialogo abierto={!!accion} alCerrar={alCerrar} titulo={accion ? `${accion.etiqueta}: motivo` : ''}>
      <form onSubmit={enviar} className="space-y-3">
        <div className="flex flex-wrap gap-1.5">
          {(accion ? (PLANTILLAS[accion.destino] ?? []) : []).map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setMotivo(p)}
              className="rounded-full border border-borde px-2.5 py-1 text-xs hover:bg-superficie-2"
            >
              {p}
            </button>
          ))}
        </div>
        <label className="block space-y-1.5">
          <span className="text-sm font-medium">Motivo (lo verá el operador)</span>
          <textarea
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            rows={3}
            maxLength={500}
            required
            autoFocus
            className="w-full rounded-md border border-borde bg-superficie p-2 text-base sm:text-sm"
          />
        </label>
        {error && <p className="text-sm text-rechazado">{error}</p>}
        <Boton
          type="submit"
          variante={accion?.destino === 'RECHAZADO' ? 'peligro' : 'primario'}
          className="w-full"
          cargando={enviando}
          disabled={!motivo.trim()}
        >
          {accion?.etiqueta}
        </Boton>
      </form>
    </Dialogo>
  );
}

function DatosSap({ a }: { a: ArticuloDetalle }) {
  const identificacion: [string, string | null | undefined][] = [
    ['Número de parte (proveedor)', a.numero_parte_proveedor],
    ['Código anterior', a.codigo_anterior?.join(', ')],
    ['Código equivalente', a.codigo_equivalente],
  ];
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="rounded-lg border border-borde bg-superficie p-4">
        <h2 className="mb-2 text-sm font-medium text-suave">Datos de SAP (solo lectura)</h2>
        <dl className="grid grid-cols-[minmax(8rem,auto)_1fr] gap-x-4 gap-y-1.5 text-sm">
          {Object.entries(a.datos_sap).map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-suave">{k}</dt>
              <dd className="tabular-nums">{typeof v === 'boolean' ? (v ? 'Sí' : 'No') : String(v)}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-3 text-xs text-suave">
          SAP no se modifica desde Nexo. Si un dato está mal, se corrige en SAP.
        </p>
      </section>
      <div className="space-y-4">
        <section className="rounded-lg border border-borde bg-superficie p-4">
          <h2 className="mb-2 text-sm font-medium text-suave">Identificación</h2>
          <dl className="grid grid-cols-[minmax(8rem,auto)_1fr] gap-x-4 gap-y-1.5 text-sm">
            {identificacion.map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="text-suave">{k}</dt>
                <dd>{v || '—'}</dd>
              </div>
            ))}
          </dl>
        </section>
        {a.hallazgos.length > 0 && (
          <section className="rounded-lg border border-borde bg-superficie p-4">
            <h2 className="mb-2 flex items-center gap-2 text-sm font-medium text-suave">
              <TriangleAlert className="size-4 text-rechazado" aria-hidden /> Hallazgos para corregir en SAP
            </h2>
            <ul className="space-y-1 text-sm">
              {a.hallazgos.map((h) => (
                <li key={`${h.tipo}-${h.campo_sap}`}>
                  {h.campo_sap}: <code className="rounded bg-superficie-2 px-1">{h.valor ?? '(vacío)'}</code>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}

function Historial({ itemCode }: { itemCode: string }) {
  const q = useHistorialArticulo(itemCode);
  return (
    <section className="rounded-lg border border-borde bg-superficie p-4">
      <h2 className="mb-3 text-sm font-medium text-suave">Historial</h2>
      <ol className="space-y-3">
        {q.data?.map((e) => (
          <li key={e.id} className="border-l-2 border-borde pl-3 text-sm">
            <p>
              {e.tipo === 'TRANSICION' && e.estado_destino ? (
                <>
                  {e.estado_origen && <span className="text-suave">{ESTADOS[e.estado_origen].etiqueta} → </span>}
                  <EtiquetaEstado estado={e.estado_destino} />
                </>
              ) : (
                <span className="font-medium">{e.tipo.replaceAll('_', ' ').toLowerCase()}</span>
              )}
            </p>
            <p className="text-xs text-suave">
              {e.actor} · {momento(e.creado_en)}
            </p>
            {e.motivo && <p className="mt-0.5">«{e.motivo}»</p>}
          </li>
        ))}
      </ol>
    </section>
  );
}

/** Espacio de trabajo del artículo (propuesta UX §6.4). En este paso: encabezado, flujo, datos SAP e historial. */
export function Articulo() {
  const { itemCode } = useParams({ strict: false }) as { itemCode: string };
  const {
    bandeja,
    pestana: pestanaUrl,
    parte: parteUrl,
  } = useSearch({ strict: false }) as {
    bandeja?: Bandeja;
    pestana?: string;
    parte?: number;
  };
  const { filtro } = useFiltro();
  const navegar = useNavigate();
  const consultas = useQueryClient();
  const q = useObtenerArticulo(itemCode);
  const a = q.data;
  const clave = getObtenerArticuloQueryKey(itemCode);
  const fijar = (d: ArticuloDetalle) => consultas.setQueryData(clave, d);

  const [pestana, setPestanaDirecta] = useState<Pestana>(
    PESTANAS.some((p) => p.id === pestanaUrl) ? (pestanaUrl as Pestana) : 'ficha',
  );
  const [pendientesFicha, setPendientesFicha] = useState(0);
  // Cambiar de pestaña desmonta la ficha: si hay cambios sin guardar, se pregunta antes
  const setPestana = (p: Pestana) => {
    if (
      p !== pestana &&
      pestana === 'ficha' &&
      pendientesFicha > 0 &&
      !confirm('Tienes cambios sin guardar en la ficha. ¿Cambiar de pestaña sin guardar?')
    )
      return;
    setPestanaDirecta(p);
  };
  const [motivoPara, setMotivoPara] = useState<AccionEstado | null>(null);
  const [aviso, setAviso] = useState<{ tono: 'error' | 'exito' | 'info'; titulo: string; detalle?: string } | null>(
    null,
  );

  const transicionar = useTransicionar();
  const renovar = useRenovarReserva();
  const soltar = useSoltarReserva();
  const reservar = useReservarArticulo();
  const siguiente = useTomarSiguiente();
  const restante = useRestante(a?.reserva?.mia ? a.reserva.hasta : null);

  // Latido: renueva la reserva propia cada 5 minutos mientras la pantalla está abierta
  useEffect(() => {
    if (!a?.reserva?.mia) return;
    const t = setInterval(
      () =>
        renovar.mutate(
          { itemCode },
          {
            onSuccess: (r) => fijar({ ...a, reserva: a.reserva && { ...a.reserva, hasta: r.hasta } }),
            onError: () => {
              setAviso({
                tono: 'error',
                titulo: 'Perdiste la reserva',
                detalle: 'Otro usuario puede tomar este artículo. Vuelve a tomarlo para seguir.',
              });
              void q.refetch();
            },
          },
        ),
      LATIDO_MS,
    );
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [a?.reserva?.mia, itemCode]);

  const tomarSiguiente = () => {
    if (!bandeja) return void navegar({ to: '/' });
    siguiente.mutate(
      { bandeja, params: filtro },
      {
        onSuccess: (r) =>
          r.articulo
            ? void navegar({
                to: '/articulos/$itemCode',
                params: { itemCode: r.articulo.item_code },
                search: (p) => ({ ...p, bandeja }),
              })
            : void navegar({ to: rutaSeccion(bandeja === 'supervisor' ? '/validar' : '/trabajar') }),
      },
    );
  };

  const ejecutar = (accion: AccionEstado, motivo?: string) => {
    if (!a) return;
    transicionar.mutate(
      { itemCode, data: { destino: accion.destino, motivo, version: a.version } },
      {
        onSuccess: (d) => {
          setMotivoPara(null);
          fijar(d);
          setAviso({
            tono: 'exito',
            titulo: `${accion.etiqueta}: listo`,
            detalle: `${d.item_code} quedó en «${ESTADOS[d.estado].etiqueta}».`,
          });
          if (bandeja) tomarSiguiente(); // seguir trabajando
        },
        onError: (e) => {
          if (e instanceof ProblemaError) {
            setAviso({ tono: 'error', titulo: e.problema.title, detalle: e.problema.detail });
            if (e.problema.status === 409) void q.refetch();
          }
        },
      },
    );
  };

  // Ctrl+Enter: enviar a revisión (si se puede)
  useEffect(() => {
    const tecla = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        const enviar = a?.acciones.find((x) => x.destino === 'POR_VALIDAR' && x.habilitada);
        if (enviar) {
          e.preventDefault();
          ejecutar(enviar);
        }
      }
    };
    window.addEventListener('keydown', tecla);
    return () => window.removeEventListener('keydown', tecla);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [a]);

  if (q.isError) {
    return (
      <Aviso tono="error" titulo={q.error.problema.title}>
        {q.error.problema.detail}
      </Aviso>
    );
  }
  if (!a) return <p className="text-sm text-suave">Cargando…</p>;

  const mia = a.reserva?.mia;
  const ajena = a.reserva && !a.reserva.mia;

  return (
    <div className="space-y-4">
      {/* Encabezado fijo */}
      <header className="sticky top-14 z-[5] -mx-4 space-y-2 border-b border-borde bg-fondo/95 px-4 pb-3 backdrop-blur lg:-mx-6 lg:px-6">
        <div className="flex flex-wrap items-start justify-between gap-3 pt-1">
          <div className="min-w-0">
            <Link
              to={
                bandeja ? rutaSeccion(bandeja === 'supervisor' ? '/validar' : '/trabajar') : rutaSeccion('/articulos')
              }
              className="inline-flex items-center gap-1 text-xs text-suave hover:text-texto"
            >
              <ArrowLeft className="size-3.5" aria-hidden /> {bandeja ? 'Bandeja' : 'Explorar'}
            </Link>
            <h1 className="flex flex-wrap items-center gap-x-3 gap-y-1 text-lg font-semibold">
              {a.item_code}
              <EtiquetaEstado estado={a.estado} />
              {!a.activo && <span className="text-sm font-normal text-rechazado">Inactivo</span>}
            </h1>
            <p className="truncate text-sm text-suave">{a.descripcion}</p>
            <p className="mt-0.5 flex flex-wrap items-center gap-x-3 text-xs text-suave">
              <span>{a.linea === 'IMPORTADO' ? 'Importado' : 'Fabricado'}</span>
              <span>v{a.version}</span>
              {a.clase ? (
                <span className="flex items-center gap-1">
                  Venta: clase {a.clase} · {porcentaje(a.participacion)} · <Tendencia valor={a.tendencia} />
                </span>
              ) : (
                <span>Sin venta en el periodo</span>
              )}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {mia && restante !== null && (
              <span
                className={cn(
                  'flex items-center gap-1 text-sm tabular-nums',
                  restante < 5 * 60_000 ? 'text-rechazado' : 'text-suave',
                )}
                title="Tiempo de tu reserva; se renueva sola mientras trabajas"
              >
                <Lock className="size-4" aria-hidden /> {mmss(restante)}
              </span>
            )}
            {ajena && (
              <span className="flex items-center gap-1 text-sm text-suave">
                <Lock className="size-4" aria-hidden /> {a.reserva?.nombre} lo está trabajando
              </span>
            )}
            {!a.reserva && a.activo && a.acciones.length > 0 && (
              <Boton
                variante="secundario"
                cargando={reservar.isPending}
                onClick={() =>
                  reservar.mutate(
                    { itemCode },
                    {
                      onSuccess: () => void q.refetch(),
                      onError: (e) =>
                        e instanceof ProblemaError &&
                        setAviso({ tono: 'error', titulo: e.problema.title, detalle: e.problema.detail }),
                    },
                  )
                }
              >
                <Lock className="size-4" aria-hidden /> Tomar
              </Boton>
            )}
            {mia && (
              <Boton
                variante="fantasma"
                onClick={() =>
                  soltar.mutate(
                    { itemCode },
                    {
                      onSuccess: () =>
                        bandeja
                          ? void navegar({ to: rutaSeccion(bandeja === 'supervisor' ? '/validar' : '/trabajar') })
                          : void q.refetch(),
                    },
                  )
                }
              >
                <LockOpen className="size-4" aria-hidden /> Soltar
              </Boton>
            )}
            {a.acciones.map((x) => (
              <Boton
                key={x.destino}
                variante={x.destino === 'RECHAZADO' ? 'peligro' : x.destino === 'PENDIENTE' ? 'secundario' : 'primario'}
                disabled={!x.habilitada}
                title={x.razon ?? (x.destino === 'POR_VALIDAR' ? 'Ctrl+Enter' : undefined)}
                cargando={transicionar.isPending && transicionar.variables?.data.destino === x.destino}
                onClick={() => (x.requiere_motivo ? setMotivoPara(x) : ejecutar(x))}
              >
                {x.etiqueta}
              </Boton>
            ))}
          </div>
        </div>

        {a.ultimo_motivo && (
          <p className="rounded-md border border-rechazado/40 bg-rechazado/10 px-3 py-1.5 text-sm">
            <span className="font-medium">Motivo:</span> {a.ultimo_motivo}
          </p>
        )}
        {a.requisitos.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-suave">Para enviar a revisión falta:</span>
            {a.requisitos.map((r) => (
              <button
                key={r.codigo}
                type="button"
                onClick={() => setPestana(r.pestana as Pestana)}
                className="rounded-full border border-borde px-2 py-0.5 hover:bg-superficie-2"
              >
                {r.etiqueta}
              </button>
            ))}
          </div>
        )}
        {a.acciones.find((x) => !x.habilitada && x.razon && x.destino !== 'POR_VALIDAR') && (
          <p className="text-xs text-suave">{a.acciones.find((x) => !x.habilitada)?.razon}</p>
        )}
      </header>

      {aviso && (
        <Aviso tono={aviso.tono} titulo={aviso.titulo}>
          {aviso.detalle}
        </Aviso>
      )}

      {/* Pestañas: en celular se desplazan de lado */}
      <div
        role="tablist"
        aria-label="Secciones del artículo"
        className="-mx-4 flex gap-1 overflow-x-auto border-b border-borde px-4 lg:mx-0 lg:px-0"
      >
        {PESTANAS.filter((p) => !('soloFabricado' in p) || a.linea === 'FABRICADO').map((p) => (
          <button
            key={p.id}
            role="tab"
            type="button"
            aria-selected={pestana === p.id}
            onClick={() => setPestana(p.id)}
            className="border-b-2 border-transparent px-3 py-2 text-sm whitespace-nowrap text-suave aria-selected:border-primario aria-selected:font-medium aria-selected:text-texto"
          >
            {p.etiqueta}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {pestana === 'ficha' && <Ficha itemCode={itemCode} alCambiarPendientes={setPendientesFicha} />}
        {pestana === 'aplicaciones' && <Aplicaciones itemCode={itemCode} />}
        {pestana === 'emparejamiento' && <Emparejamiento itemCode={itemCode} parteInicial={parteUrl} />}
        {pestana === 'equivalencia' && <Equivalencia itemCode={itemCode} />}
        {pestana === 'fotos' && <FotosDelArticulo itemCode={itemCode} />}
        {pestana === 'sap' && <DatosSap a={a} />}
        {pestana === 'historial' && <Historial itemCode={itemCode} />}
      </div>

      {/* La key reinicia el motivo escrito cada vez que se abre para otra acción */}
      <DialogoMotivo
        key={motivoPara?.destino ?? 'cerrado'}
        accion={motivoPara}
        alCerrar={() => setMotivoPara(null)}
        alConfirmar={(m) => motivoPara && ejecutar(motivoPara, m)}
        enviando={transicionar.isPending}
        error={
          transicionar.error instanceof ProblemaError
            ? (transicionar.error.problema.errors?.[0]?.mensaje ?? undefined)
            : undefined
        }
      />
    </div>
  );
}
