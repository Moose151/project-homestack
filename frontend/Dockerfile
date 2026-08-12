# HomeStack frontend — two explicit targets.
#
#   development  Vite dev server with hot reload      (docker-compose.dev.yml)
#   production   built bundle served by nginx         (docker-compose.yml, the live path)
#
# `production` is last so a bare `docker build ./frontend` produces the production image, but both
# Compose files name their target explicitly rather than relying on that.

# --- Development ------------------------------------------------------------------------------
FROM node:20-alpine AS development

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# --- Production build -------------------------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# `npm ci` installs exactly the lockfile, so a production image can never pick up a drifted
# transitive version that local development happened to resolve.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# `npm run build` is `tsc && vite build` — a type error fails the image build rather than shipping.
RUN npm run build

# --- Production runtime -----------------------------------------------------------------------
FROM nginx:1.27-alpine AS production

# Replace the stock server block entirely; ours listens on 5173 and adds the SPA fallback.
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/homestack.conf
COPY nginx-security-headers.conf /etc/nginx/snippets/homestack-security-headers.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 5173

# nginx:alpine's own CMD already runs in the foreground with logs on stdout/stderr.
