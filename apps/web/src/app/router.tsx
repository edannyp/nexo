import { createRootRoute, createRoute, createRouter, Outlet, retainSearchParams } from '@tanstack/react-router';
import { ShieldX } from 'lucide-react';
import type { ReactNode } from 'react';

import { Usuarios } from '@/features/admin/Usuarios';
import { CambiarContrasena } from '@/features/auth/CambiarContrasena';
import { Entrar } from '@/features/auth/Entrar';
import { EnConstruccion } from '@/features/pendiente/EnConstruccion';
import { Panorama } from '@/features/panorama/Panorama';

import { Armazon } from './Armazon';
import { useUsuario } from './contexto-usuario';
import { validarBusqueda } from './filtro';
import { SECCIONES, type Seccion } from './navegacion';
import { puedeVer } from './sesion';

// El filtro global vive en la URL (?cat=25&linea=IMPORTADO) y se conserva al navegar entre secciones.
const raiz = createRootRoute({
  validateSearch: validarBusqueda,
  search: { middlewares: [retainSearchParams(['cat', 'linea'])] },
  component: Outlet,
  notFoundComponent: () => (
    <div className="py-10 text-center">
      <h1 className="text-xl font-semibold">Página no encontrada</h1>
      <p className="mt-2 text-suave">Revisa la dirección o usa el menú.</p>
    </div>
  ),
});

const entrar = createRoute({
  getParentRoute: () => raiz,
  path: '/entrar',
  validateSearch: (s: Record<string, unknown>): { redirigir?: string } =>
    typeof s.redirigir === 'string' ? { redirigir: s.redirigir } : {},
  component: Entrar,
});

const cambiarContrasena = createRoute({
  getParentRoute: () => raiz,
  path: '/cambiar-contrasena',
  component: CambiarContrasena,
});

// Todo lo demás exige sesión: el armazón redirige a /entrar si no la hay.
const app = createRoute({ getParentRoute: () => raiz, id: 'app', component: Armazon });

/** Si el rol o permiso del usuario no alcanza, lo dice en lugar de mostrar la sección. */
function Protegida({ seccion, children }: { seccion: Seccion; children: ReactNode }) {
  const usuario = useUsuario();
  if (puedeVer(usuario, seccion)) return children;
  return (
    <section className="mx-auto max-w-md py-10 text-center">
      <ShieldX className="mx-auto size-10 text-suave" aria-hidden />
      <h1 className="mt-4 text-xl font-semibold">Sin acceso a {seccion.etiqueta}</h1>
      <p className="mt-2 text-suave">Tu rol no incluye esta sección. Si la necesitas, pídela a un administrador.</p>
    </section>
  );
}

const PANTALLAS: Record<string, () => ReactNode> = {
  '/': () => <Panorama />,
  '/admin': () => <Usuarios />,
};

const secciones = SECCIONES.map((s) =>
  createRoute({
    getParentRoute: () => app,
    path: s.ruta,
    component: () => <Protegida seccion={s}>{PANTALLAS[s.ruta]?.() ?? <EnConstruccion seccion={s} />}</Protegida>,
  }),
);

/**
 * Parámetros de búsqueda planos (`?cat=25&linea=IMPORTADO`). El serializador por defecto usa JSON y escribe `?cat=%2225%22`
 * para los textos que parecen números; aquí todos los valores son textos simples y las URL quedan legibles para compartir.
 */
export function leerBusqueda(texto: string): Record<string, string> {
  return Object.fromEntries(new URLSearchParams(texto));
}

export function escribirBusqueda(busqueda: Record<string, unknown>): string {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(busqueda)) if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  const texto = p.toString();
  return texto ? `?${texto}` : '';
}

export const router = createRouter({
  routeTree: raiz.addChildren([entrar, cambiarContrasena, app.addChildren(secciones)]),
  defaultPreload: 'intent',
  parseSearch: leerBusqueda,
  stringifySearch: escribirBusqueda,
});

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
