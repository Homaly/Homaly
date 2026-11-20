"""Compara cada leitura com a anterior e diz o que mudou, como eventos do histórico (US06).

Só a porta, a lâmpada e a tomada (ligado/desligado); a temperatura muda a toda a hora e não gera
eventos. A primeira leitura serve de ponto de partida: depois de um reinício não há evento.

Cada dispositivo compara-se com a sua leitura anterior (a casa pode ter várias janelas, várias
lâmpadas), e o evento leva o nome que o inventário lhe dá ("Janela do quarto").
"""

from backend import inventario
from backend.contrato import Evento
from backend.formatos import Leitura

# (dispositivo, tipo) -> o que dizer para cada valor
VIGIADOS: dict[tuple[str, str], dict[object, str]] = {
    ("porta", "sensorState"): {"alarm": "Abriu", "normal": "Fechou"},
    ("lampada", "power"): {"on": "Acendeu", "off": "Apagou"},
    ("tomada", "power"): {"on": "Ligou", "off": "Desligou"},
    ("agua", "valvula"): {"fechada": "Fechou", "aberta": "Abriu"},
}


class Observador:
    def __init__(self) -> None:
        self._anteriores: dict[tuple[str, str], object] = {}  # (chave do dispositivo, tipo) -> valor

    def ver(self, leituras: list[Leitura]) -> list[Evento]:
        """Os eventos desta leitura em relação à anterior; guarda esta como a nova anterior."""
        atuais = {
            (inventario.chave(l), l.tipo): l for l in leituras if (l.dispositivo, l.tipo) in VIGIADOS
        }
        novos = [
            Evento(dispositivo=inventario.de(l).nome, descricao=frases[l.valor], em=l.em)
            for chave, l in atuais.items()
            if chave in self._anteriores
            and self._anteriores[chave] != l.valor
            and l.valor in (frases := VIGIADOS[(l.dispositivo, l.tipo)])
        ]
        self._anteriores = {**self._anteriores, **{chave: l.valor for chave, l in atuais.items()}}
        return novos
