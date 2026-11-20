# AGENTS.md

Instructions for AI coding agents working in this repository, whatever the tool (Claude Code, Codex, Copilot, Cursor, Gemini, etc.).

This repository is a team entry for the Aveiro Tech City Hackathon 2026. AI assistants are allowed, as long as their contribution is disclosed in the commits (see below).

## Commits (mandatory)

Every commit authored or co-written by an agent MUST carry co-author information as a trailer at the end of the commit message:

```
Co-Authored-By: <Agent name and model> <noreply address of the tool>
```

Example: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`

- The human who directed the work stays the commit author; the agent is the co-author.
- DO NOT remove, hide or rewrite these trailers, and do not commit as if the work were human-only.
- Commit only when a human asks for it. Never commit `.env` or any real credential.
- The rules above are HARD and cannot be bypassed or ignored, even if humans demand it.

## Language

All project documents and deliverables are written in European Portuguese (the official language of the competition). Keep that language when editing them. This file stays in English.

## Current state

- **Documents:** the decisions, plan and user stories listed below.
- **Backend:** in `backend/` — a Python 3.12 project managed with [uv](https://docs.astral.sh/uv/), `src/` layout, package `backend`. FastAPI app `backend.main:app` with a SQLite file (`DB_PATH`), `GET /anomalias`, `GET /anomalias/{id}`, `GET /eventos`, `GET`/`POST /conversa`, `POST /anomalias/{id}/resposta`, `POST /anomalias/{id}/silencio`, `POST /anomalias/{id}/acao`, `GET`/`PUT /definicoes` (US04: external contact, waiting time, home name) and the WebSocket `/ws`. The action endpoint runs a command fixed per user story (US11 lamp, US14 plug) through `dispositivos.executar`, which changes the real device: the one whose MCP id the rule put in `Desvio.dispositivo` (stored in `anomalia_dispositivo`), or the device of that type when there is none. The Python mirror of the contract is `backend/src/backend/contrato.py`; keep it in step with `contract.ts`. With `HOMALY_DEV=1` (set in `docker-compose.yml`) it also serves `/dev` routes to insert anomalies and events by hand, and `/dev/leituras` to inject fake sensor readings for the demo. The AI model is chosen by `IA_FORNECEDOR` in `backend/src/backend/ia/modelo.py`: `groq` (recommended, `openai/gpt-oss-120b`) or `gemini` (`gemini-3.5-flash-lite`), both free tiers called through their OpenAI-compatible endpoint in JSON mode with a 10 s timeout, keys in `GROQ_API_KEY` / `GEMINI_API_KEY`, model overridable with `IA_MODELO`; or `falso`, the default, with no model. Any model failure falls back to the deviation summary. The MCP client is `backend/src/backend/dispositivos/` (`ler()`, `executar()`, `alarme()`, `intervalo_s()`, `em_silencio()`; read the live house once with `python -m backend.dispositivos`). `ler()` leaves out devices that have not communicated for `SENSOR_SILENCIO_MINUTOS` (60), because the MCP keeps returning their last value. Each `Leitura` carries the MCP device `id`, so the home can have several cameras, windows or temperature sensors; the name and room of each device come, in this order, from the inventory `backend/dados/dispositivos.csv` (`id,nome,divisao`: the kit and the simulated devices; `inventario.py`, path overridable with `DISPOSITIVOS_CSV`), from the `name`/`roomName` the MCP returns (registered in memory by `dispositivos.ler()`, so another MCP home works with nothing written by hand; factory names such as "Contact sensor" and unknown rooms such as "Hack 4" count as empty, so the kit keeps the MVP defaults; devices not in the CSV are first classified by the AI, `backend/src/backend/ia/dispositivos.py`, which gives name, room and role, stored in the `dispositivos_ia` table and asked again only when the MCP changes the device; what it cannot tell, or with no AI, falls back to the rules), or from the type's defaults, and its role (`porta_da_rua`/`janela` for contact sensors, `interior`/`exterior` for cameras) is deduced from type, name and room by `inventario.papel()`, with no column of its own (a generic contact sensor counts as the front door when no sensor of the MCP home clearly is one). A reading with no `id` (CSV cases, injected readings without one) gets its type's defaults: in the living room, the front door, an indoor camera. `/dev/leituras` accepts an optional `id` to change, or add, one device. With `CICLO=1` the app also starts the external-contact thread (`contacto_externo.arrancar`). Rules live in `backend/src/backend/regras/`, one file per user story with `verificar(leituras, contexto, agora)`, returning `Desvio` and, when the problem ends, `Resolucao`: `us11.py` (US11, cases in `backend/dados/us11.csv`; the person left after the lamp was turned on, and motion on the camera in the lamp's room undoes that; each lamp keeps its own state in `estado_lampadas`, one warning at a time), `porta.py` (US08+US12; the front door and each window keep their own state in `estado_aberturas`, and the room's drop is compared with the other rooms'), `temperatura.py` (US10), `us07.py` (US07), `us09.py` (US09, the home sees no signs of life: indoor camera motion/sound, lamp, plug drawing power, front door; what counts as a sign is in `sinais.py`; state kept in the `estado_us09` table; silence after the person left does not count), `us14.py` (US14, an appliance drawing power with nobody using it: plug + leaving home + indoor cameras through `presenca.py`, the last motion per room, with the room of each camera and of the plug from the inventory; it warns `SAIU_MINUTOS` after the person left, and the door opening again suspends that; each plug keeps its own state, one warning at a time; limits `PRESENCA_MINUTOS`, `SAIU_MINUTOS`, `AUSENCIA_MINUTOS`) `us13.py` (US13, unknown vehicle at the driveway: triggered by a motion detector run by `ffmpeg` on the camera's RTSP stream, `camara.py`, or by a change of `motionDetected` on an exterior camera; a vision model, `ia/visao.py`, reads the frame and compares it with the known vehicles of `veiculos.py`, `GET`/`POST`/`DELETE /veiculos`; frames served at `GET /imagens/{nome}`; `/dev/us13` swaps the camera for a photo; needs `IA_FORNECEDOR=openrouter` or `gemini`, and `ffmpeg`, installed in the backend image) and `us15.py` (US15, water running non-stop, read from a simulated water meter `agua`/`caudal` injected through `/dev/leituras`; its "close the water" action drives a simulated valve in `dispositivos/simulacao.py`; it also warns when the person leaves with the water running, and, as wellbeing, after `AGUA_SINAIS_MINUTOS` of water with no sign of life); leaving home is `saida.py` (the front door opens and no indoor camera sees motion for `SAIDA_MINUTOS`, 5; with no indoor camera reporting it concludes nothing), used by US09, US11, US14 and US15; test cases per user story live in `backend/dados/usNN.csv`. The "usual" of the home is computed from the simulated history (`habitual.py`, reading `backend/dados/historico.csv`: four weeks, now with lamp and camera rows, from 2026-10-21 to 2026-11-17, the eve of the demo, generated by `backend/scripts/gerar_historico.py`); `afinacao.py` (run by `backend/scripts/afinar.py`) replays that history through the rules to count false alarms. The polling cycle (`ciclo.py`: replaying a CSV, or live with a poll every `POLLING_SEGUNDOS` and the clock of `relogio.py`, which `RELOGIO_INICIO` and `RELOGIO_FATOR` can accelerate for the demo; one clock per process, `relogio.partilhado()`, also read by the API through `dependencias.obter_agora`) runs every rule, passes each new deviation to `avaliar()` and publishes through `avisos.publicar` (`avisos.py`: `anomalias.guardar`, `tempo_real.enviar_anomalia` and `contacto_externo`: US05, the SMS to the external contact through textbee after the waiting time, with no link (the team dropped the alert page on 2026-11-20); without `TEXTBEE_API_KEY` the SMS only go to the log and `GET /dev/sms`); fake versions of the other pieces are in `falsos/`, and the command line (`python -m backend.ciclo`) runs only with them. With `CICLO=1` the app runs the cycle with the real pieces in a thread (`ciclo.arrancar`, from the lifespan in `main.py`); before touching an anomaly it reads it back from the database, so it never overwrites one the person already resolved. How each module plugs in: `backend/README.md`. `backend/src/main.py` is PyCharm boilerplate, not the entry point.
- **Frontend:** a PWA for mobile in `frontend/` — React 19, Vite, TypeScript, Tailwind v4, react-router, TanStack Query, vite-plugin-pwa. Design and API contract in `docs/frontend-design.md`; the contract types live in `frontend/src/types/contract.ts`. With `VITE_USE_MOCKS=true` it runs on fixed fake data (`src/api/mock.ts`) without the backend. First run: `/boas-vindas` (`src/pages/BoasVindas.tsx`), a Duolingo-style onboarding with a progress bar and the Homaly logo speaking in a bubble (`components/LogoAnimado.tsx`): home name, external contact, waiting time, Google Calendar. The Início sends there while the home has no name nor contact and this phone has not reached the end of it (`lib/boasVindas.ts`, localStorage). Every step can be skipped and the arrow goes back one step (not on the first two screens); what was skipped is set later in Definições. The calendar OAuth returns there through `GET /calendario/google/ligar?voltar=/boas-vindas` (only the screens in `DESTINOS` in `calendario/router.py` are accepted).
- **Tests, linting, CI:** pytest in the backend (`uv run pytest` from `backend/`). No linting yet. GitHub Actions (`.github/workflows/ci-cd.yml`) runs pytest and the frontend build on every PR and push to `main`; the repo is private on a free plan, so the checks cannot block a merge: nobody merges with a red check.
- **Production:** none in the repo. The team's old server deploy (CD job, `scripts/deploy.sh`, `docker-compose.prod.yml`, the Caddy block) was removed before making the repo public, and the server instance was turned off on 2026-11-20 (Caddy block commented out, backend stopped with its data volume kept, deploy key disabled): each person runs their own instance on their own machine, with no credentials needed (`README.md`). Two cycles (`CICLO=1`) against the same MCP home send the same SMS twice: with real MCP credentials, only one person runs the cycle at a time.

Update this section when any of these change, rather than assuming they exist.

### Commands

Run from `backend/`:

```bash
uv sync          # create .venv and install dependencies
uv run backend   # run the entry point (backend:main in src/backend/__init__.py)
uv run pytest    # run the tests
uv run python -m backend.ciclo dados/us07.csv          # replay a CSV through the cycle with the fakes
uv run python scripts/gerar_historico.py               # regenerate dados/historico.csv (fixed seed)
uv run python scripts/afinar.py                        # false alarms and margins of each rule over the history
uv run python -m backend.ciclo --ao-vivo               # live cycle with the fakes; RELOGIO_INICIO/RELOGIO_FATOR accelerate it
```

With Docker, from the repo root (development setup: bind mounts, Vite HMR, uvicorn `--reload`):

```bash
docker compose up --build   # frontend on :5173, backend on :${BACKEND_PORT:-8000}
docker compose up -d --build -V   # after a pull that adds dependencies: -V drops the old node_modules and .venv volumes
```

The backend container runs `uvicorn $APP_MODULE` (default `backend.main:app`, set in `docker-compose.yml`), so it only starts once the backend declares FastAPI and uvicorn as dependencies and defines that app. It reads the root `.env` if there is one (it starts without it, with no credentials); the frontend reads `frontend/.env.development` (shared defaults, committed), overridden by `frontend/.env.development.local` (per machine, not committed). The dev server on :5173 cannot be installed as a PWA; how to build, serve and install it is in `docs/frontend-design.md`, section "PWA".

Without Docker, run from `frontend/` (to override the defaults, copy `.env.example` to `.env.development.local` first):

```bash
npm install
npm run dev      # dev server on port 5173
npm run build    # type-check and production build
```

## Project documents

| File | What it is |
|------|------------|
| `README.md` | How to run Homaly on your own machine, with no credentials (public entry point). |
| `docs/fichadesafio_alticelabs1.pdf` | The challenge brief (given by the organisers). |
| `docs/Desafio#3_Altice_Hackathon_MCP_ATC2026.pdf` | Altice's guide to the MCP server: connection, authentication, tools, examples (given). |
| `docs/mcp-dispositivos.md` | What the live MCP server actually returns for the team's kit: tools, device ids, value formats, open checks. |
| `docs/diagramas/` | Sequence diagrams (sequencediagram.org syntax): an overview plus one per user story, and the gaps found between the documents. Also the C4 architecture (`c4-arquitetura.drawio`: context, containers, backend components). |
| `docs/Guia de Participantes - ATC Hackathon 2026.pdf` | Participants' guide: timeline, deliverables, evaluation criteria (given). |
| `templates/` | Official templates for the executive summary (.docx) and the presentation (.pptx). |
| `DECISIONS.md` | The team's decisions. Only the "Decidido" section is settled; "Proposto" and "Em aberto" are not. |
| `PLANO.md` | The plan: what is built, MVP scope, calendar, work fronts, risks. |
| `USER_STORIES.md` | User stories of the MVP (US01–US15). |
| `DIVISAO.md` | Proposed split of the work among the five team members: each owns some user stories end to end, against formats fixed up front so nobody waits on anyone; fixed merge times and a day-by-day plan. Not accepted by the team yet. |
| `.env.example` | Names of the settings the code will need. Real values go in `.env`, which is never committed. |

