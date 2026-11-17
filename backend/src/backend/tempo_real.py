"""WebSocket `/ws`: o servidor avisa a PWA do que muda; o cliente não envia nada.

Mensagens (ver `MensagemWs` em contract.ts):
    {"tipo": "anomalia", "anomalia": {...}}   uma anomalia apareceu ou mudou
    {"tipo": "evento", "evento": {...}}       há um evento novo

`enviar_anomalia` e `enviar_evento` podem ser chamadas de código normal ou assíncrono, de
qualquer thread (pedidos da API, o ciclo das regras).
"""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .contrato import Anomalia, Evento

router = APIRouter(tags=["tempo real"])

_ligacoes: set[WebSocket] = set()
_tarefas: set[asyncio.Task] = set()
_loop: asyncio.AbstractEventLoop | None = None


@router.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    global _loop
    _loop = asyncio.get_running_loop()
    await websocket.accept()
    _ligacoes.add(websocket)
    try:
        while True:
            await websocket.receive_text()  # o cliente não envia nada; isto só deteta o fecho
    except WebSocketDisconnect:
        pass
    finally:
        _ligacoes.discard(websocket)


def enviar_anomalia(anomalia: Anomalia) -> None:
    _enviar({"tipo": "anomalia", "anomalia": anomalia.para_json()})


def enviar_evento(evento: Evento) -> None:
    _enviar({"tipo": "evento", "evento": evento.para_json()})


def _enviar(mensagem: dict) -> None:
    loop = _loop
    if loop is None or not _ligacoes:
        return
    texto = json.dumps(mensagem, ensure_ascii=False)
    try:
        atual = asyncio.get_running_loop()
    except RuntimeError:
        atual = None
    if atual is loop:
        tarefa = loop.create_task(_difundir(texto))
        _tarefas.add(tarefa)
        tarefa.add_done_callback(_tarefas.discard)
    else:
        asyncio.run_coroutine_threadsafe(_difundir(texto), loop)


async def _difundir(texto: str) -> None:
    for ligacao in list(_ligacoes):
        try:
            await ligacao.send_text(texto)
        except Exception:
            _ligacoes.discard(ligacao)
