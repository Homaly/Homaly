#!/usr/bin/env bash
# Corre NA VM, a partir da pasta do repo (~/homaly): atualiza o codigo, recompila a PWA e reinicia o backend.
# Usado a mao ou pelo workflow de deploy (GitHub Actions por SSH).
set -euo pipefail
cd "$(dirname "$0")/.."

DOMINIO="${HOMALY_DOMINIO:-homaly.duckdns.org}"
WWW="${HOMALY_WWW:-/srv/homaly/www}"

# Sem .git (primeiro deploy, copiado por rsync) usa o codigo que ja la esta.
if [ -d .git ]; then
  git fetch --quiet origin main
  git reset --hard origin/main
fi

# A PWA: compila-se numa imagem, copia-se o resultado para uma pasta temporaria e so depois
# substitui a atual. Sem BuildKit/buildx (a VM nao o tem), por isso nada de --output.
export DOCKER_BUILDKIT=0 COMPOSE_BAKE=false
docker build -q -f frontend/Dockerfile.prod \
  --build-arg "VITE_API_URL=https://${DOMINIO}/api" \
  --build-arg "VITE_WS_URL=wss://${DOMINIO}/api/ws" \
  -t homaly-www frontend
NOVO="$(mktemp -d)"
docker rm -f homaly-www-tmp >/dev/null 2>&1 || true
docker create --name homaly-www-tmp homaly-www /nada >/dev/null
docker cp homaly-www-tmp:/. "${NOVO}"
docker rm homaly-www-tmp >/dev/null
rm -rf "${WWW:?}"/*
cp -a "${NOVO}"/. "${WWW}"/
chmod -R a+rX "${WWW}"   # o Caddy corre como outro utilizador
rm -rf "${NOVO}"

docker compose -f docker-compose.prod.yml up -d --build
docker image prune -f >/dev/null
echo "Deploy feito: https://${DOMINIO}"
