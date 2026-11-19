"""Afinar os limites com o histórico: num histórico normal, cada aviso é um falso alarme.

Validação por semanas: para cada bloco de sete dias do histórico, o habitual calcula-se
com os outros dias e o bloco passa pelo Ciclo real com as regras da US07, US09 e US14.
O contexto leva a semana de férias do histórico (a casa sabe que esteve vazia).

O historico.csv só tem mudanças; aqui faz-se um polling a cada POLLING (com o último
estado) e outro em cada mudança, para a US09 chegar à hora limite e nenhuma abertura
de um minuto se perder.

Uso: uv run python scripts/afinar.py
"""

from __future__ import annotations

import contextlib
import csv
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterator

from backend import habitual, sinais
from backend.ciclo import Ciclo, correr
from backend.contrato import Anomalia
from backend.formatos import Contexto, Leitura, Periodo
from backend.regras import us07, us09, us14

POLLING = timedelta(minutes=10)
REGRAS = (us07, us09, us14)

FERIAS = Periodo(
    datetime.combine(habitual.FERIAS_DO_HISTORICO[0], time.min),
    datetime.combine(habitual.FERIAS_DO_HISTORICO[1], time.max),
    "férias do histórico",
)


def _mudancas(caminho: Path) -> list[tuple[datetime, str, str, str]]:
    """As mudanças do histórico: (quando, dispositivo, tipo, valor)."""
    with open(caminho, newline="", encoding="utf-8") as f:
        return [(datetime.fromisoformat(l["em"]), l["dispositivo"], l["tipo"], l["valor"])
                for l in csv.DictReader(f)]


def pollings(mudancas: list[tuple[datetime, str, str, str]], dias: list[date]) -> Iterator[tuple[datetime, list[Leitura]]]:
    """Um polling a cada POLLING e em cada mudança, nos dias dados, com o último estado
    de cada (dispositivo, tipo) do histórico, partindo de sinais.BASE."""
    inicio = datetime.combine(dias[0], time.min)
    fim = datetime.combine(dias[-1], time.max)
    momentos = {m for m, *_ in mudancas if inicio <= m <= fim}
    t = inicio
    while t <= fim:
        momentos.add(t)
        t += POLLING
    estado = dict(sinais.BASE)
    i = 0
    for agora in sorted(momentos):
        while i < len(mudancas):
            em, dispositivo, tipo, valor = mudancas[i]
            if em > agora:
                break
            estado[(dispositivo, tipo)] = float(valor) if (dispositivo, tipo) == ("tomada", "instantPower") else valor
            i += 1
        yield agora, [Leitura(d, t, v, agora) for (d, t), v in estado.items()]


@contextlib.contextmanager
def _com_habitual(h: habitual.Habitual):
    """As regras leem habitual.padrao(); aqui troca-se pelo habitual do bloco."""
    original = habitual.padrao
    habitual.padrao = lambda: h  # type: ignore[assignment]
    try:
        yield
    finally:
        habitual.padrao = original  # type: ignore[assignment]


def avisos_em(h: habitual.Habitual, mudancas, dias: list[date]) -> list[tuple[datetime, str, str]]:
    """Os desvios que chegam à IA ao passar estes dias pelas regras: (quando, us, resumo)."""
    for regra in REGRAS:
        regra.reiniciar()
    vistos: list[tuple[datetime, str, str]] = []
    passo: list[datetime] = []

    def avaliar(desvio, contexto):
        vistos.append((passo[0], desvio.us, desvio.resumo))
        return Anomalia(id=str(len(vistos)), classe=desvio.classe, titulo="", explicacao="", detetada_em=passo[0])

    ciclo = Ciclo(
        regras=[r.verificar for r in REGRAS],
        avaliar=avaliar,
        publicar=lambda a: None,
        obter_contexto=lambda: Contexto(ferias=[FERIAS], rotinas=[], silencios=[], casa_vazia=False),
        registar_historico=lambda d, m, a: None,
    )

    def lotes():
        for agora, leituras in pollings(mudancas, dias):
            passo[:] = [agora]
            yield agora, leituras

    with _com_habitual(h):
        correr(ciclo, lotes())
    return vistos


