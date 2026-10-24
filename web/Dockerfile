# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS base
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    PNPM_HOME=/pnpm
RUN corepack enable
WORKDIR /app

# ---- deps: install once, reused by dev and build ----
FROM base AS deps
COPY package.json pnpm-lock.yaml ./
RUN --mount=type=cache,id=pnpm-store,target=/pnpm/store \
    pnpm config set store-dir /pnpm/store && pnpm install --frozen-lockfile

# ---- dev: Vite dev server with hot reload (docker-compose.dev.yml) ----
FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["pnpm", "dev", "--host", "0.0.0.0"]

# ---- build: static bundle ----
FROM deps AS build
COPY . .
RUN pnpm build

# ---- runtime: nginx serves the SPA and proxies /api and /ws to the API ----
FROM nginxinc/nginx-unprivileged:1.28-alpine AS runtime
ENV API_UPSTREAM=http://api:8000
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
