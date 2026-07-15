FROM node:24-alpine AS build

ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
WORKDIR /app
COPY apps/web/package*.json ./
RUN npm install
COPY apps/web/ ./
RUN npm run build

FROM nginx:1.29-alpine
COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

