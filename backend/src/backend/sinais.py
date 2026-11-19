"""O que é um sinal de vida (US09): algo que só acontece com alguém em casa.

Sinais: movimento ou som na câmara, a lâmpada ligada, desligada ou com o brilho
mudado, a tomada a começar a gastar (passa LIMITE_W) e a porta a abrir (passa a
"alarm"). Um sinal é sempre uma mudança em relação à leitura anterior; sem
leitura anterior não há sinal.

Por confirmar: o formato de motionDetected (a 2026-11-19 vinha ""). Assume-se que
um valor não vazio e diferente do anterior (por exemplo uma hora) é um sinal.
Fica isolado em _camara.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from backend.formatos import Leitura

LIMITE_W = 10.0  # "a gastar": potência acima disto (US14, US09), a afinar

CHAVES: frozenset[tuple[str, str]] = frozenset(
    {
        ("camara", "motionDetected"),
        ("camara", "soundDetected"),
        ("lampada", "power"),
        ("lampada", "brightness"),
        ("tomada", "instantPower"),
        ("porta", "sensorState"),
    }
)

# O estado de partida do histórico.
BASE: dict[tuple[str, str], object] = {
    ("porta", "sensorState"): "normal",
    ("lampada", "power"): "off",
    ("tomada", "instantPower"): 0.0,
    ("camara", "motionDetected"): "",
    ("camara", "soundDetected"): "",
}


@dataclass(frozen=True)
class Sinal:
    dispositivo: str
    descricao: str
    em: datetime


def _camara(valor, anterior) -> bool:
    """Formato por confirmar: um valor não vazio e diferente do anterior."""
    return valor != "" and valor != anterior


def sinal(dispositivo: str, tipo: str, valor, anterior) -> str | None:
    """A descrição do sinal de vida que esta mudança dá, ou None."""
    if anterior is None:
        return None
    if dispositivo == "camara" and tipo == "motionDetected":
        return "movimento na câmara" if _camara(valor, anterior) else None
    if dispositivo == "camara" and tipo == "soundDetected":
        return "som na câmara" if _camara(valor, anterior) else None
    if dispositivo == "lampada" and tipo == "power" and valor != anterior:
        return "a luz ligada" if valor == "on" else "a luz desligada"
    if dispositivo == "lampada" and tipo == "brightness" and valor != anterior:
        return "o brilho da luz mudado"
    if dispositivo == "tomada" and tipo == "instantPower":
        if float(valor) > LIMITE_W and float(anterior) <= LIMITE_W:
            return "a tomada a gastar"
        return None
    if dispositivo == "porta" and tipo == "sensorState":
        if valor == "alarm" and anterior != "alarm":
            return "a porta aberta"
    return None


def comunica(leituras: list[Leitura]) -> bool:
    """Há pelo menos uma leitura de um dispositivo que dá sinais de vida."""
    return any((l.dispositivo, l.tipo) in CHAVES for l in leituras)


class Detetor:
    """Compara cada volta com a anterior e devolve os sinais de vida."""

    def __init__(
        self,
        anteriores: dict[tuple[str, str], object] | None = None,
        comandado: Callable[[str, str], bool] = lambda d, t: False,
    ):
        self.anteriores = dict(anteriores or {})
        self.comandado = comandado

    def ver(self, leituras: list[Leitura]) -> list[Sinal]:
        sinais = []
        for l in leituras:
            chave = (l.dispositivo, l.tipo)
            descricao = sinal(l.dispositivo, l.tipo, l.valor, self.anteriores.get(chave))
            if descricao and not self.comandado(l.dispositivo, l.tipo):
                sinais.append(Sinal(l.dispositivo, descricao, l.em))
            self.anteriores[chave] = l.valor
        return sinais
