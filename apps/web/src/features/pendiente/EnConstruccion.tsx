import { Construction } from 'lucide-react';

import type { Seccion } from '@/app/navegacion';

/** Marcador de las secciones que llegan en pasos posteriores de la ruta de construcción. */
export function EnConstruccion({ seccion }: { seccion: Seccion }) {
  return (
    <section aria-labelledby="titulo" className="mx-auto max-w-2xl py-10 text-center">
      <seccion.icono className="mx-auto size-10 text-suave" aria-hidden />
      <h1 id="titulo" className="mt-4 text-xl font-semibold">
        {seccion.etiqueta}
      </h1>
      <p className="mt-2 text-suave">{seccion.descripcion}</p>
      <p className="mt-6 inline-flex items-center gap-2 rounded-full border border-borde px-3 py-1 text-sm text-suave">
        <Construction className="size-4" aria-hidden />
        Llega en el paso {seccion.paso} de la ruta de construcción
      </p>
    </section>
  );
}
