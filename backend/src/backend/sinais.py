"""O que é um sinal de vida (US09): algo que só acontece com alguém em casa.

Sinais: movimento ou som na câmara, a lâmpada ligada, desligada ou com o brilho
mudado, a tomada a começar a gastar (passa LIMITE_W) e a porta a abrir (passa a
"alarm"). Um sinal é sempre uma mudança em relação à leitura anterior; sem
leitura anterior não há sinal.

Por confirmar: o formato de motionDetected (a 2026-11-19 vinha ""). `movimento` aceita os
dois formatos possíveis: true/on/1 é movimento agora e false/off/vazio não é; outro valor (por
exemplo a hora do último movimento) conta quando muda em relação ao anterior. É a mesma noção
de movimento para todas as regras (US09, US14, a saída de casa).

Com vários dispositivos do mesmo tipo (várias câmaras), cada um compara-se com a sua leitura
anterior: a chave é o id do dispositivo (ou o tipo, numa leitura sem id). Só contam os que vêem
dentro de casa (backend.inventario.conta_como_casa): uma câmara exterior vê quem passa na rua e
uma janela a abrir não é a porta da rua.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from backend import inventario
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

# O estado de partida do histórico (leituras sem id: a chave é o tipo do dispositivo).
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


_VERDADE = {"true", "on", "1", "yes", "sim"}
_FALSO = {"", "false", "off", "0", "no", "nao", "não", "none"}


def movimento(valor: object, anterior: object) -> bool:
    """Se este valor de motionDetected (ou soundDetected) quer dizer que a câmara viu alguém."""
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


def sinal(dispositivo: str, tipo: str, valor, anterior) -> str | None:
    """A descrição do sinal de vida que esta mudança dá, ou None."""
    if anterior is None:
        return None
    if dispositivo == "camara" and tipo == "motionDetected":
        return "movimento na câmara" if movimento(valor, anterior) else None
    if dispositivo == "camara" and tipo == "soundDetected":
        return "som na câmara" if movimento(valor, anterior) else None
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
    return any(_conta(l) for l in leituras)


def _conta(leitura: Leitura) -> bool:
    return (leitura.dispositivo, leitura.tipo) in CHAVES and inventario.conta_como_casa(leitura)


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
            if not _conta(l):
                continue
            chave = (inventario.chave(l), l.tipo)
            descricao = sinal(l.dispositivo, l.tipo, l.valor, self.anteriores.get(chave))
            if descricao and not self.comandado(l.dispositivo, l.tipo):
                sinais.append(Sinal(l.dispositivo, descricao, l.em))
            self.anteriores[chave] = l.valor
        return sinais
