# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

The repository holds documents only — no code yet. There is no build system, test runner or source tree to describe; update this file once those exist, rather than assuming any of them.

All project documents are written in European Portuguese. Keep that language when editing them.

| File | What it is |
|------|------------|
| `fichadesafio_alticelabs1.pdf` | The challenge brief (given by the organisers). |
| `Desafio#3_Altice_Hackathon_MCP_ATC2026.pdf` | Altice's guide to the MCP server: connection, authentication, tools, examples (given). |
| `Guia de Participantes - ATC Hackathon 2026.pdf` | Participants' guide: timeline, deliverables, evaluation criteria (given). |
| `templates/` | Official templates for the executive summary (.docx) and the presentation (.pptx). |
| `DECISIONS.md` | The team's decisions. Only the "Decidido" section is settled; "Proposto" and "Em aberto" are not. |
| `PLANO.md` | The plan: what is built, MVP scope, calendar, work fronts, risks. |
| `USER_STORIES.md` | User stories of the MVP (US01–US13). |
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

Deliverables and the rest of the participants' guide must be in Portuguese.

## Chosen stack (not yet implemented)

- **Frontend:** a web page made for mobile, in React, Vite and TypeScript.
- **Backend:** a single Python service holding the AI agent connected to the Altice MCP server, with a simple database.
- **External contact alerts:** a Telegram bot, standing in for SMS.
- **Data:** a simulated dataset provides the home's history and the test cases for detection. No model is trained from scratch.

## The MCP server

Documented in `Desafio#3_Altice_Hackathon_MCP_ATC2026.pdf`; read it before writing integration code.

- **Transport:** HTTP, at the URL in `MCP_URL`.
- **Authentication:** OAuth through Keycloak with the team's account, plus an `X-API-Key` header and an `X-Client-Type` header. Values live in `.env`; never write them into code, documents or commits.
- **Tools:** 16, in four groups — Home (home, devices, rooms, status brief, detail report), Device (details, update capabilities, recommendations), Security (state, change state, alarm history), Scenarios (list, detail, create, activate, execute).
- **Reading and acting on devices:** device state is read with the Home and Device tools; `UPDATE_DEVICE_CAPABILITIES` changes it (the guide's example changes a light's colour).
- **No tool returns camera images.** The camera is reached through an RTSP stream outside the MCP (`CAMERA_RTSP_URL`).

The guide's examples come from Altice's own showroom home. What the team's kit actually exposes is not yet confirmed — check against the live server rather than assuming the examples hold.
