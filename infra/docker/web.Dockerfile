FROM node:24-alpine AS build

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_API_KEY=
ARG VITE_ADMIN_API_KEY=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_API_KEY=${VITE_API_KEY}
ENV VITE_ADMIN_API_KEY=${VITE_ADMIN_API_KEY}
WORKDIR /app
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM nginx:1.29-alpine
ENV PORT=80 \
    NGINX_ENVSUBST_FILTER=PORT
COPY infra/docker/nginx.conf /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
