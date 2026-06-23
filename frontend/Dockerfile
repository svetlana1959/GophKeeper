FROM node:24-slim@sha256:c2d5ade763cacfb03fe9cb8e8af5d1be5041ff331921fa26a9b231ca3a4f780a AS build
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build assets
COPY public public/
COPY src src/
COPY index.html .
COPY vite.config.js .
RUN npm run build

FROM nginx:1.30-alpine@sha256:9f00a7a92624975cdd964ec71fbb86bf91dc117e86436a9a91fa7b5cdb9615d1
WORKDIR /usr/share/nginx/html

# Clean default NGINX assets
RUN rm -rf ./*

# Install new assets
COPY --from=build /app/dist ./

# Install NGINX SPA configuration
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf

# Run NGINX
EXPOSE 80
CMD [ "nginx", "-g", "daemon off;" ]