@dataclass
class Folgas:
    """A distância mais curta a cada limite (negativa: passou o limite)."""

    us07: list[timedelta] = field(default_factory=list)
    us09: list[timedelta] = field(default_factory=list)
    us14: list[timedelta] = field(default_factory=list)


def _min(t: time) -> datetime:
    return datetime.combine(date.min, t)


def folgas(h: habitual.Habitual, mudancas, dias: list[date], caminho: Path = habitual.HISTORICO) -> Folgas:
    f = Folgas()
    nos_dias = [m for m in mudancas if m[0].date() in dias and not habitual._nas_ferias(m[0])]
    desde: datetime | None = None
    for em, dispositivo, tipo, valor in nos_dias:
        if (dispositivo, tipo) == ("porta", "sensorState") and valor == "alarm":
            janela = h.porta.get(habitual.tipo_de_dia(em))
            if janela:
                t = _min(em.time())
                f.us07.append(min(t - (_min(janela[0]) - habitual.MARGEM_PORTA),
                                  (_min(janela[1]) + habitual.MARGEM_PORTA) - t))
        elif (dispositivo, tipo) == ("tomada", "instantPower"):
            if float(valor) > habitual.LIMITE_W:
                desde = desde or em
            elif desde is not None:
                f.us14.append(h.limite_tomada - (em - desde))
                desde = None
    primeiros: dict[date, datetime] = {}
    for sinal in habitual.sinais_de_vida(caminho):
        if sinal.em.date() in dias:
            primeiros.setdefault(sinal.em.date(), sinal.em)
    for dia, primeiro in primeiros.items():
        limite = h.limite_sem_sinais(dia)
        if limite:
            f.us09.append(_min(limite) - _min(primeiro.time()))
    return f


def blocos(mudancas) -> list[list[date]]:
    """Blocos de sete dias, do primeiro ao último dia do histórico."""
    primeiro, ultimo = mudancas[0][0].date(), mudancas[-1][0].date()
    dias = [primeiro + timedelta(days=n) for n in range((ultimo - primeiro).days + 1)]
    return [dias[i:i + 7] for i in range(0, len(dias), 7)]


def relatorio(caminho: Path = habitual.HISTORICO) -> tuple[Counter, dict[str, timedelta | None], list]:
    """Falsos alarmes por US, a folga mais curta de cada limite e os avisos em si."""
    mudancas = _mudancas(caminho)
    falsos: Counter = Counter()
    todos: list = []
    menor: dict[str, timedelta | None] = {"US07": None, "US09": None, "US14": None}
    for dias in blocos(mudancas):
        h = habitual.carregar(caminho, excluir=set(dias))
        vistos = avisos_em(h, mudancas, dias)
        todos += vistos
        falsos.update(us for _, us, _ in vistos)
        f = folgas(h, mudancas, dias, caminho)
        for us, valores in (("US07", f.us07), ("US09", f.us09), ("US14", f.us14)):
            if valores:
                m = min(valores)
                menor[us] = m if menor[us] is None else min(menor[us], m)
    return falsos, menor, todos


def _texto(td: timedelta | None) -> str:
    if td is None:
        return "sem casos"
    sinal = "-" if td < timedelta(0) else ""
    return sinal + habitual.duracao(abs(td))


def main() -> None:
    falsos, menor, todos = relatorio()
    print("Validação por semanas (habitual das outras semanas):")
    for us in ("US07", "US09", "US14"):
        print(f"  {us}: {falsos[us]} falsos alarmes; folga mais curta ao limite: {_texto(menor[us])}")
    for quando, us, resumo in todos:
        print(f"    {quando:%Y-%m-%d %H:%M} {us}: {resumo}")
