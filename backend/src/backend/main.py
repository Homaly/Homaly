"""A aplicação FastAPI: `backend.main:app` (é o que o docker-compose.yml arranca)."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import acoes, anomalias, dev, eventos, tempo_real
from .conversa import router as conversa
from .dispositivos import simulacao
from .resposta import router as resposta

app = FastAPI(title="Homaly", description="A casa que repara.")

# A PWA corre noutra origem (Vite em :5173, ou o telemóvel na rede local). Sem login nem cookies.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Cada pessoa acrescenta aqui uma linha com o seu router.
app.include_router(anomalias.router)
app.include_router(eventos.router)
app.include_router(tempo_real.router)
app.include_router(conversa.router)
app.include_router(resposta.router)
app.include_router(acoes.router)

if os.environ.get("HOMALY_DEV") == "1":
    app.include_router(dev.router)
    app.include_router(simulacao.router)  # leituras injetadas para a demo
