"""A aplicação FastAPI: `backend.main:app` (é o que o docker-compose.yml arranca)."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import anomalias, dev, eventos, tempo_real

app = FastAPI(title="Homaly", description="A casa que repara.")

# A PWA corre noutra origem (Vite em :5173, ou o telemóvel na rede local). Sem login nem cookies.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Cada pessoa acrescenta aqui uma linha com o seu router.
app.include_router(anomalias.router)
app.include_router(eventos.router)
app.include_router(tempo_real.router)

if os.environ.get("HOMALY_DEV") == "1":
    app.include_router(dev.router)
