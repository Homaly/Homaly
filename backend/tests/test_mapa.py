"""Do JSON do MCP para as leituras da casa (dispositivos.mapa)."""

import json
from datetime import UTC, datetime
from pathlib import Path

from backend.dispositivos import mapa
from backend.formatos import Leitura

from .conftest import AGORA

DADOS = Path(__file__).parent / "dados"


def resposta_real(nome: str) -> dict:
    """O JSON que vem dentro de uma resposta real do MCP guardada em tests/dados/."""
    texto = (DADOS / nome).read_text()
    mensagem = json.loads([l[5:] for l in texto.splitlines() if l.startswith("data:")][-1])
    return json.loads(mensagem["result"]["content"][0]["text"])


def test_le_os_dispositivos_da_casa_real():
    leituras = mapa.para_leituras(resposta_real("mcp_get_home_devices.txt"), AGORA)

    assert Leitura("porta", "sensorState", "alarm", AGORA) in leituras
    assert Leitura("temperatura", "temperatureValue", 23.1, AGORA) in leituras
    assert Leitura("lampada", "power", "on", AGORA) in leituras
    assert Leitura("lampada", "brightness", 100, AGORA) in leituras
    assert Leitura("tomada", "power", "off", AGORA) in leituras
    assert Leitura("tomada", "instantPower", 0, AGORA) in leituras
    assert Leitura("fumo", "sensorState", "normal", AGORA) in leituras
    assert Leitura("hub", "alarmState", "normal", AGORA) in leituras
    assert Leitura("camara", "motionDetected", "", AGORA) in leituras


def test_ignora_valores_que_nao_sao_simples():
    # A tomada traz "multiPower" com uma lista; não cabe numa Leitura.
    leituras = mapa.para_leituras(resposta_real("mcp_get_home_devices.txt"), AGORA)

    assert all(isinstance(l.valor, (str, int, float, bool)) for l in leituras)
    assert not any(l.tipo == "multiPower" for l in leituras)


def test_tipo_desconhecido_fica_com_o_nome_original():
    dados = {"devices": [{"id": "x", "type": "robot", "capabilities": [{"type": "power", "value": "on"}]}]}

    assert mapa.para_leituras(dados, AGORA) == [Leitura("robot", "power", "on", AGORA)]


def test_dispositivo_sem_capabilities_nao_da_leituras():
    assert mapa.para_leituras({"devices": [{"id": "x", "type": "bulb"}]}, AGORA) == []


# Sensores em silêncio: o MCP devolve o último valor mesmo que o dispositivo não comunique há horas.
# Na resposta guardada, a porta comunicou a 16/11 às 19:16 UTC e a lâmpada a 4/11.
DEPOIS_DA_LAMPADA = datetime(2026, 11, 16, 19, 0, tzinfo=UTC)


def test_dispositivo_que_nao_comunica_desde_o_limite_nao_da_leituras():
    leituras = mapa.para_leituras(resposta_real("mcp_get_home_devices.txt"), AGORA, DEPOIS_DA_LAMPADA)

    assert Leitura("porta", "sensorState", "alarm", AGORA) in leituras
    assert not any(l.dispositivo == "lampada" for l in leituras)


def test_sem_limite_da_todas_as_leituras():
    leituras = mapa.para_leituras(resposta_real("mcp_get_home_devices.txt"), AGORA, None)

    assert any(l.dispositivo == "lampada" for l in leituras)


def test_dispositivo_sem_hora_de_comunicacao_conta_como_recente():
    dados = {"devices": [{"id": "x", "type": "bulb", "capabilities": [{"type": "power", "value": "on"}]}]}

    assert mapa.para_leituras(dados, AGORA, DEPOIS_DA_LAMPADA) == [Leitura("lampada", "power", "on", AGORA)]


def test_em_silencio_diz_desde_quando():
    calados = mapa.em_silencio(resposta_real("mcp_get_home_devices.txt"), DEPOIS_DA_LAMPADA)

    assert calados == {"lampada": datetime(2026, 11, 4, 11, 55, 15, 316000, tzinfo=UTC)}


def test_ids_por_dispositivo():
    ids = mapa.ids(resposta_real("mcp_get_home_devices.txt"))

    assert ids["lampada"] == "59dfc0f6-8813-4768-9877-f993b3e2dec3"
    assert ids["tomada"] == "30c07125-1175-47ae-a8be-96b1b20d4539"
    assert ids["porta"] == "937ac145-dc42-4dcf-9180-ad481ef33c82"


def test_valor_de_uma_capability_nos_detalhes():
    detalhes = resposta_real("mcp_get_device_details.txt")

    assert mapa.valor(detalhes, "power") == "on"
    assert mapa.valor(detalhes, "brightness") == 100
    assert mapa.valor(detalhes, "naoexiste") is None
