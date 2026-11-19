"""Compara cada leitura com a anterior e diz o que mudou, como eventos do histórico (US06).

Só a porta, a lâmpada e a tomada (ligado/desligado); a temperatura muda a toda a hora e não gera
eventos. A primeira leitura serve de ponto de partida: depois de um reinício não há evento.
"""

from backend.contrato import Evento
from backend.formatos import Leitura

# (dispositivo, tipo) -> o que dizer para cada valor
VIGIADOS: dict[tuple[str, str], dict[object, str]] = {
    ("porta", "sensorState"): {"alarm": "Abriu", "normal": "Fechou"},
    ("lampada", "power"): {"on": "Acendeu", "off": "Apagou"},
    ("tomada", "power"): {"on": "Ligou", "off": "Desligou"},
    ("agua", "valvula"): {"fechada": "Fechou", "aberta": "Abriu"},
}

NOMES = {"porta": "Porta da rua", "lampada": "Luz da sala", "tomada": "Tomada", "agua": "Válvula da água"}


class Observador:
    def __init__(self) -> None:
        self._anteriores: dict[tuple[str, str], object] = {}

    def ver(self, leituras: list[Leitura]) -> list[Evento]:
        """Os eventos desta leitura em relação à anterior; guarda esta como a nova anterior."""
        atuais = {(l.dispositivo, l.tipo): l for l in leituras if (l.dispositivo, l.tipo) in VIGIADOS}
        novos = [
            Evento(dispositivo=NOMES[chave[0]], descricao=VIGIADOS[chave][l.valor], em=l.em)
            for chave, l in atuais.items()
            if chave in self._anteriores and self._anteriores[chave] != l.valor and l.valor in VIGIADOS[chave]
        ]
        self._anteriores = {**self._anteriores, **{chave: l.valor for chave, l in atuais.items()}}
        return novos
