import './styles.css';

import { ProblemaError } from '@nexo/api-client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from '@tanstack/react-router';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { router } from './app/router';

const consultas = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // Los errores del cliente (4xx) no se reintentan: repetirlos no cambia la respuesta.
      retry: (intentos, error) => !(error instanceof ProblemaError && error.problema.status < 500) && intentos < 2,
    },
  },
});

createRoot(document.getElementById('raiz')!).render(
  <StrictMode>
    <QueryClientProvider client={consultas}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