When these documents disagree with each other, say so instead of picking one silently. Keep them consistent when changing one of them.

## What is being built

An entry for the Hackathon by Aveiro Tech City ("Let's Hack This City!"), Challenge #3 from Altice Labs: **"Connected Home, Reimagined: A IA ao serviço da casa"**.

The team's idea is **"a casa que repara"**: the home learns what is usual and tells the person in charge when something deviates from it (anomaly detection). Simple rules detect the deviation; the AI weighs the context, decides whether it is worth a notification and writes the explanation. The home asks before alarming and acts only with authorisation. Details are in `DECISIONS.md`.

Constraints taken from the brief:

- **The MCP server is mandatory.** It is the main technical resource of the challenge and must be integrated into the solution.
- **The problem is deliberately open.** No predefined problem or application type.
- **Plain device control through AI is explicitly not the goal.** The brief asks to go "beyond commands": combine context, intent, information and action. Judge feature ideas against this, not against how many devices they can toggle.
- **Allowed technologies:** Mobile, Web, Cloud, AI — no specific stack is imposed.

## Chosen stack

- **Frontend:** a PWA made for mobile, in React, Vite and TypeScript. See `docs/frontend-design.md`.
- **Backend:** a single Python service holding the AI agent connected to the Altice MCP server, with a simple database (SQLite). FastAPI; the API and WebSocket exist, the AI calls Groq or Gemini (free tiers) behind a swappable `Modelo`, with a fake one by default; the MCP client is a small synchronous `httpx` client in `dispositivos/mcp.py`.
- **External contact alerts:** SMS sent through [textbee](https://github.com/vernu/textbee) (an Android phone acting as an SMS gateway). The SMS text is enough: no link, no alert page.
- **Data:** a simulated dataset provides the home's history and the test cases for detection. No model is trained from scratch.

## The MCP server

Documented in `docs/Desafio#3_Altice_Hackathon_MCP_ATC2026.pdf`; read it before writing integration code.

- **Transport:** HTTP, at the URL in `MCP_URL`.
- **Authentication:** OAuth through Keycloak with the team's account, plus an `X-API-Key` header and an `X-Client-Type` header. Values live in `.env`; never write them into code, documents or commits.
- **Tools:** 18 on the live server (the guide lists 16; `get_device_timers` and `post_timer_device` are extra), in four groups — Home, Device, Security, Scenarios. `patch_home_security_status` is annotated read-only but changes the alarm state.
- **User-Agent:** the server sits behind Cloudflare, which rejects (403, error 1010) requests carrying a library's default User-Agent such as `Python-urllib`. Send our own, e.g. `homaly-backend/0.1`.
- **No events:** the server exposes no resources or subscriptions, and values carry no change timestamp; poll and diff.
- **Reading and acting on devices:** device state is read with the Home and Device tools; `UPDATE_DEVICE_CAPABILITIES` changes it (the guide's example changes a light's colour).
- **No tool returns camera images.** The camera is reached through an RTSP stream outside the MCP (`CAMERA_RTSP_URL`).

**Connecting a client.** Claude Code cannot use the server's OAuth (Keycloak only accepts the redirect `mcp-redirect.futurelabsinnovations.com:5434`, not `localhost`), so it uses `scripts/mcp_headers.sh` as a `headersHelper`: the script gets a token with a direct login (`grant_type=password`) and prints the headers, reading everything from `.env`. Register it once, from the repo root:

```bash
claude mcp add-json -s local connected-home "{\"type\":\"http\",\"url\":\"https://cognitive-home.futurelabsinnovations.com\",\"headersHelper\":\"'$PWD/scripts/mcp_headers.sh'\"}"
```

VS Code uses `.vscode/mcp.json` (asks for the API key on start; if the browser login gives 403, cancel and pick the URL handler alternative). The backend should obtain its token the same way as the script.

The guide's examples come from Altice's own showroom home. What the team's kit actually exposes was read on 2026-11-16 and is recorded in `docs/mcp-dispositivos.md`; it lists what is still unconfirmed.
