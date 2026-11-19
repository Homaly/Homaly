"""A aplicação FastAPI: `backend.main:app` (é o que o docker-compose.yml arranca)."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import acoes, anomalias, ciclo, contacto_externo, definicoes, dev, eventos, relogio, tempo_real
from .calendario import google as calendario_google
from .calendario import router as calendario_router
from .calendario import sincronizar as calendario_sincronizar
from .contacto_externo import pagina, sms
from .conversa import router as conversa
from .dependencias import obter_agora, obter_modelo_dep
from .dispositivos import simulacao
from .resposta import router as resposta


@asynccontextmanager
async def _vida(app: FastAPI):
    # O relógio começa a contar no arranque, com ou sem ciclo, para a API ter a hora simulada.
    relogio.partilhado()
    # O ciclo das regras (Vila): só com CICLO=1, para os testes e a PWA não lerem o MCP.
    parar = ciclo.arrancar() if os.environ.get("CICLO") == "1" else None
    # O contacto externo (US05) envia as SMS que o ciclo agenda; arranca com ele, ou com
    # HOMALY_DEV=1, para as anomalias de /dev/anomalias?contacto=true também chegarem a sair.
    com_contacto = parar is not None or os.environ.get("HOMALY_DEV") == "1"
    parar_contacto = contacto_externo.arrancar() if com_contacto else None
    # O calendário Google lê-se de hora a hora, se a app estiver registada na Google (.env).
    parar_calendario = (
        calendario_sincronizar.arrancar(obter_agora, obter_modelo_dep)
        if calendario_google.credenciais() is not None
        else None
    )
    yield
    if parar_calendario is not None:
        parar_calendario.set()
    if parar is not None:
        parar.set()
    if parar_contacto is not None:
        parar_contacto()


app = FastAPI(title="Homaly", description="A casa que repara.", lifespan=_vida)

# A PWA corre noutra origem (Vite em :5173, ou o telemóvel na rede local). Sem login nem cookies.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Cada pessoa acrescenta aqui uma linha com o seu router.
app.include_router(anomalias.router)
app.include_router(eventos.router)
app.include_router(tempo_real.router)
app.include_router(conversa.router)
app.include_router(resposta.router)
app.include_router(acoes.router)
app.include_router(definicoes.router)
app.include_router(calendario_router.router)
app.include_router(pagina.router)  # a página do alerta, para o contacto externo (sem login)

if os.environ.get("HOMALY_DEV") == "1":
    app.include_router(dev.router)
    app.include_router(simulacao.router)  # leituras injetadas para a demo
    app.include_router(sms.router)  # as SMS que não saíram por falta do textbee
