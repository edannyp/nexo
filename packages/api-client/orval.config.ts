import { defineConfig } from 'orval';

// Cliente generado desde el OpenAPI de apps/api (nunca tipos a mano). Regenerar: `pnpm api-client` en la raíz.
export default defineConfig({
  nexo: {
    input: './openapi.json',
    output: {
      target: './src/generado/nexo.ts',
      client: 'react-query',
      httpClient: 'fetch',
      clean: true,
      override: {
        mutator: { path: './src/fetcher.ts', name: 'nexoFetch' },
        fetch: { includeHttpResponseReturnType: false },
      },
    },
  },
});
