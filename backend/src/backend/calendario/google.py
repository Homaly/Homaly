"""A conversa com a Google: OAuth 2.0 (código de autorização) e a lista de eventos.

Só leitura (`calendar.readonly`). As chaves vêm do `.env`: `GOOGLE_CLIENT_ID`,
`GOOGLE_CLIENT_SECRET` e `GOOGLE_REDIRECT_URI` (o endereço registado na Google Cloud, para onde
a Google devolve a pessoa depois de autorizar).
"""

import base64
import hashlib
import json
import secrets
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import httpx

URL_AUTORIZAR = "https://accounts.google.com/o/oauth2/v2/auth"
URL_TOKEN = "https://oauth2.googleapis.com/token"
URL_REVOGAR = "https://oauth2.googleapis.com/revoke"
URL_EVENTOS = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
PERMISSAO_CALENDARIO = "https://www.googleapis.com/auth/calendar.readonly"
PERMISSOES = f"openid email {PERMISSAO_CALENDARIO}"
REDIRECT_POR_OMISSAO = "http://localhost:8000/calendario/google/retorno"
TIMEOUT_S = 10
MAX_EVENTOS = 250  # por página
MAX_PAGINAS = 4
# Convites que a pessoa ainda não aceitou (ou recusou) não dizem nada sobre a vida dela.
RESPOSTAS_IGNORADAS = {"needsAction", "declined"}


class ErroGoogle(Exception):
    """A Google recusou ou não respondeu; a mensagem diz o quê, sem segredos."""


@dataclass(frozen=True)
class Credenciais:
    client_id: str
    client_secret: str
    redirect_uri: str


@dataclass(frozen=True)
class Ligacao:
    """O que fica depois de autorizar."""

    refresh_token: str
    email: str | None


