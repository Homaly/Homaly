"""Regra de brincar, só para ver o ciclo de ponta a ponta. Apagar quando houver regras reais."""

from __future__ import annotations

from datetime import datetime

from backend.formatos import Contexto, Desvio, Leitura


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio]:
    porta_aberta = any(
        l.dispositivo == "porta" and l.tipo == "sensorState" and l.valor == "alarm" for l in leituras
    )
    if not porta_aberta:
        return []
    return [Desvio(us="BRINCAR", classe="seguranca", resumo="A porta está aberta.", habitual=None)]
