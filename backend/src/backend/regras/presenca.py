"""Onde há alguém em casa: o último movimento visto em cada divisão, pelas câmaras (US14).

Não tem `verificar()`, por isso o ciclo não o corre como regra: é a US14 que o alimenta.

Há uma câmara por sítio. A do kit (`camara`) está dentro de casa, na divisão CAMARA_DIVISAO
(`sala` por omissão), como a US09 já a usa para os sinais de vida. As outras chamam-se
`camara_<divisão>` (ex.: `camara_cozinha`); na demo entram por `/dev/leituras`. A da entrada de
veículos (`camara_entrada`, US13) está lá fora e não diz se há alguém dentro de casa.

Movimento é `motionDetected` com true/on/1. Outro valor não vazio (por exemplo a hora do último
movimento) conta quando muda em relação ao anterior, como em `sinais.py`: o formato do MCP ainda
não foi confirmado (a 2026-11-19 vinha vazio).
"""

from __future__ import annotations

import os
from datetime import datetime

from backend.formatos import Leitura

CAMARA_DO_KIT = "camara"
LA_FORA = {"entrada"}  # divisões cujas câmaras estão fora de casa

_VERDADE = {"true", "on", "1", "yes", "sim"}
_FALSO = {"", "false", "off", "0", "no", "nao", "não", "none"}

_ultimo: dict[str, datetime] = {}  # divisão -> último movimento
_anteriores: dict[str, object] = {}  # câmara -> último valor de motionDetected
_dentro: set[str] = set()  # as câmaras de dentro que já deram leituras


def reiniciar() -> None:
    _ultimo.clear()
    _anteriores.clear()
    _dentro.clear()


def divisao_da_camara(dispositivo: str) -> str | None:
    """A divisão de uma câmara de dentro, ou None se não é câmara ou se está lá fora."""
    if dispositivo == CAMARA_DO_KIT:
        divisao = os.environ.get("CAMARA_DIVISAO", "").strip().lower() or "sala"
    elif dispositivo.startswith(CAMARA_DO_KIT + "_"):
        divisao = dispositivo.removeprefix(CAMARA_DO_KIT + "_").strip().lower()
    else:
        return None
    return None if not divisao or divisao in LA_FORA else divisao


def movimento(valor: object, anterior: object) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return valor != 0
    if valor is None:
        return False
    texto = str(valor).strip().lower()
    if texto in _VERDADE:
        return True
    if texto in _FALSO:
        return False
    return valor != anterior  # uma hora, por exemplo: só conta quando muda


def ver(leituras: list[Leitura], agora: datetime) -> None:
    """Junta o movimento desta volta ao que se sabe de cada divisão."""
    for l in leituras:
        if l.tipo != "motionDetected":
            continue
        divisao = divisao_da_camara(l.dispositivo)
        if divisao is None:
            continue
        _dentro.add(l.dispositivo)
        anterior = _anteriores.get(l.dispositivo)
        _anteriores[l.dispositivo] = l.valor
        if movimento(l.valor, anterior):
            _ultimo[divisao] = agora


def ha_cameras_dentro() -> bool:
    """Alguma câmara de dentro já deu leituras: sem elas, a casa não sabe onde há alguém."""
    return bool(_dentro)


def ultimo_movimento(divisao: str | None = None) -> datetime | None:
    """O último movimento numa divisão, ou em qualquer divisão de dentro (divisao=None)."""
    if divisao is not None:
        return _ultimo.get(divisao.lower())
    return max(_ultimo.values(), default=None)


def onde_desde(desde: datetime, exceto: str) -> list[str]:
    """As outras divisões com movimento desde `desde`."""
    return sorted(d for d, em in _ultimo.items() if d != exceto and em >= desde)
