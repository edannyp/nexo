import { ProblemaError, useListarFotos, useOrdenarFotos, useSubirFotos, type FotoPropia } from '@nexo/api-client';
import { ChevronLeft, ChevronRight, CircleCheck, ExternalLink, ImagePlus, ImageOff } from 'lucide-react';
import { useRef, useState, type DragEvent } from 'react';

import { cn } from '@/shared/cn';
import { momento } from '@/shared/formato';
import { Aviso, Boton, Dialogo, Insignia } from '@/shared/ui';

const MAX_ARCHIVOS = 10;

/** Mueve el elemento `i` una posición (`-1` izquierda, `1` derecha). */
export function mover<T>(lista: T[], i: number, paso: -1 | 1): T[] {
  const j = i + paso;
  if (i < 0 || i >= lista.length || j < 0 || j >= lista.length) return lista;
  const copia = [...lista];
  const [x] = copia.splice(i, 1);
  copia.splice(j, 0, ...(x === undefined ? [] : [x]));
  return copia;
}

function Miniatura({ url, alt, alAmpliar }: { url: string | null; alt: string; alAmpliar: () => void }) {
  return url ? (
    <button
      type="button"
      onClick={alAmpliar}
      aria-label={`Ampliar ${alt}`}
      className="block aspect-square w-full overflow-hidden rounded-md border border-borde bg-superficie-2"
    >
      <img src={url} alt={alt} loading="lazy" className="size-full object-cover" />
    </button>
  ) : (
    <div className="grid aspect-square w-full place-items-center rounded-md border border-borde bg-superficie-2 text-suave">
      <ImageOff className="size-6" aria-label="Sin vista previa" />
    </div>
  );
}

/** Zona para soltar o elegir fotos. En celular abre la cámara o la galería (el sistema lo pregunta). */
function Subir({ alSubir, subiendo }: { alSubir: (archivos: File[]) => void; subiendo: boolean }) {
  const entrada = useRef<HTMLInputElement>(null);
  const [encima, setEncima] = useState(false);
  const soltar = (e: DragEvent) => {
    e.preventDefault();
    setEncima(false);
    const archivos = [...e.dataTransfer.files].filter((f) => f.type.startsWith('image/'));
    if (archivos.length) alSubir(archivos.slice(0, MAX_ARCHIVOS));
  };
  return (
    <div
      onDragOver={(e) => (e.preventDefault(), setEncima(true))}
      onDragLeave={() => setEncima(false)}
      onDrop={soltar}
      className={cn(
        'flex flex-col items-center gap-2 rounded-lg border-2 border-dashed p-5 text-center text-sm',
        encima ? 'border-primario bg-primario/5' : 'border-borde',
      )}
    >
      <ImagePlus className="size-7 text-suave" aria-hidden />
      <p className="text-suave">
        <span className="hidden sm:inline">Arrastra las fotos aquí o elige hasta {MAX_ARCHIVOS}</span>
        <span className="sm:hidden">Hasta {MAX_ARCHIVOS} fotos</span> (JPG, PNG o WebP).
      </p>
      <input
        ref={entrada}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        className="sr-only"
        aria-label="Elegir fotos"
        onChange={(e) => {
          const archivos = [...(e.target.files ?? [])].slice(0, MAX_ARCHIVOS);
          if (archivos.length) alSubir(archivos);
          e.target.value = '';
        }}
      />
      <Boton cargando={subiendo} onClick={() => entrada.current?.click()}>
        <ImagePlus className="size-4" aria-hidden /> Tomar o elegir fotos
      </Boton>
    </div>
  );
}

