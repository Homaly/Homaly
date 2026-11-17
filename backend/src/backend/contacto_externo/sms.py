"""O envio de SMS pelo textbee: um telemóvel Android com a app textbee envia o que o backend pede.

Com `TEXTBEE_API_KEY` no ambiente, `enviar` faz `POST /gateway/send-sms` à API do textbee (e
escolhe o telemóvel com `TEXTBEE_DEVICE_ID`, se houver). Sem a chave, a SMS não sai: fica no
registo e em `GET /dev/sms` (só com `HOMALY_DEV=1`), para se ver o texto.

No máximo `SMS_MAXIMO_HORA` SMS por hora (10 por omissão; 0 tira o limite): a app não tem login,
e quem chegasse à API podia pôr outro número nas Definições e gastar o tarifário do telemóvel.
"""

import logging
import os
import threading
import time
from collections import deque

import httpx
from fastapi import APIRouter

registo = logging.getLogger(__name__)

URL = "https://api.textbee.dev/api/v1/gateway/send-sms"
USER_AGENT = "homaly-backend/0.1"

_trinco = threading.Lock()
_falsas: deque[dict] = deque(maxlen=50)
_enviadas_em: deque[float] = deque()  # as horas (monotónicas) das SMS da última hora
_relogio = time.monotonic  # os testes trocam-no


class ErroSMS(Exception):
    """O textbee não aceitou a SMS (ou não se conseguiu falar com ele)."""


def _http() -> httpx.Client:
    return httpx.Client(timeout=15)


def maximo_hora() -> int:
    texto = os.environ.get("SMS_MAXIMO_HORA", "").strip()
    try:
        return int(texto) if texto else 10
    except ValueError:
        raise ValueError(f"SMS_MAXIMO_HORA tem de ser um número inteiro, não '{texto}'") from None


def _contar_no_limite() -> None:
    """Conta esta SMS; levanta ErroSMS se já se enviaram SMS_MAXIMO_HORA na última hora."""
    maximo = maximo_hora()
    if maximo <= 0:
        return
    agora = _relogio()
    with _trinco:
        while _enviadas_em and agora - _enviadas_em[0] >= 3600:
            _enviadas_em.popleft()
        if len(_enviadas_em) >= maximo:
            raise ErroSMS(f"Chegou-se ao limite de {maximo} SMS por hora (SMS_MAXIMO_HORA)")
        _enviadas_em.append(agora)


def limpar_limite() -> None:
    with _trinco:
        _enviadas_em.clear()


def enviar(para: str, texto: str) -> None:
    """Envia uma SMS para `para` (formato internacional, ex.: +351912345678)."""
    _contar_no_limite()
    chave = os.environ.get("TEXTBEE_API_KEY", "").strip()
    if not chave:
        registo.warning("Sem TEXTBEE_API_KEY: a SMS para %s não saiu:\n%s", para, texto)
        with _trinco:
            _falsas.append({"para": para, "texto": texto})
        return
    corpo: dict = {"recipients": [para], "message": texto}
    telemovel = os.environ.get("TEXTBEE_DEVICE_ID", "").strip()
    if telemovel:
        corpo["deviceId"] = telemovel
    try:
        with _http() as cliente:
            resposta = cliente.post(URL, headers={"x-api-key": chave, "User-Agent": USER_AGENT}, json=corpo)
    except httpx.HTTPError as e:
        # Só o tipo do erro: a mensagem do httpx pode trazer o pedido.
        raise ErroSMS(f"Não foi possível falar com o textbee ({type(e).__name__})") from e
    if resposta.status_code >= 300:
        raise ErroSMS(f"O textbee respondeu {resposta.status_code}")


def falsas() -> list[dict]:
    """As SMS que não saíram por não haver textbee configurado (as mais recentes no fim)."""
    with _trinco:
        return list(_falsas)


def limpar_falsas() -> None:
    with _trinco:
        _falsas.clear()


router = APIRouter(prefix="/dev/sms", tags=["dev"])


@router.get("")
def pedir_falsas() -> list[dict]:
    return falsas()
