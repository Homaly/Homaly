"""O "habitual" da casa, calculado a partir do histórico simulado (dados/historico.csv).

- Porta: para cada tipo de dia (dias úteis, fim de semana), a primeira e a última
  hora a que a porta abriu no histórico. Uma abertura conta como normal até uma
  hora antes da primeira e uma hora depois da última (US07).
- Sinais de vida (US09, backend.sinais): o histórico passa por um Detetor, como as
  leituras ao vivo. Para cada tipo de dia, o primeiro sinal do dia mais tardio (o
  primeiro de cada dia, e desses o mais tardio): a US09 avisa se ainda não houve
  nenhum MARGEM_US09 depois disso. E as horas com atividade: as horas (0–23) com
  sinais em pelo menos ATIVIDADE_FRACAO dos dias desse tipo com sinais. Só o tempo
  nessas horas conta como silêncio (dormir não é "a atividade parou").
- Porta, de manhã (a US09 antiga, até a regra nova a substituir): para cada tipo de
  dia, a primeira abertura mais tardia; a regra avisa se a porta ainda não abriu
  _MARGEM_PORTA_US09 depois disso.
- Tomada: o período seguido mais longo a gastar (acima de LIMITE_W). A US14 avisa
  a partir de três vezes esse período.

A semana de férias do histórico não entra no cálculo: com a casa vazia, a casa
aprenderia que é normal a porta não abrir e não haver sinais.

Afinação (backend.afinacao, 2026-11-17): cada semana do histórico, passada pelas regras
com o habitual das outras, dá 0 falsos alarmes com estes valores. Folgas mais curtas:
US07 25 min, US14 2 h, US09 0 min (um sábado abriu às 11:00, com o limite dessa
semana nas 11:00). A margem da US09 da porta (30 min) foi decidida assim. A dos sinais
de vida (1 h 30) é a do exemplo da spec (habitual antes das 9h, limite às 10h30) e
ATIVIDADE_FRACAO um primeiro valor: ambos a afinar.
"""

from __future__ import annotations

import csv
import functools
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Container

from backend.formatos import Leitura
from backend.sinais import BASE, LIMITE_W, Detetor, Sinal  # LIMITE_W também é lido pela US14

HISTORICO = Path(__file__).resolve().parents[2] / "dados" / "historico.csv"

# A semana de férias do histórico simulado (o gerador usa a mesma).
FERIAS_DO_HISTORICO = (date(2026, 11, 2), date(2026, 11, 8))

MARGEM_PORTA = timedelta(hours=1)
MARGEM_US09 = timedelta(hours=1, minutes=30)  # depois do primeiro sinal habitual
ATIVIDADE_FRACAO = 0.25  # uma hora tem atividade se teve sinais em 1/4 dos dias
_MARGEM_PORTA_US09 = timedelta(minutes=30)  # a US09 da porta; sai quando a regra for reescrita
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
    primeira_abertura: dict[str, time]  # tipo de dia -> a primeira abertura do dia mais tardia
    primeiro_sinal: dict[str, time]  # tipo de dia -> o primeiro sinal de vida do dia mais tardio
    atividade: dict[str, frozenset[int]]  # tipo de dia -> as horas (0–23) com atividade

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

    def limite_porta_nao_abriu(self, quando: datetime | date) -> time | None:
        """US09: a hora a partir da qual a porta já devia ter aberto; None se nunca abre nesse tipo de dia."""
        primeira = self.primeira_abertura.get(tipo_de_dia(quando))
        if primeira is None:
            return None
        return (datetime.combine(date.min, primeira) + _MARGEM_PORTA_US09).time()

    def texto_primeira_abertura(self, quando: datetime | date) -> str:
        tipo = tipo_de_dia(quando)
        primeira = self.primeira_abertura.get(tipo)
        if primeira is None:
            return f"{NOME_DO_TIPO[tipo]}, a porta nunca abre."
        return f"{NOME_DO_TIPO[tipo]}, a porta costuma abrir pela primeira vez até às {primeira:%H:%M}."

    def limite_sem_sinais(self, quando: datetime | date) -> time | None:
        """US09: a hora a partir da qual já devia ter havido um sinal de vida; None se esse
        tipo de dia nunca tem sinais."""
        primeiro = self.primeiro_sinal.get(tipo_de_dia(quando))
        if primeiro is None:
            return None
        return (datetime.combine(date.min, primeiro) + MARGEM_US09).time()

    def texto_primeiro_sinal(self, quando: datetime | date) -> str:
        tipo = tipo_de_dia(quando)
        primeiro = self.primeiro_sinal.get(tipo)
        if primeiro is None:
            return f"{NOME_DO_TIPO[tipo]}, não costuma haver sinais de vida."
        return f"{NOME_DO_TIPO[tipo]}, o primeiro sinal de vida costuma chegar até às {primeiro:%H:%M}."

    def com_atividade(self, quando: datetime) -> bool:
        return quando.hour in self.atividade.get(tipo_de_dia(quando), frozenset())

    def tempo_ativo(self, desde: datetime, ate: datetime) -> timedelta:
        """A parte de [desde, ate] que cai em horas com atividade (cada hora pelo tipo do seu dia)."""
        total = timedelta(0)
        inicio = desde.replace(minute=0, second=0, microsecond=0)
        while inicio < ate:
            fim = inicio + timedelta(hours=1)
            if self.com_atividade(inicio):
                total += max(min(fim, ate) - max(inicio, desde), timedelta(0))
            inicio = fim
        return total

    def texto_atividade(self, quando: datetime | date) -> str:
        tipo = tipo_de_dia(quando)
        horas = sorted(self.atividade.get(tipo, ()))
        if not horas:
            return f"{NOME_DO_TIPO[tipo]}, não costuma haver atividade."
        intervalos: list[list[int]] = []
        for h in horas:
            if intervalos and intervalos[-1][1] == h:
                intervalos[-1][1] = h + 1
            else:
                intervalos.append([h, h + 1])
        partes = [f"das {a:02d}:00 às {b:02d}:00" for a, b in intervalos]
        juntas = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " e " + partes[-1]
        return f"{NOME_DO_TIPO[tipo]}, costuma haver atividade {juntas}."

    @property
    def limite_tomada(self) -> timedelta:
        return VEZES_O_HABITUAL * self.tomada_max

    def texto_tomada(self) -> str:
        return f"Costuma estar a gastar no máximo {duracao(self.tomada_max)} de seguida."


