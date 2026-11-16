# Desenvolvimento: servidor do Vite com recarregamento automatico.
# O codigo entra por bind mount (ver docker-compose.yml); a imagem so traz as dependencias.
FROM node:24-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
