"""Os casos do dataset das US08, US10 e US12 (dados/us08.csv, us10.csv, us12.csv), pelas regras.

Cada lote de leituras com a mesma hora faz de uma volta do polling. Os CSV seguem os critérios
de aceitação das user stories e servem também para correr o ciclo da Vila:
`uv run python -m backend.ciclo dados/us08.csv`.
"""

import csv
from datetime import datetime
from itertools import groupby
from pathlib import Path

import pytest

from backend.formatos import Contexto, Desvio, Leitura, Resolucao
from backend.regras import porta, temperatura

DADOS = Path(__file__).resolve().parents[1] / "dados"
CONTEXTO = Contexto(ferias=[], rotinas=[], silencios=[], casa_vazia=False)


@pytest.fixture(autouse=True)
def limites_por_omissao(monkeypatch):
    for nome in ("PORTA_MINUTOS", "PORTA_QUEDA_GRAUS", "FRIO_LIMITE_GRAUS", "FRIO_MINUTOS"):
        monkeypatch.delenv(nome, raising=False)


def _valor(texto: str) -> str | float:
    try:
        return float(texto)
    except ValueError:
        return texto


def _lotes(ficheiro: str):
    with open(DADOS / ficheiro, newline="", encoding="utf-8") as f:
        leituras = [
            Leitura(l["dispositivo"], l["tipo"], _valor(l["valor"]), datetime.fromisoformat(l["em"]))
            for l in csv.DictReader(f)
        ]
    for em, lote in groupby(leituras, key=lambda l: l.em):
        yield em, list(lote)


def _resultados(ficheiro: str, regra) -> list[tuple[str, str, str, str]]:
    """(hora, US, classe ou 'resolvida', texto) de cada volta em que a regra devolveu algo novo.

    O ciclo recebe o mesmo desvio em todas as voltas; aqui só se guarda quando muda, que é o que a
    pessoa vê (um aviso novo, um aviso que mudou, ou o fim).
    """
    vistos: list[tuple[str, str, str, str]] = []
    anterior: dict[str, Desvio] = {}
    for em, lote in _lotes(ficheiro):
        for r in regra.verificar(lote, CONTEXTO, em):
            if isinstance(r, Resolucao):
                vistos.append((f"{em:%H:%M}", r.us, "resolvida", r.texto))
                anterior.pop(r.us, None)
            elif anterior.get(r.us) != r:
                vistos.append((f"{em:%H:%M}", r.us, r.classe, r.resumo))
                anterior[r.us] = r
    return vistos


def test_us08_porta_esquecida_aberta():
    assert _resultados("us08.csv", porta) == [
        # 09:00–09:03: fecha antes dos cinco minutos, não há aviso.
        ("10:05", "US08", "seguranca", "A porta da rua está aberta há mais de 5 minutos, desde as 10:00."),
        ("10:12", "US08", "resolvida", "a porta fechou às 10:12"),
    ]


def test_us12_porta_aberta_com_a_casa_a_arrefecer():
    assert _resultados("us12.csv", porta) == [
        # A US12 avisa primeiro e, aos cinco minutos, o mesmo aviso passa a segurança.
        (
            "14:02",
            "US12",
            "eficiencia",
            "A porta da rua está aberta desde as 14:00 e a sala já desceu 2,1 °C (de 20,5 °C para 18,4 °C).",
        ),
        (
            "14:05",
            "US12",
            "seguranca",
            "A porta da rua está aberta há mais de 5 minutos, desde as 14:00, e a sala já desceu 2,1 °C.",
        ),
        ("14:09", "US12", "resolvida", "a porta fechou às 14:09"),
        # A US08 avisa primeiro e a descida junta-se ao mesmo aviso.
        ("16:05", "US08", "seguranca", "A porta da rua está aberta há mais de 5 minutos, desde as 16:00."),
        (
            "16:08",
            "US08",
            "seguranca",
            "A porta da rua está aberta há mais de 5 minutos, desde as 16:00, e a sala já desceu 2,1 °C.",
        ),
        ("16:10", "US08", "resolvida", "a porta fechou às 16:10"),
        # 18:00–18:04: desce só 1 °C e fecha antes dos cinco minutos, não há aviso.
    ]


def test_us10_casa_fria_durante_horas():
    assert _resultados("us10.csv", temperatura) == [
        ("08:00", "US10", "saude_conforto", "A sala está abaixo de 16 °C desde as 06:00; às 08:00 estava a 15,3 °C."),
        ("09:15", "US10", "resolvida", "a temperatura voltou a 16,4 °C às 09:15"),
        # 12:00–13:30: abaixo de 16 °C só hora e meia, não há aviso.
    ]