def _nas_ferias(quando: datetime) -> bool:
    return FERIAS_DO_HISTORICO[0] <= quando.date() <= FERIAS_DO_HISTORICO[1]


def _fora(em: datetime, excluir: Container[date]) -> bool:
    return _nas_ferias(em) or em.date() in excluir


def sinais_de_vida(caminho: Path | str = HISTORICO, excluir: Container[date] = ()) -> list[Sinal]:
    """Os sinais de vida do histórico, sem a semana de férias nem os dias em excluir.

    Todas as linhas passam pelo Detetor (a partir de BASE), uma de cada vez, para o
    valor anterior estar certo também a seguir a um dia que não conta."""
    detetor = Detetor(anteriores=BASE)
    sinais: list[Sinal] = []
    with open(caminho, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            em = datetime.fromisoformat(linha["em"])
            leitura = Leitura(linha["dispositivo"], linha["tipo"], linha["valor"], em)
            sinais += [s for s in detetor.ver([leitura]) if not _fora(s.em, excluir)]
    return sinais


def _primeiro_sinal_e_atividade(sinais: list[Sinal]) -> tuple[dict[str, time], dict[str, frozenset[int]]]:
    primeiros: dict[date, time] = {}
    horas_por_dia: dict[date, set[int]] = {}
    for s in sinais:
        primeiros.setdefault(s.em.date(), s.em.time())
        horas_por_dia.setdefault(s.em.date(), set()).add(s.em.hour)

    primeiro_sinal: dict[str, time] = {}
    atividade: dict[str, frozenset[int]] = {}
    for tipo in {tipo_de_dia(d) for d in primeiros}:
        dias = [d for d in primeiros if tipo_de_dia(d) == tipo]
        primeiro_sinal[tipo] = max(primeiros[d] for d in dias)
        atividade[tipo] = frozenset(
            h for h in range(24)
            if sum(h in horas_por_dia[d] for d in dias) >= ATIVIDADE_FRACAO * len(dias)
        )
    return primeiro_sinal, atividade


def carregar(caminho: Path | str = HISTORICO, excluir: Container[date] = ()) -> Habitual:
    """O habitual do ficheiro. Os dias em excluir não contam (a afinação usa-o para
    testar uma semana com o habitual das outras)."""
    aberturas: dict[str, list[time]] = {}
    primeiras: dict[date, time] = {}
    periodos: list[timedelta] = []
    desde: datetime | None = None

    with open(caminho, newline="", encoding="utf-8") as f:
        for linha in csv.DictReader(f):
            em = datetime.fromisoformat(linha["em"])
            if _fora(em, excluir):
                continue
            if linha["dispositivo"] == "porta" and linha["tipo"] == "sensorState":
                if linha["valor"] == "alarm":
                    aberturas.setdefault(tipo_de_dia(em), []).append(em.time())
                    primeiras.setdefault(em.date(), em.time())
            elif linha["dispositivo"] == "tomada" and linha["tipo"] == "instantPower":
                if float(linha["valor"]) > LIMITE_W:
                    desde = desde or em
                elif desde is not None:
                    periodos.append(em - desde)
                    desde = None

    primeiro_sinal, atividade = _primeiro_sinal_e_atividade(sinais_de_vida(caminho, excluir))
    return Habitual(
        porta={tipo: (min(horas), max(horas)) for tipo, horas in aberturas.items()},
        tomada_max=max(periodos, default=timedelta(0)),
        primeira_abertura={
            tipo: max(t for d, t in primeiras.items() if tipo_de_dia(d) == tipo)
            for tipo in {tipo_de_dia(d) for d in primeiras}
        },
        primeiro_sinal=primeiro_sinal,
        atividade=atividade,
    )


@functools.cache
def padrao() -> Habitual:
    """O habitual de dados/historico.csv, lido uma só vez."""
    return carregar()
