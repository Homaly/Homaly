#!/usr/bin/env bash
# headersHelper do Claude Code para o MCP Connected Home.
# Obtem um token no Keycloak (login direto, sem browser) e escreve em JSON os
# cabecalhos que o servidor MCP exige. Le os valores do .env da raiz do repo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
set -a
# shellcheck disable=SC1091
. "$ROOT/.env"
set +a

TOKEN_URL="$MCP_URL/realms/smarthome-prd-beta-app/protocol/openid-connect/token"

TOKEN="$(curl -sS --fail --max-time 20 -X POST "$TOKEN_URL" \
  --data-urlencode "grant_type=password" \
  --data-urlencode "client_id=$MCP_CLIENT_ID" \
  --data-urlencode "username=$KEYCLOAK_USER" \
  --data-urlencode "password=$KEYCLOAK_PASSWORD" \
  --data-urlencode "scope=openid connected-home-attributes" \
  | python3 -I -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"

TOKEN="$TOKEN" python3 -I -c '
import json, os
print(json.dumps({
    "Authorization": "Bearer " + os.environ["TOKEN"],
    "X-API-Key": os.environ["MCP_API_KEY"],
    "X-Client-Type": os.environ["MCP_CLIENT_TYPE"],
}))'
