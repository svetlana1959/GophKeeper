FROM node:24-slim AS build
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

FROM nginx:1.30-alpine
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