/** Fotos propias (con estado de validación y orden) y del catálogo, con subida para el encargado de fotos (ADR 0013). */
export function FotosDelArticulo({ itemCode }: { itemCode: string }) {
  const q = useListarFotos(itemCode);
  const subir = useSubirFotos();
  const ordenar = useOrdenarFotos();
  const [zoom, setZoom] = useState<string | null>(null);
  const [hecho, setHecho] = useState<string>();
  const f = q.data;

  if (q.isError) return <Aviso tono="error" titulo={q.error.problema.title} />;
  if (!f) return <p className="text-sm text-suave">Cargando las fotos…</p>;

  const error = [subir.error, ordenar.error].find((e) => e instanceof ProblemaError);
  const reordenar = (fotos: FotoPropia[]) => ordenar.mutate({ itemCode, data: { ids: fotos.map((x) => x.id) } });
  const alSubir = (archivos: File[]) =>
    subir.mutate(
      { itemCode, data: { archivos } },
      { onSuccess: (r) => setHecho(`${r.subidas} ${r.subidas === 1 ? 'foto subida' : 'fotos subidas'}.`) },
    );

  return (
    <div className="space-y-4">
      {error instanceof ProblemaError && (
        <Aviso tono="error" titulo={error.problema.title}>
          {error.problema.detail}
        </Aviso>
      )}
      {hecho && !error && <Aviso tono="exito" titulo={hecho} />}
      {f.puede_subir &&
        (f.subida_disponible ? (
          <Subir alSubir={alSubir} subiendo={subir.isPending} />
        ) : (
          <Aviso tono="info" titulo="Subida de fotos no configurada">
            La API aún no tiene la llave de escritura de MinIO para las fotos propias.
          </Aviso>
        ))}

      <section className="rounded-lg border border-borde bg-superficie">
        <h2 className="border-b border-borde px-4 py-2 text-xs font-medium tracking-wide text-suave uppercase">
          Fotos propias ({f.propias.length})
        </h2>
        {f.propias.length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-suave">Este artículo aún no tiene fotos propias.</p>
        ) : (
          <ul className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3 lg:grid-cols-4">
            {f.propias.map((p, i) => (
              <li key={p.id} className="space-y-1">
                <Miniatura url={p.url} alt={`foto ${i + 1}`} alAmpliar={() => p.url && setZoom(p.url)} />
                <div className="flex items-center justify-between gap-1 text-xs">
                  {p.validada ? (
                    <span
                      className="flex items-center gap-1 text-validado"
                      title={`Validada por ${p.validada_por ?? ''}`}
                    >
                      <CircleCheck className="size-3.5" aria-hidden /> Validada
                    </span>
                  ) : (
                    <span className="text-suave">Sin validar</span>
                  )}
                  {f.puede_subir && f.propias.length > 1 && (
                    <span className="flex">
                      <button
                        type="button"
                        disabled={i === 0 || ordenar.isPending}
                        onClick={() => reordenar(mover(f.propias, i, -1))}
                        aria-label={`Mover foto ${i + 1} a la izquierda`}
                        className="grid size-7 place-items-center rounded hover:bg-superficie-2 disabled:opacity-30"
                      >
                        <ChevronLeft className="size-4" aria-hidden />
                      </button>
                      <button
                        type="button"
                        disabled={i === f.propias.length - 1 || ordenar.isPending}
                        onClick={() => reordenar(mover(f.propias, i, 1))}
                        aria-label={`Mover foto ${i + 1} a la derecha`}
                        className="grid size-7 place-items-center rounded hover:bg-superficie-2 disabled:opacity-30"
                      >
                        <ChevronRight className="size-4" aria-hidden />
                      </button>
                    </span>
                  )}
                </div>
                <p className="truncate text-xs text-suave" title={momento(p.subida_en)}>
                  {p.subida_por ?? 'Importada'} · {momento(p.subida_en)}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      {f.proveedor.length > 0 && (
        <section className="rounded-lg border border-borde bg-superficie">
          <h2 className="border-b border-borde px-4 py-2 text-xs font-medium tracking-wide text-suave uppercase">
            Del catálogo maestro ({f.proveedor.length})
          </h2>
          <ul className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3 lg:grid-cols-4">
            {f.proveedor.map((p) => (
              <li key={p.url} className="space-y-1">
                <Miniatura url={p.url} alt={p.tipo.toLowerCase()} alAmpliar={() => setZoom(p.url)} />
                <Insignia>
                  {p.tipo.toLowerCase()} · parte {p.parte_id}
                </Insignia>
              </li>
            ))}
          </ul>
        </section>
      )}

      <Dialogo abierto={!!zoom} alCerrar={() => setZoom(null)} titulo="Foto">
        {zoom && (
          <div className="space-y-2">
            <img src={zoom} alt="Foto ampliada" className="max-h-[70vh] w-full object-contain" />
            <a href={zoom} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-sm underline">
              Abrir en otra pestaña <ExternalLink className="size-3.5" aria-hidden />
            </a>
          </div>
        )}
      </Dialogo>
    </div>
  );
}
