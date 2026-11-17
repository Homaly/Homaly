"""Os formatos partilhados entre as peças do backend (DIVISAO.md, secção 1).

Mudar um destes campos obriga a avisar a equipa toda.
"""

from dataclasses import dataclass
from datetime import datetime, time

from backend.contrato import Classe


@dataclass
class Leitura:
    """O que a ligação ao MCP produz (e o dataset, no mesmo formato)."""

    dispositivo: str  # "porta", "temperatura", "lampada", "tomada", "camara"
    tipo: str  # o type da capability: "sensorState", "temperatureValue", ...
    valor: str | float | bool
    em: datetime  # hora da leitura (do polling), não da mudança


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


@dataclass
class Desvio:
    """O que uma regra produz."""

    us: str  # "US08"
    classe: Classe  # os mesmos valores de contract.ts
    resumo: str  # os factos, em português simples
    habitual: str | None
    imediato: bool = False  # casa vazia: alerta já, a IA não decide


@dataclass(frozen=True)
class Resolucao:
    """Uma regra diz que o problema da sua US acabou, e como.

    `regra.verificar()` devolve-a na volta em que vê o fim (ex.: a porta fechou); o ciclo põe o
    `texto` na `resolucao` da anomalia ativa dessa US, em vez de um texto genérico.
    """

    us: str  # "US08"
    texto: str  # ex.: "a porta fechou às 14:12"
    em: datetime
