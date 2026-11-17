"""A regra da US11 (luz acesa há demasiado tempo), com os casos de dados/us11.csv."""

import csv
from datetime import datetime, timedelta
from itertools import groupby
from pathlib import Path

import pytest

from backend.formatos import Contexto, Leitura
from backend.regras import us11

DADOS = Path(__file__).resolve().parents[1] / "dados"
CONTEXTO = Contexto(ferias=[], rotinas=[], silencios=[], casa_vazia=False)


@pytest.fixture(autouse=True)
def sem_luz_horas(monkeypatch):
    monkeypatch.delenv("LUZ_HORAS", raising=False)


def _lotes(ficheiro: str):
    """Um lote por hora 'em', pela ordem do ficheiro: cada lote faz de uma volta do polling."""
    with open(DADOS / ficheiro, newline="", encoding="utf-8") as f:
        leituras = [
            Leitura(l["dispositivo"], l["tipo"], l["valor"], datetime.fromisoformat(l["em"]))
            for l in csv.DictReader(f)
        ]
    for em, lote in groupby(leituras, key=lambda l: l.em):
        yield em, list(lote)


def _desvios(ficheiro: str) -> list[tuple[datetime, str]]:
    return [
        (em, d.resumo)
        for em, lote in _lotes(ficheiro)
        for d in us11.verificar(lote, CONTEXTO, em)
    ]


def test_casos_do_dataset():
    terca = "A luz da sala está acesa desde as 14:00, há mais de 5 h, e a porta abriu e fechou depois disso (fechou às 15:11)."
    quinta = "A luz da sala está acesa desde as 08:00, há mais de 5 h, e a porta abriu e fechou depois disso (fechou às 14:11)."
    assert _desvios("us11.csv") == [
        # 1) 5 h acesa, com a porta aberta e fechada às 15:10: avisa e mantém o mesmo texto
        (datetime(2026, 11, 17, 19, 0), terca),
        (datetime(2026, 11, 17, 19, 30), terca),
        # 2) quarta: 6 h acesa, mas a porta nunca abriu -> nada
        # 3) quinta: a porta já estava aberta às 8:00 (não conta); abre e fecha às 14:10
        (datetime(2026, 11, 19, 14, 11), quinta),
        # 4) sexta: a luz apagou ao fim de 2 h -> nada
    ]


def test_o_desvio_e_de_eficiencia_e_nao_imediato():
    desvios = [d for em, lote in _lotes("us11.csv") for d in us11.verificar(lote, CONTEXTO, em)]
    assert {(d.us, d.classe, d.imediato) for d in desvios} == {("US11", "eficiencia", False)}


def _volta(minutos: int, *leituras: tuple[str, str, str]):
    em = datetime(2026, 11, 17, 14, 0) + timedelta(minutes=minutos)
    lote = [Leitura(d, t, v, em) for d, t, v in leituras]
    return us11.verificar(lote, CONTEXTO, em)


LUZ = ("lampada", "power", "on")


def test_luz_horas_curto_para_a_demo(monkeypatch):
    monkeypatch.setenv("LUZ_HORAS", "0.05")  # 3 minutos
    assert _volta(0, LUZ) == []
    assert _volta(1, LUZ, ("porta", "sensorState", "alarm")) == []
    assert _volta(2, LUZ, ("porta", "sensorState", "normal")) == []
    [desvio] = _volta(3, LUZ, ("porta", "sensorState", "normal"))
    assert "há mais de 3 min" in desvio.resumo


def test_volta_sem_leitura_da_luz_nao_esquece(monkeypatch):
    monkeypatch.setenv("LUZ_HORAS", "1")
    _volta(0, LUZ)
    _volta(10, ("porta", "sensorState", "alarm"))  # o MCP não trouxe a lâmpada nesta volta
    _volta(11, ("porta", "sensorState", "normal"))
    assert len(_volta(60)) == 1
    assert _volta(61, ("lampada", "power", "off")) == []
    assert _volta(62) == []  # apagada: sem leitura, continua apagada


def test_valor_estranho_conta_como_a_ultima_leitura(monkeypatch):
    monkeypatch.setenv("LUZ_HORAS", "1")
    _volta(0, LUZ)
    _volta(10, LUZ, ("porta", "sensorState", "alarm"))
    _volta(11, LUZ, ("porta", "sensorState", "normal"))
    assert len(_volta(60, ("lampada", "power", "?"))) == 1


def test_estado_de_um_futuro_e_esquecido():
    _volta(0, LUZ)
    # Um CSV de um dia anterior corrido contra a mesma base de dados: recomeça.
    antes = datetime(2026, 11, 10, 9, 0)
    assert us11.verificar([Leitura("lampada", "power", "on", antes)], CONTEXTO, antes) == []
    assert us11._carregar().acesa_desde.replace(tzinfo=None) == antes


def test_luz_horas_invalido(monkeypatch):
    monkeypatch.setenv("LUZ_HORAS", "cinco")
    with pytest.raises(ValueError, match="LUZ_HORAS"):
        _volta(0, LUZ)


def test_reiniciar():
    _volta(0, LUZ)
    us11.reiniciar()
    assert us11._carregar() is None
