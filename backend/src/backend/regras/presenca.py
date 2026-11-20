"""Onde há alguém em casa: o último movimento visto em cada divisão, pelas câmaras (US14).

Não tem `verificar()`, por isso o ciclo não o corre como regra: é a US14 que o alimenta.

A divisão de cada câmara vem do inventário (backend.inventario, `dados/dispositivos.csv`), pelo
id do dispositivo; uma câmara sem id, ou fora do inventário, é a do kit, na sala. Só contam as
câmaras interiores: uma exterior (a da entrada de veículos, US13) não diz se há alguém dentro de
casa. Na demo, as câmaras que o kit não tem entram por `/dev/leituras` com o seu id.

O movimento é o de backend.sinais (`sinais.movimento`), a mesma noção para todas as regras.
"""

from __future__ import annotations

from datetime import datetime

from backend import inventario
from backend.formatos import Leitura
from backend.sinais import movimento

__all__ = ["ha_cameras_dentro", "movimento", "onde_desde", "reiniciar", "ultimo_movimento", "ver"]

_ultimo: dict[str, datetime] = {}  # divisão ("a sala") -> último movimento
_anteriores: dict[str, object] = {}  # câmara -> último valor de motionDetected
_dentro: set[str] = set()  # as câmaras de dentro que já deram leituras


def reiniciar() -> None:
    _ultimo.clear()
    _anteriores.clear()
    _dentro.clear()


def ver(leituras: list[Leitura], agora: datetime) -> None:
    """Junta o movimento desta volta ao que se sabe de cada divisão."""
    for l in inventario.com_papel(leituras, "camara", "motionDetected", inventario.INTERIOR):
        camara = inventario.de(l)
        _dentro.add(camara.chave)
        anterior = _anteriores.get(camara.chave)
        _anteriores[camara.chave] = l.valor
        if movimento(l.valor, anterior):
            _ultimo[camara.divisao] = agora


def ha_cameras_dentro() -> bool:
    """Alguma câmara de dentro já deu leituras: sem elas, a casa não sabe onde há alguém."""
    return bool(_dentro)


def ultimo_movimento(divisao: str | None = None) -> datetime | None:
    """O último movimento numa divisão, ou em qualquer divisão de dentro (divisao=None)."""
    if divisao is not None:
        return _ultimo.get(divisao)
    return max(_ultimo.values(), default=None)


def onde_desde(desde: datetime, exceto: str) -> list[str]:
    """As outras divisões com movimento desde `desde`."""
    return sorted(d for d, em in _ultimo.items() if d != exceto and em >= desde)
