"""Cliente do servidor MCP da Altice: token no Keycloak, sessão MCP e chamada de ferramentas.

Síncrono, com `httpx`. O servidor responde em `text/event-stream` (streamable HTTP, protocolo
2025-06-18) e está atrás do Cloudflare, que recusa (403) o User-Agent por omissão das bibliotecas.

- Token: `grant_type=password`, como `scripts/mcp_headers.sh`. Guarda-se até 60 s antes de expirar;
  se o servidor responder 401, pede-se outro e repete-se uma vez.
- Sessão: `initialize` na primeira chamada; se o servidor a der por desconhecida (404), abre-se
  outra e repete-se uma vez. Um 400 é um erro do pedido e não se repete.
- Qualquer falha (rede, servidor, ferramenta, resposta que não se percebe) levanta
  `ErroDispositivos`, para o ciclo poder saltar essa volta.
"""

from __future__ import annotations

import itertools
import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

USER_AGENT = "homaly-backend/0.1"
PROTOCOLO = "2025-06-18"
REALM = "smarthome-prd-beta-app"
MARGEM_TOKEN_S = 60

_VARIAVEIS = {
    "url": "MCP_URL",
    "client_id": "MCP_CLIENT_ID",
    "client_type": "MCP_CLIENT_TYPE",
    "api_key": "MCP_API_KEY",
    "utilizador": "KEYCLOAK_USER",
    "palavra_passe": "KEYCLOAK_PASSWORD",
}


class ErroDispositivos(Exception):
    """Não foi possível falar com o servidor MCP ou a ferramenta falhou."""


@dataclass(frozen=True)
class Config:
    url: str
    client_id: str
    client_type: str
    api_key: str
    utilizador: str
    palavra_passe: str

    @classmethod
    def do_ambiente(cls) -> Config:
        """Lê os valores do ambiente (o `.env`, pelo docker-compose)."""
        valores = {campo: os.environ.get(var, "").strip() for campo, var in _VARIAVEIS.items()}
        faltam = [_VARIAVEIS[campo] for campo, v in valores.items() if not v]
        if faltam:
            raise ErroDispositivos(f"Faltam variáveis do MCP no ambiente: {', '.join(faltam)}")
        valores["url"] = valores["url"].rstrip("/")
        return cls(**valores)


class _Repetir(Exception):
    """O servidor recusou o token ou a sessão; vale a pena repetir uma vez."""


