"""O "habitual" da casa, calculado a partir do histórico simulado (dados/historico.csv).

- Porta: para cada tipo de dia (dias úteis, fim de semana), a primeira e a última
  hora a que a porta abriu no histórico. Uma abertura conta como normal até uma
  hora antes da primeira e uma hora depois da última (US07).
- Tomada: o período seguido mais longo a gastar (acima de LIMITE_W). A US14 avisa
  a partir de três vezes esse período.

A semana de férias do histórico não entra no cálculo: com a casa vazia, a casa
aprenderia que é normal a porta não abrir.
"""

from __future__ import annotations

import csv
import functools
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

HISTORICO = Path(__file__).resolve().parents[2] / "dados" / "historico.csv"

# A semana de férias do histórico simulado (o gerador usa a mesma).
FERIAS_DO_HISTORICO = (date(2026, 11, 2), date(2026, 11, 8))

MARGEM_PORTA = timedelta(hours=1)
LIMITE_W = 10.0  # "a gastar": potência acima disto (US14), a afinar
VEZES_O_HABITUAL = 3  # US14: avisa a partir de 3x o período mais longo do histórico

NOME_DO_TIPO = {"util": "Nos dias úteis", "fim_de_semana": "Ao fim de semana"}


def tipo_de_dia(quando: datetime | date) -> str:
    return "util" if quando.weekday() < 5 else "fim_de_semana"


def duracao(td: timedelta) -> str:
    """'1 h', '1 h 30 min', '45 min'."""
    minutos = round(td.total_seconds() / 60)
    h, m = divmod(minutos, 60)
    if h and m:
        return f"{h} h {m} min"
    return f"{h} h" if h else f"{m} min"


def _minutos(t: time) -> int:
    return t.hour * 60 + t.minute


@dataclass(frozen=True)
class Habitual:
    porta: dict[str, tuple[time, time]]  # tipo de dia -> (primeira, última abertura vistas)
    tomada_max: timedelta  # período seguido mais longo a gastar

    def porta_normal(self, quando: datetime) -> bool:
        janela = self.porta.get(tipo_de_dia(quando))
        if janela is None:
            return False  # nunca abriu neste tipo de dia
        margem = MARGEM_PORTA.total_seconds() / 60
        m = _minutos(quando.time())
        return _minutos(janela[0]) - margem <= m <= _minutos(janela[1]) + margem

    def texto_porta(self, quando: datetime) -> str:
        tipo = tipo_de_dia(quando)
        janela = self.porta.get(tipo)
        if janela is None:
            return f"{NOME_DO_TIPO[tipo]}, a porta nunca abre."
        return f"{NOME_DO_TIPO[tipo]}, a porta costuma abrir entre as {janela[0]:%H:%M} e as {janela[1]:%H:%M}."

    @property
    def limite_tomada(self) -> timedelta:
        return VEZES_O_HABITUAL * self.tomada_max

    def texto_tomada(self) -> str:
        return f"Costuma estar a gastar no máximo {duracao(self.tomada_max)} seguida."


def _nas_ferias(quando: datetime) -> bool:
    return FERIAS_DO_HISTORICO[0] <= quando.date() <= FERIAS_DO_HISTORICO[1]


def carregar(caminho: Path | str = HISTORICO) -> Habitual:
    aberturas: dict[str, list[time]] = {}
    periodos: list[timedelta] = []
    desde: datetime | None = None

    with open(caminho, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            em = datetime.fromisoformat(linha["em"])
            if _nas_ferias(em):
                continue
            if linha["dispositivo"] == "porta" and linha["tipo"] == "sensorState":
                if linha["valor"] == "alarm":
                    aberturas.setdefault(tipo_de_dia(em), []).append(em.time())
            elif linha["dispositivo"] == "tomada" and linha["tipo"] == "instantPower":
                if float(linha["valor"]) > LIMITE_W:
                    desde = desde or em
                elif desde is not None:
                    periodos.append(em - desde)
                    desde = None

    return Habitual(
        porta={tipo: (min(horas), max(horas)) for tipo, horas in aberturas.items()},
        tomada_max=max(periodos, default=timedelta(0)),
    )


@functools.cache
def padrao() -> Habitual:
    """O habitual de dados/historico.csv, lido uma só vez."""
    return carregar()
