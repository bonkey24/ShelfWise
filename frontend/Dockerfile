# Stage 1: Build React application
FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci || npm install

ARG VITE_API_URL=http://localhost:8000/api
ARG VITE_SHOW_DEMO_LOGIN=true

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_SHOW_DEMO_LOGIN=$VITE_SHOW_DEMO_LOGIN

COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

