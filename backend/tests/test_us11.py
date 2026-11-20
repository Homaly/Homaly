"""A regra da US11 (luz acesa há demasiado tempo), com os casos de dados/us11.csv."""

import csv
from datetime import datetime, timedelta
from itertools import groupby
from pathlib import Path

import pytest

from backend.formatos import Contexto, Leitura, Resolucao
from backend.regras import us11

DADOS = Path(__file__).resolve().parents[1] / "dados"
CONTEXTO = Contexto(ferias=[], rotinas=[], silencios=[], casa_vazia=False)


@pytest.fixture(autouse=True)
def sem_luz_horas(monkeypatch):
    monkeypatch.delenv("LUZ_HORAS", raising=False)
    monkeypatch.delenv("SAIDA_MINUTOS", raising=False)
    us11.reiniciar()  # a janela da saída fica em memória, entre testes


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
    assert us11._carregar()["lampada"].acesa_desde.replace(tzinfo=None) == antes


def test_luz_horas_invalido(monkeypatch):
    monkeypatch.setenv("LUZ_HORAS", "cinco")
    with pytest.raises(ValueError, match="LUZ_HORAS"):
        _volta(0, LUZ)


def test_reiniciar():
    _volta(0, LUZ)
    us11.reiniciar()
    assert us11._carregar() == {}


# Com câmaras (inventário CASA, em conftest.py): a saída de casa e a câmara da divisão da luz


def _casa(minutos: int, porta: str = "normal", sala: str = "", quarto: str = "", luz: str = "on"):
    em = datetime(2026, 11, 17, 14, 0) + timedelta(minutes=minutos)
    lote = [
        Leitura("lampada", "power", luz, em, "luz-sala"),
        Leitura("porta", "sensorState", porta, em, "porta-rua"),
        Leitura("camara", "motionDetected", sala, em, "cam-sala"),
        Leitura("camara", "motionDetected", quarto, em, "cam-quarto"),
    ]
    return us11.verificar(lote, CONTEXTO, em)


@pytest.mark.usefixtures("casa")
def test_saiu_de_casa_com_a_luz_acesa(monkeypatch):
    monkeypatch.setenv("LUZ_HORAS", "1")
    _casa(0)
    _casa(10, "alarm")  # 14:10, a porta abre
    _casa(11)
    assert _casa(15) == []  # 14:15: ninguém nas câmaras, saiu

    [desvio] = _casa(60)
    assert desvio.resumo == (
        "A luz da sala está acesa desde as 14:00, há mais de 1 h, e parece que saíram de casa às 14:10: "
        "a porta da rua abriu e as câmaras não viram ninguém a seguir."
    )
    assert _casa(90) == [desvio]


@pytest.mark.usefixtures("casa")
def test_movimento_depois_da_porta_quer_dizer_que_nao_saiu(monkeypatch):
    monkeypatch.setenv("LUZ_HORAS", "1")
    _casa(0)
    _casa(10, "alarm")
    _casa(12, quarto="14:12")  # alguém em casa (entrou, ou não chegou a sair)

    assert _casa(60, quarto="14:12") == []
    assert _casa(120, quarto="14:12") == []


@pytest.mark.usefixtures("casa")
def test_movimento_na_divisao_da_luz_resolve_o_aviso(monkeypatch):
    monkeypatch.setenv("LUZ_HORAS", "1")
    _casa(0)
    _casa(10, "alarm")
    _casa(15)
    [desvio] = _casa(60)

    assert _casa(70, sala="15:10") == [Resolucao("US11", "houve movimento na sala às 15:10", datetime(2026, 11, 17, 15, 10).astimezone())]
    assert _casa(80, sala="15:10") == []


@pytest.mark.usefixtures("casa")
def test_movimento_noutra_divisao_nao_resolve(monkeypatch):
    monkeypatch.setenv("LUZ_HORAS", "1")
    _casa(0)
    _casa(10, "alarm")
    _casa(15)
    [desvio] = _casa(60)

    assert _casa(70, quarto="15:10") == [desvio]


@pytest.mark.usefixtures("casa")
def test_com_camaras_a_porta_abrir_e_fechar_ja_nao_chega(monkeypatch):
    # Antes da saída se concluir (cinco minutos sem movimento), não há aviso.
    monkeypatch.setenv("LUZ_HORAS", "1")
    monkeypatch.setenv("SAIDA_MINUTOS", "30")
    _casa(0)
    _casa(50, "alarm")
    _casa(51)

    assert _casa(60) == []
    assert len(_casa(80)) == 1


# Várias lâmpadas: cada uma com o seu estado, um aviso de cada vez, com o id da lâmpada


def _duas(minutos: int, sala: str = "on", quarto: str = "on", porta: str = "normal", cam_quarto: str = ""):
    em = datetime(2026, 11, 17, 14, 0) + timedelta(minutes=minutos)
    lote = [
        Leitura("lampada", "power", sala, em, "luz-sala"),
        Leitura("lampada", "power", quarto, em, "luz-quarto"),
        Leitura("porta", "sensorState", porta, em, "porta-rua"),
        Leitura("camara", "motionDetected", "", em, "cam-sala"),
        Leitura("camara", "motionDetected", cam_quarto, em, "cam-quarto"),
    ]
    return us11.verificar(lote, CONTEXTO, em)


@pytest.mark.usefixtures("casa")
def test_duas_luzes_um_aviso_de_cada_vez(monkeypatch):
    monkeypatch.setenv("LUZ_HORAS", "1")
    _duas(0, quarto="off")
    _duas(5)  # a do quarto acende às 14:05
    _duas(10, porta="alarm")
    _duas(15)  # saiu às 14:10

    [sala] = _duas(60)
    assert sala.dispositivo == "luz-sala"
    assert sala.resumo.startswith("A luz da sala está acesa desde as 14:00")
    assert _duas(70) == [sala]  # a do quarto também já merece, mas espera

    assert _duas(80, sala="off") == []  # o aviso acaba: o ciclo fecha-o nesta volta
    [quarto] = _duas(81, sala="off")
    assert quarto.dispositivo == "luz-quarto"
    assert quarto.resumo.startswith("A luz do quarto está acesa desde as 14:05")
    assert _duas(90, sala="off", quarto="off") == []
    assert us11._carregar() == {}


@pytest.mark.usefixtures("casa")
def test_o_movimento_no_quarto_so_conta_para_a_luz_do_quarto(monkeypatch):
    monkeypatch.setenv("LUZ_HORAS", "1")
    _duas(0)
    _duas(10, porta="alarm")
    _duas(15)
    [sala] = _duas(60)

    assert _duas(65, cam_quarto="15:05") == [sala]  # a da sala continua: ninguém na sala
    assert _duas(80, sala="off", cam_quarto="15:05") == []
    assert _duas(81, sala="off", cam_quarto="15:05") == []  # há alguém no quarto: a luz de lá não avisa


@pytest.mark.usefixtures("casa")
def test_uma_luz_a_apagar_nao_mexe_no_aviso_da_outra(monkeypatch):
    monkeypatch.setenv("LUZ_HORAS", "1")
    _duas(0)
    _duas(10, porta="alarm")
    _duas(15)
    [sala] = _duas(60)
    assert _duas(61, quarto="off") == [sala]
