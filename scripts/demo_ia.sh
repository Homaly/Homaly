#!/usr/bin/env bash
# Demo da conversa (US01) e da resposta às anomalias (US02) contra o backend a correr.
#
# Precisa do backend com HOMALY_DEV=1 (o docker-compose.yml já o liga), de curl e de jq.
#   docker compose up --build        # noutro terminal
#   scripts/demo_ia.sh               # usa BACKEND_PORT do .env; ou HOMALY_URL=http://outro:8000
#
# Sem modelo de IA (IA_FORNECEDOR=falso) a casa não percebe a conversa e nunca propõe
# silêncio; o script mostra isso e os erros previstos (404, 409, 422).

set -euo pipefail

# A porta é a do docker-compose.yml: BACKEND_PORT no .env da raiz, senão 8000.
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
PORTA=$(sed -n 's/^BACKEND_PORT=\([0-9]*\).*/\1/p' "$RAIZ/.env" 2>/dev/null | tail -n1)
URL="${HOMALY_URL:-http://localhost:${PORTA:-8000}}"
JSON='Content-Type: application/json'

passo() { printf '\n\033[1;34m== %s\033[0m\n' "$1"; }

# Faz um pedido e mostra o código HTTP e o JSON. Uso: pedido METODO CAMINHO [CORPO]
pedido() {
    local metodo=$1 caminho=$2 corpo=${3:-}
    local args=(-s -w '\n%{http_code}' -X "$metodo" "$URL$caminho")
    [[ -n $corpo ]] && args+=(-H "$JSON" -d "$corpo")
    local resposta codigo
    resposta=$(curl "${args[@]}")
    codigo=${resposta##*$'\n'}
    printf '\033[2m%s %s -> %s\033[0m\n' "$metodo" "$caminho" "$codigo"
    printf '%s\n' "${resposta%$'\n'*}" | jq . 2>/dev/null || printf '%s\n' "${resposta%$'\n'*}"
}

if ! curl -sf "$URL/anomalias" >/dev/null; then
    echo "O backend não responde em $URL. Arranca-o com: docker compose up --build" >&2
    exit 1
fi

passo "1. A pessoa fala com a casa (POST /conversa)"
pedido POST /conversa '{"texto": "Vou de férias até dia 25."}'

passo "2. A conversa guardada (GET /conversa)"
pedido GET /conversa

passo "3. Texto vazio é recusado (422)"
pedido POST /conversa '{"texto": "   "}'

passo "4. Uma anomalia nova, posta à mão (POST /dev/anomalias)"
anomalia=$(curl -s -X POST "$URL/dev/anomalias" -H "$JSON" \
    -d '{"classe": "bem_estar", "titulo": "A porta não abriu", "explicacao": "A porta costuma abrir até às 9h; hoje ainda não abriu."}')
if ! id=$(jq -er .id <<<"$anomalia" 2>/dev/null); then
    echo "Não consegui criar a anomalia. O backend tem HOMALY_DEV=1?" >&2
    echo "$anomalia" >&2
    exit 1
fi
jq . <<<"$anomalia"

passo "5. A pessoa responde (POST /anomalias/$id/resposta): fica resolvida"
pedido POST "/anomalias/$id/resposta" '{"texto": "Está tudo bem, saí mais tarde."}'

passo "6. Responder outra vez dá 409"
pedido POST "/anomalias/$id/resposta" '{"texto": "Outra vez."}'

passo "7. Sem proposta de silêncio, aceitar dá 409"
pedido POST "/anomalias/$id/silencio" '{"aceitar": true}'

passo "8. Uma anomalia que não existe dá 404"
pedido POST /anomalias/nao-existe/resposta '{"texto": "Olá"}'

passo "9. A anomalia como a PWA a vê agora (GET /anomalias/$id)"
pedido GET "/anomalias/$id"

echo
echo "Feito. Os pedidos também se experimentam em $URL/docs."
