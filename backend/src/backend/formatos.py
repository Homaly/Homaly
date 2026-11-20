"""Os formatos partilhados entre as peças do backend (DIVISAO.md, secção 1).

Mudar um destes campos obriga a avisar a equipa toda.
"""

from dataclasses import dataclass, field
from datetime import datetime, time

from backend.contrato import Classe


@dataclass
class Leitura:
    """O que a ligação ao MCP produz (e o dataset, no mesmo formato)."""

    dispositivo: str  # "porta", "temperatura", "lampada", "tomada", "camara"
    tipo: str  # o type da capability: "sensorState", "temperatureValue", ...
    valor: str | float | bool
    em: datetime  # hora da leitura (do polling), não da mudança
    # O id do dispositivo no MCP. Vazio nos CSV e nas leituras injetadas sem id: é "o" dispositivo
    # desse tipo. A divisão e o papel de cada um estão no inventário (backend.inventario).
    id: str = ""


@dataclass
class Periodo:
    """Férias ditas à casa."""

    inicio: datetime
    fim: datetime
    motivo: str


@dataclass
class Rotina:
    """Ex.: "a empregada vem às terças"."""

    descricao: str
    dias: list[int]  # 0 = segunda
    hora: time | None


@dataclass
class Compromisso:
    """Um evento de um dia, vindo do calendário (ex.: "Dentista", das 15:00 às 16:00)."""

    descricao: str
    inicio: datetime
    fim: datetime


@dataclass
class Silencio:
    """Resposta a uma anomalia (US02)."""

    us: str
    ate: datetime | None  # None: até ser removido
    motivo: str


@dataclass
class Contexto:
    """O que o responsável disse à casa (US01, US02)."""

    ferias: list[Periodo]
    rotinas: list[Rotina]
    silencios: list[Silencio]
    casa_vazia: bool
    aparelho_tomada: str | None = None  # o aparelho dito na conversa (US14)
    compromissos: list[Compromisso] = field(default_factory=list)  # os de hoje, do calendário


@dataclass
class Desvio:
    """O que uma regra produz."""

    us: str  # "US08"
    classe: Classe  # os mesmos valores de contract.ts
    resumo: str  # os factos, em português simples
    habitual: str | None
    imediato: bool = False  # casa vazia: alerta já, a IA não decide
    # O id do MCP do dispositivo de que o desvio fala (ex.: a lâmpada da US11), quando a regra o
    # sabe: a ação da US03 muda esse dispositivo, e não "o" dispositivo desse tipo. "" sem id.
    dispositivo: str = ""
    # A imagem que mostra o desvio ("/imagens/<id>.jpg", backend.camara), quando há uma (US13): o
    # ciclo põe-na na `imagemUrl` da anomalia.
    imagem: str | None = None


@dataclass(frozen=True)
class Resolucao:
    """Uma regra diz que o problema da sua US acabou, e como.

    `regra.verificar()` devolve-a na volta em que vê o fim (ex.: a porta fechou); o ciclo põe o
    `texto` na `resolucao` da anomalia ativa dessa US, em vez de um texto genérico.
    """

    us: str  # "US08"
    texto: str  # ex.: "a porta fechou às 14:12"
    em: datetime
