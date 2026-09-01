FROM node:22-alpine AS build
WORKDIR /app
ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_ALLOW_DEV_LOGIN=true
ARG VITE_SUPER_ADMIN_EMAIL=admin@example.com
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
ENV VITE_ALLOW_DEV_LOGIN=$VITE_ALLOW_DEV_LOGIN
ENV VITE_SUPER_ADMIN_EMAIL=$VITE_SUPER_ADMIN_EMAIL
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
