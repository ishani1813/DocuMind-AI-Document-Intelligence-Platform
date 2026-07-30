FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json ./
RUN npm install --silent
COPY . .
RUN npm run build

FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
RUN printf 'server {\n  listen 80;\n  root /usr/share/nginx/html;\n  index index.html;\n  location / { try_files $uri $uri/ /index.html; }\n  location /api/ { proxy_pass http://backend:8000; proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; }\n  gzip on;\n  gzip_types text/plain text/css application/json application/javascript;\n}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
