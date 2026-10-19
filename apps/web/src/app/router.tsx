import { createRootRoute, createRoute, createRouter, retainSearchParams } from '@tanstack/react-router';

import { EnConstruccion } from '@/features/pendiente/EnConstruccion';
import { Panorama } from '@/features/panorama/Panorama';

import { Armazon } from './Armazon';
import { validarBusqueda } from './filtro';
import { SECCIONES } from './navegacion';

// El filtro global vive en la URL (?cat=25&linea=IMPORTADO) y se conserva al navegar entre secciones.
const raiz = createRootRoute({
  validateSearch: validarBusqueda,
  search: { middlewares: [retainSearchParams(['cat', 'linea'])] },
  component: Armazon,
  notFoundComponent: () => (
    <div className="py-10 text-center">
      <h1 className="text-xl font-semibold">Página no encontrada</h1>
      <p className="mt-2 text-suave">Revisa la dirección o usa el menú.</p>
    </div>
  ),
});

const inicio = createRoute({ getParentRoute: () => raiz, path: '/', component: Panorama });

const pendientes = SECCIONES.filter((s) => s.ruta !== '/').map((s) =>
  createRoute({ getParentRoute: () => raiz, path: s.ruta, component: () => <EnConstruccion seccion={s} /> }),
);

export const router = createRouter({ routeTree: raiz.addChildren([inicio, ...pendientes]), defaultPreload: 'intent' });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