def credenciais() -> Credenciais | None:
    """As chaves do `.env`, ou `None` se a app não está registada na Google."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not (client_id and client_secret):
        return None
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI") or REDIRECT_POR_OMISSAO
    return Credenciais(client_id, client_secret, redirect_uri)


def novo_verificador() -> str:
    """O segredo do PKCE: fica no servidor; à Google só vai o resumo (`code_challenge`)."""
    return secrets.token_urlsafe(48)


def url_autorizar(c: Credenciais, state: str, verificador: str) -> str:
    """O endereço do "Escolher conta" da Google. `prompt=consent` garante o refresh token."""
    resumo = base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest()).decode().rstrip("=")
    return URL_AUTORIZAR + "?" + urlencode(
        {
            "client_id": c.client_id,
            "redirect_uri": c.redirect_uri,
            "response_type": "code",
            "scope": PERMISSOES,
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
            "code_challenge": resumo,
            "code_challenge_method": "S256",
        }
    )


def trocar_codigo(
    c: Credenciais, codigo: str, verificador: str, *, cliente: httpx.Client | None = None
) -> Ligacao:
    """Troca o código que a Google devolveu por um refresh token e o email da conta.

    Se a pessoa desmarcou "ver os calendários" no ecrã da Google, não liga: revoga e falha.
    """
    dados = _pedir_token(
        c,
        {
            "code": codigo,
            "grant_type": "authorization_code",
            "redirect_uri": c.redirect_uri,
            "code_verifier": verificador,
        },
        cliente,
    )
    refresh = dados.get("refresh_token")
    if not isinstance(refresh, str) or not refresh:
        raise ErroGoogle("a Google não deu acesso contínuo ao calendário")
    if PERMISSAO_CALENDARIO not in str(dados.get("scope", "")).split():
        revogar(refresh, cliente=cliente)
        raise ErroGoogle("a pessoa não deu permissão para ver o calendário")
    return Ligacao(refresh, _email_do_id_token(dados.get("id_token")))


def token_de_acesso(c: Credenciais, refresh_token: str, *, cliente: httpx.Client | None = None) -> str:
    """Um token de acesso novo (dura uma hora) a partir do refresh token."""
    dados = _pedir_token(c, {"refresh_token": refresh_token, "grant_type": "refresh_token"}, cliente)
    token = dados.get("access_token")
    if not isinstance(token, str) or not token:
        raise ErroGoogle("a Google não deu acesso ao calendário")
    return token


def listar_eventos(
    token: str, de: datetime, ate: datetime, *, cliente: httpx.Client | None = None
) -> list[dict]:
    """Os eventos do calendário principal entre `de` e `ate`.

    Os que se repetem vêm uma só vez, com a regra (`recurrence`), e não cada ocorrência. Ficam de
    fora os cancelados e os convites que a pessoa não aceitou.
    """
    parametros = {
        "timeMin": de.isoformat(),
        "timeMax": ate.isoformat(),
        "singleEvents": "false",
        "maxResults": str(MAX_EVENTOS),
    }
    eventos: list[dict] = []
    for _ in range(MAX_PAGINAS):
        pagina = _pagina_de_eventos(token, parametros, cliente)
        eventos += [e for e in pagina.get("items", []) if isinstance(e, dict) and _conta(e)]
        seguinte = pagina.get("nextPageToken")
        if not isinstance(seguinte, str):
            break
        parametros = {**parametros, "pageToken": seguinte}
    return eventos


def _pagina_de_eventos(token: str, parametros: dict, cliente: httpx.Client | None) -> dict:
    try:
        resposta = _cliente(cliente).get(
            URL_EVENTOS,
            params=parametros,
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT_S,
        )
    except httpx.HTTPError as erro:
        raise ErroGoogle(f"o calendário não respondeu ({type(erro).__name__})") from erro
    if resposta.status_code != 200:
        raise ErroGoogle(f"o calendário recusou o pedido ({resposta.status_code})")
    try:
        pagina = resposta.json()
    except ValueError as erro:
        raise ErroGoogle("o calendário respondeu num formato inesperado") from erro
    if not isinstance(pagina, dict):
        raise ErroGoogle("o calendário respondeu num formato inesperado")
    return pagina


def _conta(evento: dict) -> bool:
    """Se o evento diz alguma coisa sobre a pessoa: não está cancelado e, se é um convite, aceitou-o."""
    if evento.get("status") == "cancelled":
        return False
    convidados = evento.get("attendees")
    eu = next((a for a in convidados if isinstance(a, dict) and a.get("self")), None) if isinstance(convidados, list) else None
    return eu is None or eu.get("responseStatus") not in RESPOSTAS_IGNORADAS


def revogar(refresh_token: str, *, cliente: httpx.Client | None = None) -> bool:
    """Tira o acesso da app na conta Google. Se falhar, devolve `False` (quem chama segue)."""
    try:
        resposta = _cliente(cliente).post(URL_REVOGAR, data={"token": refresh_token}, timeout=TIMEOUT_S)
    except httpx.HTTPError:
        return False
    return resposta.status_code == 200


def _cliente(cliente: httpx.Client | None) -> Any:
    """O cliente dos testes, ou o módulo `httpx` (que tem os mesmos `get` e `post`)."""
    return cliente if cliente is not None else httpx


def _pedir_token(c: Credenciais, campos: dict, cliente: httpx.Client | None) -> dict:
    corpo = {"client_id": c.client_id, "client_secret": c.client_secret, **campos}
    try:
        resposta = _cliente(cliente).post(URL_TOKEN, data=corpo, timeout=TIMEOUT_S)
    except httpx.HTTPError as erro:
        raise ErroGoogle(f"a Google não respondeu ({type(erro).__name__})") from erro
    try:
        dados = resposta.json()
    except ValueError:
        dados = {}
    if resposta.status_code != 200 or not isinstance(dados, dict):
        motivo = dados.get("error") if isinstance(dados, dict) else None
        raise ErroGoogle(f"a Google recusou o acesso ({motivo or resposta.status_code})")
    return dados


def _email_do_id_token(id_token: object) -> str | None:
    """O email dentro do `id_token` (veio direto da Google por HTTPS, por isso não se verifica)."""
    if not isinstance(id_token, str) or id_token.count(".") != 2:
        return None
    carga = id_token.split(".")[1]
    try:
        dados = json.loads(base64.urlsafe_b64decode(carga + "=" * (-len(carga) % 4)))
    except ValueError:
        return None
    email = dados.get("email") if isinstance(dados, dict) else None
    return email if isinstance(email, str) else None
