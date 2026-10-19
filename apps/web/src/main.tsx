import './styles.css';

import { alPerderSesion, getObtenerSesionQueryKey, ProblemaError } from '@nexo/api-client';
import { MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from '@tanstack/react-router';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { router } from './app/router';
import { invalidarArticulos } from './shared/consultas';

const consultas: QueryClient = new QueryClient({
  // Cualquier cambio (estado, reserva, ficha…) deja viejas las listas, conteos y el panorama: se refrescan
  mutationCache: new MutationCache({ onSuccess: () => invalidarArticulos(consultas) }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // Los errores del cliente (4xx) no se reintentan: repetirlos no cambia la respuesta.
      retry: (intentos, error) => !(error instanceof ProblemaError && error.problema.status < 500) && intentos < 2,
    },
  },
});

// Si la sesión vence o la cierra un administrador, se vuelve a consultar: el armazón lleva a /entrar.
alPerderSesion(() => void consultas.resetQueries({ queryKey: getObtenerSesionQueryKey() }));

createRoot(document.getElementById('raiz')!).render(
  <StrictMode>
    <QueryClientProvider client={consultas}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
