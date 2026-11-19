from datetime import datetime, timedelta

from backend.formatos import Leitura
from backend.sinais import BASE, Detetor, Sinal, comunica, sinal

T0 = datetime(2026, 11, 20, 11, 0)
T1 = T0 + timedelta(seconds=30)
T2 = T1 + timedelta(seconds=30)


def test_cada_tipo_de_sinal():
    assert sinal("camara", "motionDetected", "2026-11-20T11:05", "") == "movimento na câmara"
    assert sinal("camara", "soundDetected", "x", "") == "som na câmara"
    assert sinal("lampada", "power", "on", "off") == "a luz ligada"
    assert sinal("lampada", "power", "off", "on") == "a luz desligada"
    assert sinal("lampada", "brightness", 40, 100) == "o brilho da luz mudado"
    assert sinal("tomada", "instantPower", 190.0, 0.0) == "a tomada a gastar"
    assert sinal("porta", "sensorState", "alarm", "normal") == "a porta aberta"


def test_o_que_nao_e_sinal():
    assert sinal("camara", "motionDetected", "", "2026-11-20T11:05") is None
    assert sinal("camara", "motionDetected", "2026-11-20T11:05", "2026-11-20T11:05") is None
    assert sinal("tomada", "instantPower", 200.0, 190.0) is None  # já gastava
    assert sinal("tomada", "instantPower", 0.0, 190.0) is None
    assert sinal("porta", "sensorState", "normal", "alarm") is None  # fechar não conta
    assert sinal("lampada", "power", "on", None) is None  # sem anterior
    assert sinal("temperatura", "temperatureValue", 15.0, 20.0) is None


def test_detetor_compara_com_a_volta_anterior():
    d = Detetor()
    assert d.ver([Leitura("lampada", "power", "off", T0)]) == []
    assert d.ver([Leitura("lampada", "power", "on", T1)]) == [Sinal("lampada", "a luz ligada", T1)]
    assert d.ver([Leitura("lampada", "power", "on", T2)]) == []


def test_um_dispositivo_que_falta_numa_volta_guarda_o_anterior():
    d = Detetor(anteriores=BASE)
    assert d.ver([Leitura("porta", "sensorState", "normal", T1)]) == []
    assert d.ver([Leitura("lampada", "power", "on", T2)]) == [Sinal("lampada", "a luz ligada", T2)]


def test_um_comando_da_casa_nao_e_sinal():
    d = Detetor(anteriores=BASE, comandado=lambda disp, tipo: (disp, tipo) == ("lampada", "power"))
    assert d.ver([Leitura("lampada", "power", "on", T1)]) == []
    assert d.ver([Leitura("camara", "motionDetected", "a", T2)]) == [Sinal("camara", "movimento na câmara", T2)]


def test_comunica():
    assert comunica([Leitura("porta", "sensorState", "normal", T0)])
    assert not comunica([Leitura("temperatura", "temperatureValue", 20.0, T0)])
    assert not comunica([])
