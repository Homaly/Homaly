"""Ajudas partilhadas pelas regras. Não tem `verificar()`, por isso o ciclo não o corre."""

import os
from datetime import datetime

from backend.formatos import Leitura


def ultima(leituras: list[Leitura], dispositivo: str, tipo: str) -> str | float | bool | None:
    """O valor mais recente de um dispositivo nesta volta, ou None se não veio."""
    valores = [l.valor for l in leituras if l.dispositivo == dispositivo and l.tipo == tipo]
    return valores[-1] if valores else None


def numero(variavel: str, omissao: float) -> float:
    """Um limite configurável no ambiente (ex.: PORTA_MINUTOS=1 na demo)."""
    texto = os.environ.get(variavel, "").strip()
    if not texto:
        return omissao
    try:
        return float(texto)
    except ValueError:
        raise ValueError(f"{variavel} tem de ser um número, não '{texto}'") from None


def graus(valor: float) -> str:
    """15.4 -> '15,4 °C'; 16.0 -> '16 °C'."""
    return f"{decimal(valor)} °C"


def decimal(valor: float) -> str:
    texto = f"{valor:.1f}".replace(".", ",")
    return texto.removesuffix(",0")


def com_fuso(momento: datetime) -> datetime:
    """Uma hora sem fuso é tomada como hora local, como em `contrato.py`."""
    return momento if momento.tzinfo else momento.astimezone()


def hora(momento: datetime) -> str:
    return f"{momento:%H:%M}"
