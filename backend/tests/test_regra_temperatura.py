"""A regra da casa fria (US10): abaixo de 16 °C durante duas horas."""

from datetime import timedelta

from backend.formatos import Contexto, Desvio, Leitura, Resolucao
from backend.regras import temperatura

from .conftest import AGORA

CONTEXTO = Contexto(ferias=[], rotinas=[], silencios=[], casa_vazia=False)


def minuto(m: float):
    return AGORA + timedelta(minutes=m)


def ver(m: float, graus: float | None) -> list[Desvio | Resolucao]:
    lidas = [] if graus is None else [Leitura("temperatura", "temperatureValue", graus, minuto(m))]
    return temperatura.verificar(lidas, CONTEXTO, minuto(m))


def test_casa_quente_nao_da_nada():
    assert ver(0, 20.0) == []


def test_abaixo_de_16_menos_de_duas_horas_nao_da_nada():
    assert ver(0, 15.5) == []
    assert ver(119, 15.5) == []


def test_abaixo_de_16_durante_duas_horas_da_aviso():
    ver(0, 15.8)

    [desvio] = ver(120, 15.4)

    assert desvio.us == "US10"
    assert desvio.classe == "saude_conforto"
    assert desvio.resumo == "A sala está abaixo de 16 °C desde as 15:00; às 17:00 estava a 15,4 °C."
    assert desvio.habitual is None


def test_o_aviso_repete_igual_mesmo_que_a_temperatura_mude():
    ver(0, 15.8)
    aviso = ver(120, 15.4)

    assert ver(121, 15.1) == aviso


def test_volta_a_subir_resolve_com_a_temperatura_e_a_hora():
    ver(0, 15.8)
    ver(120, 15.4)

    assert ver(150, 16.4) == [Resolucao("US10", "a temperatura voltou a 16,4 °C às 17:30", minuto(150))]
    assert ver(151, 16.4) == []


def test_sobe_antes_das_duas_horas_recomeca_a_contar():
    ver(0, 15.0)
    assert ver(60, 16.5) == []
    ver(61, 15.0)

    assert ver(150, 15.0) == []
    [desvio] = ver(181, 15.0)
    assert "desde as 16:01" in desvio.resumo


def test_volta_sem_leitura_mantem_o_aviso():
    ver(0, 15.8)
    aviso = ver(120, 15.4)

    assert ver(121, None) == aviso


def test_volta_sem_leitura_antes_do_aviso_nao_da_nada():
    ver(0, 15.8)

    assert ver(130, None) == []


def test_hora_sem_fuso_conta_como_hora_local():
    ver(0, 15.0)
    sem_fuso = minuto(120).astimezone().replace(tzinfo=None)
    lidas = [Leitura("temperatura", "temperatureValue", 15.0, sem_fuso)]

    [desvio] = temperatura.verificar(lidas, CONTEXTO, sem_fuso)

    assert desvio.us == "US10"


def test_estado_com_hora_no_futuro_recomeca():
    ver(200, 15.0)

    assert ver(0, 15.0) == []
    [desvio] = ver(120, 15.0)
    assert "desde as 15:00" in desvio.resumo


def test_exatamente_no_limite_resolve():
    ver(0, 15.8)
    ver(120, 15.4)

    [resolucao] = ver(130, 16.0)
    assert resolucao.texto == "a temperatura voltou a 16 °C às 17:10"


def test_temperatura_habitual_vem_do_historico(monkeypatch):
    monkeypatch.setattr(temperatura, "temperatura_habitual", lambda agora: 19.5)
    ver(0, 15.8)

    [desvio] = ver(120, 15.4)

    assert desvio.habitual == "a esta hora a sala costuma estar a 19,5 °C"


def test_limite_e_tempo_configuraveis(monkeypatch):
    monkeypatch.setenv("FRIO_LIMITE_GRAUS", "25")
    monkeypatch.setenv("FRIO_MINUTOS", "2")
    ver(0, 23.1)

    [desvio] = ver(2, 23.1)
    assert desvio.resumo.startswith("A sala está abaixo de 25 °C")
