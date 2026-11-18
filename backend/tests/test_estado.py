from datetime import timedelta

from backend import dispositivos
from backend.contexto import repositorio
from backend.conversa.estado import _sensores, estado_da_casa
from backend.formatos import Leitura, Rotina
from tests.conftest import AGORA


def _l(dispositivo, tipo, valor):
    return Leitura(dispositivo, tipo, valor, AGORA)


def test_sensores_em_texto():
    leituras = [
        _l("porta", "sensorState", "alarm"),
        _l("temperatura", "temperatureValue", 14.0),
        _l("lampada", "power", "off"),
        _l("tomada", "power", "on"),
        _l("tomada", "instantPower", 1800),
    ]
    assert _sensores(leituras, {}, AGORA) == {
        "porta da rua": "aberta",
        "temperatura da sala": "14 °C",
        "luz da sala": "apagada",
        "tomada": "ligada, a gastar 1800 W",
    }


def test_sensor_calado_diz_desde_quando():
    calados = {"lampada": AGORA - timedelta(days=1)}
    assert _sensores([_l("porta", "sensorState", "normal")], calados, AGORA) == {
        "porta da rua": "fechada",
        "lampada": "sem comunicar desde 16/11 15:00",
    }


def test_sem_leituras_diz_que_nao_leu():
    assert _sensores([], {}, AGORA) == "A casa ainda não leu os sensores."


def test_estado_junta_o_que_a_pessoa_disse(monkeypatch):
    monkeypatch.setattr(dispositivos, "ultimas", lambda: [])
    monkeypatch.setattr(dispositivos, "em_silencio", lambda: {})
    repositorio.guardar_rotina(Rotina("a empregada vem", [1], None))
    estado = estado_da_casa(AGORA)
    assert estado["o_que_me_disseram"]["rotinas"] == ["a empregada vem: terça-feira"]
    assert estado["avisos_ativos"] == []


def test_uma_parte_que_falha_fica_de_fora(monkeypatch):
    def rebenta():
        raise RuntimeError("MCP em baixo")

    monkeypatch.setattr(dispositivos, "ultimas", rebenta)
    estado = estado_da_casa(AGORA)
    assert "sensores" not in estado
    assert "o_que_me_disseram" in estado


def test_aconteceu_hoje_diz_o_dispositivo(monkeypatch):
    from backend import eventos
    from backend.contrato import Evento

    eventos.registar(Evento(em=AGORA - timedelta(hours=1), dispositivo="porta", descricao="Abriu"))
    eventos.registar(Evento(em=AGORA - timedelta(days=1), dispositivo="porta", descricao="Fechou"))  # ontem
    assert estado_da_casa(AGORA)["aconteceu_hoje"] == ["14:00 porta: Abriu"]
