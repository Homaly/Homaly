# Homaly — a casa que repara

Projeto da equipa Homaly para o Hackathon Aveiro Tech City 2026 (Desafio #3 da Altice Labs, "Connected Home, Reimagined").

A casa aprende o que é habitual e avisa quem cuida dela quando alguma coisa foge do normal. Regras simples detetam o desvio; a IA pesa o contexto, decide se vale a pena avisar e escreve a explicação. A casa pergunta antes de alarmar e só age com autorização.

## Correr na tua máquina, sem credenciais

Não há nenhum servidor partilhado: cada pessoa corre a sua própria instância. Nenhum dos modos abaixo precisa de chaves ou contas.

### 1. Só a app, com dados falsos

Precisa de Node.js 24.

```bash
cd frontend
npm install
npm run dev
```

Abre http://localhost:5173. A app usa os dados fixos de `frontend/src/api/mock.ts` e não precisa do backend.

### 2. App e backend, com Docker

```bash
docker compose up --build
```

- Frontend em http://localhost:5173, backend em http://localhost:8000 (a API documentada em http://localhost:8000/docs).
- Para a app falar com o backend em vez dos dados falsos, cria `frontend/.env.development.local` com `VITE_USE_MOCKS=false` e reinicia o frontend.
- O backend começa vazio. Para carregar os mesmos exemplos que a app mostra com dados falsos:

```bash
curl -X POST localhost:8000/dev/exemplo
```

As rotas `/dev` (pôr anomalias, eventos e leituras à mão) estão descritas em `backend/README.md`. Existem só com `HOMALY_DEV=1`, que o `docker-compose.yml` já define, porque não pedem login: não as exponhas na internet.

### 3. Testes

Precisa do [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
uv run pytest
```

## O que precisa de credenciais

Copia `.env.example` para `.env` e preenche só o que quiseres usar. Usa sempre credenciais tuas; o `.env` nunca vai para o git.

| O quê | Variáveis | Sem elas |
|---|---|---|
| Casa real (servidor MCP da Altice) | `MCP_URL`, `MCP_API_KEY`, `KEYCLOAK_USER`, `KEYCLOAK_PASSWORD`, ... | Só as rotas `/dev`; o ciclo das regras (`CICLO=1`) precisa do MCP |
| IA (Groq ou Gemini, planos gratuitos) | `IA_FORNECEDOR`, `GROQ_API_KEY` ou `GEMINI_API_KEY` | `IA_FORNECEDOR=falso`: a explicação é o resumo do desvio |
| SMS ao contacto externo (textbee) | `TEXTBEE_API_KEY`, `TEXTBEE_DEVICE_ID` | As SMS ficam só no log |
| Calendário Google | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `APP_URL` | O calendário fica desligado |
| Câmara (US13) | `CAMERA_RTSP_URL` e uma IA que veja imagens | A US13 não corre |

O servidor MCP e o kit de dispositivos foram dados pela Altice Labs às equipas do hackathon; o guia está em `docs/Desafio#3_Altice_Hackathon_MCP_ATC2026.pdf`.

## Saber mais

- `AGENTS.md`: o estado do projeto e os comandos.
- `backend/README.md`: como se ligam os módulos do backend.
- `docs/frontend-design.md`: o desenho da PWA e o contrato da API.
- `DECISIONS.md`, `PLANO.md`, `USER_STORIES.md`: as decisões, o plano e as user stories.
