"""O texto das SMS ao contacto externo (US05).

    Homaly - Casa da D. Maria
    Alerta de segurança às 14:05:
    A porta da rua está aberta há mais de 5 minutos, desde as 14:00.
    Ver: http://192.168.1.20:8000/a/kX9...

    Homaly - Casa da D. Maria
    Resolvido às 14:12: a porta fechou às 14:12.
    Ver: http://192.168.1.20:8000/a/kX9...
"""

import os
from datetime import datetime

from backend.contrato import Anomalia

ROTULOS = {"seguranca": "Alerta de segurança", "bem_estar": "Alerta de bem-estar"}
MAXIMO_EXPLICACAO = 300  # a SMS com acentos parte-se em pedaços de 67 carateres
SEM_TEXTO = "o responsável tratou do assunto"


def url_publico() -> str:
    """O início do link, que o telemóvel do contacto tem de alcançar (HOMALY_URL_PUBLICO)."""
    return (os.environ.get("HOMALY_URL_PUBLICO", "").strip() or "http://localhost:8000").rstrip("/")


def link(codigo: str) -> str:
    return f"{url_publico()}/a/{codigo}"


def hora(momento: datetime) -> str:
    return f"{momento.astimezone():%H:%M}"


def cabecalho(nome_casa: str | None) -> str:
    return f"Homaly - {nome_casa}" if nome_casa else "Homaly"


def alerta(anomalia: Anomalia, nome_casa: str | None, codigo: str) -> str:
    rotulo = ROTULOS.get(anomalia.classe, "Alerta")
    return "\n".join(
        [
            cabecalho(nome_casa),
            f"{rotulo} às {hora(anomalia.detetada_em)}:",
            _curto(anomalia.explicacao),
            f"Ver: {link(codigo)}",
        ]
    )


def resolvido(anomalia: Anomalia, nome_casa: str | None, codigo: str, resolvida_em: datetime) -> str:
    texto = anomalia.resolucao.texto if anomalia.resolucao else SEM_TEXTO
    # A hora da anomalia (a simulada, com o relógio acelerado); `resolvida_em` é a real.
    if anomalia.resolucao:
        quando = anomalia.resolucao.em
    elif anomalia.resposta:
        quando = anomalia.resposta.em
    else:
        quando = resolvida_em
    return "\n".join(
        [
            cabecalho(nome_casa),
            f"Resolvido às {hora(quando)}: {_com_ponto(texto)}",
            f"Ver: {link(codigo)}",
        ]
    )


def _curto(texto: str) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= MAXIMO_EXPLICACAO else texto[: MAXIMO_EXPLICACAO - 1].rstrip() + "…"


def _com_ponto(texto: str) -> str:
    texto = texto.strip()
    return texto if texto.endswith((".", "!", "?", "…")) else texto + "."
