"""Saída de casa: a porta da rua abre e as câmaras interiores não vêem ninguém a seguir."""

from datetime import timedelta

import pytest

from backend.formatos import Leitura
from backend.saida import Movimento, Vigia, Visto

from .conftest import AGORA


@pytest.fixture(autouse=True)
def _casa(casa, monkeypatch):
    monkeypatch.delenv("SAIDA_MINUTOS", raising=False)


def volta(vigia: Vigia, m: float, porta: str | None = "normal", **camaras: str) -> Visto:
    em = AGORA + timedelta(minutes=m)
    leituras = [] if porta is None else [Leitura("porta", "sensorState", porta, em, "porta-rua")]
    leituras += [Leitura("camara", "motionDetected", v, em, c.replace("_", "-")) for c, v in camaras.items()]
    return vigia.ver(leituras, em)


def test_porta_abre_e_ninguem_aparece_nas_camaras_a_pessoa_saiu():
    v = Vigia()
    volta(v, 0, cam_sala="")
    assert volta(v, 1, "alarm", cam_sala="") == Visto(porta_abriu=AGORA + timedelta(minutes=1))
    assert volta(v, 3, "normal", cam_sala="") == Visto()
    assert v.a_vigiar

    assert volta(v, 6, "normal", cam_sala="") == Visto(saiu=AGORA + timedelta(minutes=1))
    assert not v.a_vigiar


def test_movimento_numa_camara_interior_depois_da_porta_a_pessoa_ficou():
    v = Vigia()
    volta(v, 0, cam_sala="", cam_quarto="")
    volta(v, 1, "alarm", cam_sala="", cam_quarto="")

    visto = volta(v, 3, "normal", cam_sala="", cam_quarto="15:03")

    assert visto == Visto(movimentos=[Movimento("o quarto", AGORA + timedelta(minutes=3))])
    assert volta(v, 7, "normal", cam_sala="", cam_quarto="15:03") == Visto()  # não conclui saída


def test_o_movimento_da_volta_em_que_a_porta_abre_nao_conta():
    # É quem vai a caminho da porta.
    v = Vigia()
    volta(v, 0, cam_sala="")
    volta(v, 1, "alarm", cam_sala="15:01")

    assert volta(v, 6, "normal", cam_sala="15:01").saiu == AGORA + timedelta(minutes=1)


def test_a_camara_exterior_nao_conta():
    v = Vigia()
    volta(v, 0, cam_sala="", cam_rua="")
    volta(v, 1, "alarm", cam_sala="", cam_rua="")
    volta(v, 2, "normal", cam_sala="", cam_rua="15:02")  # quem passa na rua

    assert volta(v, 6, "normal", cam_sala="", cam_rua="15:02").saiu == AGORA + timedelta(minutes=1)


def test_sem_camaras_interiores_a_casa_nao_conclui():
    v = Vigia()
    volta(v, 0)
    volta(v, 1, "alarm")

    assert volta(v, 6, "normal") == Visto(sem_conclusao=AGORA + timedelta(minutes=1))


def test_uma_janela_a_abrir_nao_e_uma_saida():
    v = Vigia()
    em = AGORA
    v.ver([Leitura("porta", "sensorState", "normal", em, "janela-quarto")], em)

    assert v.ver([Leitura("porta", "sensorState", "alarm", em, "janela-quarto")], em) == Visto()
    assert not v.a_vigiar


def test_a_porta_a_abrir_outra_vez_recomeca_a_janela():
    v = Vigia()
    volta(v, 0, cam_sala="")
    volta(v, 1, "alarm", cam_sala="")
    volta(v, 2, "normal", cam_sala="")
    volta(v, 4, "alarm", cam_sala="")

    assert volta(v, 6, "normal", cam_sala="") == Visto()
    assert volta(v, 9, "normal", cam_sala="").saiu == AGORA + timedelta(minutes=4)


def test_minutos_configuraveis(monkeypatch):
    monkeypatch.setenv("SAIDA_MINUTOS", "1")
    v = Vigia()
    volta(v, 0, cam_sala="")
    volta(v, 1, "alarm", cam_sala="")

    assert volta(v, 2, "normal", cam_sala="").saiu == AGORA + timedelta(minutes=1)


def test_movimento_fora_da_janela_tambem_e_devolvido():
    v = Vigia()
    volta(v, 0, cam_sala="")

    assert volta(v, 1, cam_sala="15:01").movimentos == [Movimento("a sala", AGORA + timedelta(minutes=1))]