class ClienteMCP:
    def __init__(self, config: Config, http: httpx.Client | None = None) -> None:
        self._config = config
        self._http = http or httpx.Client(timeout=20)
        self._ids = itertools.count(1)
        self._trinco = threading.Lock()
        self._token: str | None = None
        self._token_ate = 0.0
        self._sessao: str | None = None

    def chamar(self, ferramenta: str, argumentos: dict | None = None) -> dict:
        """Chama uma ferramenta do MCP e devolve o JSON do resultado."""
        with self._trinco:
            try:
                try:
                    return self._chamar(ferramenta, argumentos or {})
                except _Repetir:
                    return self._chamar(ferramenta, argumentos or {})
            except _Repetir as e:
                raise ErroDispositivos(f"O MCP recusou {ferramenta} duas vezes: {e}") from e
            except httpx.HTTPError as e:
                raise ErroDispositivos(f"Falha a falar com o MCP ({ferramenta}): {e}") from e
            except (ValueError, KeyError, TypeError, AttributeError) as e:
                # Uma resposta com um formato inesperado; nunca deve parar o ciclo.
                raise ErroDispositivos(f"Resposta do MCP que não se percebe ({ferramenta}): {e!r}") from e

    def _chamar(self, ferramenta: str, argumentos: dict) -> dict:
        if self._sessao is None:
            self._iniciar()
        resposta = self._rpc("tools/call", {"name": ferramenta, "arguments": argumentos})
        return _conteudo(ferramenta, resposta)

    def _iniciar(self) -> None:
        params = {
            "protocolVersion": PROTOCOLO,
            "capabilities": {},
            "clientInfo": {"name": "homaly-backend", "version": "0.1"},
        }
        r = self._post({"jsonrpc": "2.0", "id": next(self._ids), "method": "initialize", "params": params})
        _verificar(r, "initialize")
        self._sessao = r.headers.get("mcp-session-id")
        aviso = self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        _verificar(aviso, "notifications/initialized")

    def _rpc(self, metodo: str, params: dict) -> dict:
        id_pedido = next(self._ids)
        r = self._post({"jsonrpc": "2.0", "id": id_pedido, "method": metodo, "params": params})
        _verificar(r, metodo)
        mensagem = _mensagem(r, id_pedido)
        if "error" in mensagem:
            raise ErroDispositivos(f"O MCP devolveu um erro em {metodo}: {mensagem['error'].get('message')}")
        return mensagem.get("result", {})

    def _post(self, corpo: dict) -> httpx.Response:
        cabecalhos = {
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {self._obter_token()}",
            "X-API-Key": self._config.api_key,
            "X-Client-Type": self._config.client_type,
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self._sessao:
            cabecalhos["Mcp-Session-Id"] = self._sessao
            cabecalhos["MCP-Protocol-Version"] = PROTOCOLO
        r = self._http.post(self._config.url + "/", headers=cabecalhos, json=corpo)
        if r.status_code == 401:
            self._token = None
            self._sessao = None
            raise _Repetir("token recusado (401)")
        if r.status_code == 404 and self._sessao and corpo.get("method") != "initialize":
            self._sessao = None
            raise _Repetir("sessão desconhecida (404)")
        return r

    def _obter_token(self) -> str:
        if self._token and time.monotonic() < self._token_ate:
            return self._token
        c = self._config
        r = self._http.post(
            f"{c.url}/realms/{REALM}/protocol/openid-connect/token",
            headers={"User-Agent": USER_AGENT},
            data={
                "grant_type": "password",
                "client_id": c.client_id,
                "username": c.utilizador,
                "password": c.palavra_passe,
                "scope": "openid connected-home-attributes",
            },
        )
        if r.status_code != 200:
            raise ErroDispositivos(f"O Keycloak recusou o login ({r.status_code})")
        try:
            dados = r.json()
            token = dados["access_token"]
            validade = int(dados.get("expires_in", 300))
        except (ValueError, KeyError, TypeError) as e:
            raise ErroDispositivos("O Keycloak respondeu sem um token que se perceba") from e
        self._token = token
        self._token_ate = time.monotonic() + max(0, validade - MARGEM_TOKEN_S)
        return token


def _verificar(r: httpx.Response, metodo: str) -> None:
    if r.status_code not in (200, 202):
        raise ErroDispositivos(f"O MCP respondeu {r.status_code} a {metodo}")


def _mensagem(r: httpx.Response, id_pedido: int) -> dict[str, Any]:
    """A resposta JSON-RPC ao pedido `id_pedido`, venha em JSON ou em stream (SSE)."""
    tipo = r.headers.get("content-type", "")
    if "text/event-stream" in tipo:
        mensagens = [json.loads(dados) for dados in _eventos_sse(r.text)]
    elif "json" in tipo:
        corpo = r.json()
        mensagens = corpo if isinstance(corpo, list) else [corpo]
    else:
        raise ErroDispositivos(f"O MCP respondeu com {tipo or 'um tipo desconhecido'} em vez de JSON")
    respostas = [
        m for m in mensagens if isinstance(m, dict) and m.get("id") == id_pedido and ("result" in m or "error" in m)
    ]
    if not respostas:
        raise ErroDispositivos("O MCP respondeu sem resultado")
    return respostas[-1]


def _eventos_sse(texto: str) -> list[str]:
    """Os dados de cada evento do stream: as linhas `data:` de um evento juntam-se com '\\n'."""
    eventos: list[str] = []
    atual: list[str] = []
    for linha in texto.splitlines() + [""]:
        if not linha:
            if atual:
                eventos.append("\n".join(atual))
            atual = []
        elif linha.startswith("data:"):
            atual.append(linha[5:].removeprefix(" "))
    return eventos


def _conteudo(ferramenta: str, resultado: dict) -> dict:
    textos = [c.get("text", "") for c in resultado.get("content", []) if c.get("type") == "text"]
    if resultado.get("isError"):
        raise ErroDispositivos(f"A ferramenta {ferramenta} falhou: {' '.join(textos)}")
    if isinstance(resultado.get("structuredContent"), dict):
        return resultado["structuredContent"]
    if not textos:
        return {}
    try:
        dados = json.loads(textos[0])
    except json.JSONDecodeError:
        return {"texto": textos[0]}
    return dados if isinstance(dados, dict) else {"dados": dados}
