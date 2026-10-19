# Consola web de Nexo servida por Caddy, que además hace de proxy inverso hacia la API.
# Contexto de construcción: raíz del repositorio (usa el workspace de pnpm y packages/api-client).
FROM node:24-slim AS construccion
RUN corepack enable
WORKDIR /repo
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/
COPY packages/api-client/package.json packages/api-client/
RUN pnpm install --frozen-lockfile
COPY packages/api-client packages/api-client
COPY apps/web apps/web
RUN pnpm --filter @nexo/web build

FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=construccion /repo/apps/web/dist /srv
