/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// En desarrollo, /api se redirige a la API local (uvicorn en :8000). En el servidor lo hace Caddy.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    // Una sola copia: pnpm instala React Query dos veces (para la consola y para @nexo/api-client) y, compiladas por separado,
    // los hooks generados no ven el QueryClient de la consola ("No QueryClient set"). En desarrollo Vite ya las unificaba.
    dedupe: ['react', 'react-dom', '@tanstack/react-query'],
  },
  server: {
    host: true,
    proxy: { '/api': process.env.NEXO_API_URL ?? 'http://localhost:8000' },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/pruebas.setup.ts'],
  },
});
