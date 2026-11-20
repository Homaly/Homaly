"""O modelo de IA, trocável: quem o usa só conhece `Modelo`.

`IA_FORNECEDOR` escolhe o modelo. `falso` (ou por definir) não usa nenhum: a casa fica com o resumo
do desvio. `groq`, `gemini` e `openrouter` usam a API no formato da OpenAI, com a chave em `GROQ_API_KEY`,
`GEMINI_API_KEY` ou `OPENROUTER_API_KEY`; `IA_MODELO` troca o modelo por omissão do fornecedor.
"""

import json
import logging
import os
from collections.abc import Sequence
from typing import Protocol

import httpx

registo = logging.getLogger(__name__)

TIMEOUT_S = 10  # o ciclo não pode ficar à espera; se falhar, fica o resumo do desvio

# fornecedor: (endpoint, variável da chave, modelo por omissão)
FORNECEDORES = {
    "groq": (
        "https://api.groq.com/openai/v1/chat/completions",
        "GROQ_API_KEY",
        "openai/gpt-oss-120b",
    ),
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "GEMINI_API_KEY",
        "gemini-3.5-flash-lite",
    ),
    "openrouter": (
        "https://openrouter.ai/api/v1/chat/completions",
        "OPENROUTER_API_KEY",
        "anthropic/claude-haiku-5.5",
    ),
}


class Modelo(Protocol):
    def completar_json(
        self, sistema: str, mensagem: str, historico: Sequence[dict[str, str]] = ()
    ) -> dict | None:
        """A resposta do modelo como dicionário, ou `None` se falhou ou não há modelo.

        `historico` são as mensagens anteriores da conversa (`{"role": "user"|"assistant",
        "content": ...}`), que vão entre o sistema e `mensagem`.
        """
        ...


class ModeloFalso:
    def completar_json(
        self, sistema: str, mensagem: str, historico: Sequence[dict[str, str]] = ()
    ) -> dict | None:
        return None


class ModeloOpenAI:
    """Um modelo por trás de uma API no formato da OpenAI (`/chat/completions`), em modo JSON."""

    def __init__(self, url: str, chave: str, modelo: str, *, cliente: httpx.Client | None = None):
        self.url = url
        self.modelo = modelo
        self._chave = chave
        self._cliente = cliente

    def completar_json(
        self, sistema: str, mensagem: str, historico: Sequence[dict[str, str]] = ()
    ) -> dict | None:
        corpo = {
            "model": self.modelo,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": sistema},
                *historico,
                {"role": "user", "content": mensagem},
            ],
        }
        cabecalhos = {
            "Authorization": f"Bearer {self._chave}",
            # o mesmo do MCP: o Cloudflare pode recusar o User-Agent por omissão das bibliotecas
            "User-Agent": "homaly-backend/0.1",
        }
        try:
            pedir = self._cliente.post if self._cliente else httpx.post
            resposta = pedir(self.url, json=corpo, headers=cabecalhos, timeout=TIMEOUT_S)
            resposta.raise_for_status()
            dados = json.loads(resposta.json()["choices"][0]["message"]["content"])
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as erro:
            registo.warning("O modelo %s falhou: %s", self.modelo, erro)
            return None
        return dados if isinstance(dados, dict) else None


def obter_modelo() -> Modelo:
    fornecedor = os.environ.get("IA_FORNECEDOR") or "falso"
    if fornecedor == "falso":
        return ModeloFalso()
    if fornecedor not in FORNECEDORES:
        raise ValueError(f"IA_FORNECEDOR desconhecido: {fornecedor!r}")
    url, variavel, modelo = FORNECEDORES[fornecedor]
    chave = os.environ.get(variavel)
    if not chave:
        raise ValueError(f"IA_FORNECEDOR={fornecedor} precisa de {variavel} no .env")
    return ModeloOpenAI(url, chave, os.environ.get("IA_MODELO") or modelo)
