# Pre-built dist is copied from the host (built locally with VITE_API_BASE_URL=/api).
# This avoids npm install inside Docker, which fails due to network issues on
# Docker Desktop for Windows (TLS connection drops on long npm registry downloads).
#
# To rebuild: run `npm run build` locally (with VITE_API_BASE_URL=/api set),
# then `docker compose build nginx`.
FROM nginx:alpine
COPY dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
