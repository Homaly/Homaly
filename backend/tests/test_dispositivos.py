"""A fachada dispositivos: ler(), executar(), alarme(), leituras injetadas e eventos."""

import copy
import json
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import dispositivos, eventos
from backend.dispositivos import simulacao
from backend.dispositivos.mcp import ErroDispositivos
from backend.formatos import Leitura

from .conftest import AGORA

DADOS = Path(__file__).parent / "dados"
LAMPADA = "59dfc0f6-8813-4768-9877-f993b3e2dec3"
TOMADA = "30c07125-1175-47ae-a8be-96b1b20d4539"


def json_real(nome: str) -> dict:
    texto = (DADOS / nome).read_text()
    mensagem = json.loads([l[5:] for l in texto.splitlines() if l.startswith("data:")][-1])
    return json.loads(mensagem["result"]["content"][0]["text"])


def com_valor(casa: dict, tipo_mcp: str, capability: str, valor) -> dict:
    """Uma cópia da casa com um valor mudado."""
    nova = copy.deepcopy(casa)
    for d in nova["devices"]:
        if d["type"] == tipo_mcp:
            for c in d["capabilities"]:
                if c["type"] == capability:
                    c["value"] = valor
    return nova


def comunicou_em(casa: dict, quando, tipo_mcp: str | None = None) -> dict:
    """Uma cópia da casa em que os dispositivos (ou só um tipo) comunicaram pela última vez em `quando`."""
    nova = copy.deepcopy(casa)
    for d in nova["devices"]:
        if tipo_mcp is None or d["type"] == tipo_mcp:
            d["lastCommunicationTime"] = int(quando.timestamp() * 1000)
    return nova


class ClienteFalso:
    """Faz de ClienteMCP: responde com a casa guardada e regista as chamadas."""

    def __init__(self, casa: dict | None = None):
        self.casa = casa or comunicou_em(json_real("mcp_get_home_devices.txt"), AGORA)
        self.chamadas: list[tuple[str, dict]] = []
        self.detalhes: dict[str, list[dict]] = {}  # deviceId -> respostas seguidas de get_device_details
        self.falhar = False

    def chamar(self, ferramenta: str, argumentos: dict | None = None) -> dict:
        self.chamadas.append((ferramenta, argumentos or {}))
        if self.falhar:
            raise ErroDispositivos("sem rede")
        if ferramenta == "get_home_devices":
            return self.casa
        if ferramenta == "get_home_security_status":
            return {"status": "AWAY", "isAlarmed": False}
        if ferramenta == "update_device_capabilities":
            return {"texto": "ok"}
        if ferramenta == "get_device_details":
            respostas = self.detalhes[argumentos["deviceId"]]
            return respostas.pop(0) if len(respostas) > 1 else respostas[0]
        raise AssertionError(ferramenta)


def detalhes(tipo: str, valor) -> dict:
    return {"capabilities": [{"type": tipo, "value": valor}]}


@pytest.fixture
def falso(monkeypatch):
    cliente = ClienteFalso()
    dispositivos.configurar(cliente)
    simulacao.limpar()
    monkeypatch.setattr(dispositivos, "PAUSA_S", 0)
    # A hora real da casa: um minuto depois de todos os dispositivos terem comunicado.
    monkeypatch.setattr(dispositivos, "_agora_real", lambda: AGORA + timedelta(minutes=1))
    monkeypatch.delenv("SENSOR_SILENCIO_MINUTOS", raising=False)
    yield cliente
    dispositivos.configurar(None)
    simulacao.limpar()


# ler()


def test_ler_faz_um_so_pedido_e_devolve_leituras(falso):
    leituras = dispositivos.ler(AGORA)

    assert falso.chamadas == [("get_home_devices", {})]
    assert Leitura("porta", "sensorState", "alarm", AGORA) in leituras
    assert Leitura("temperatura", "temperatureValue", 23.1, AGORA) in leituras


def test_ler_sem_mcp_levanta_erro(falso):
    falso.falhar = True

    with pytest.raises(ErroDispositivos):
        dispositivos.ler(AGORA)


# Eventos quando a porta, a lâmpada ou a tomada mudam


def test_primeira_leitura_nao_gera_eventos(falso):
    dispositivos.ler(AGORA)

    assert eventos.listar() == []


def test_porta_a_fechar_gera_evento(falso):
    dispositivos.ler(AGORA)
    falso.casa = com_valor(falso.casa, "contactSensor", "sensorState", "normal")
    dispositivos.ler(AGORA)

    [evento] = eventos.listar()
    assert (evento.dispositivo, evento.descricao, evento.em) == ("Porta da rua", "Fechou", AGORA)


def test_lampada_e_tomada_geram_eventos(falso):
    dispositivos.ler(AGORA)
    casa = com_valor(falso.casa, "bulb", "power", "off")
    falso.casa = com_valor(casa, "plug", "power", "on")
    dispositivos.ler(AGORA)

    assert {(e.dispositivo, e.descricao) for e in eventos.listar()} == {("Luz da sala", "Apagou"), ("Tomada", "Ligou")}


def test_temperatura_nao_gera_eventos(falso):
    dispositivos.ler(AGORA)
    falso.casa = com_valor(falso.casa, "temperatureSensor", "temperatureValue", 18.0)
    dispositivos.ler(AGORA)

    assert eventos.listar() == []


def test_valor_igual_nao_gera_evento(falso):
    dispositivos.ler(AGORA)
    dispositivos.ler(AGORA)

    assert eventos.listar() == []


# Sensores em silêncio: o MCP repete o último valor de um dispositivo que deixou de comunicar


def test_dispositivo_calado_ha_mais_de_uma_hora_nao_da_leituras(falso):
    falso.casa = comunicou_em(falso.casa, AGORA - timedelta(minutes=61), "bulb")

    leituras = dispositivos.ler(AGORA)

    assert not any(l.dispositivo == "lampada" for l in leituras)
    assert any(l.dispositivo == "porta" for l in leituras)


def test_dispositivo_calado_ha_menos_de_uma_hora_conta(falso):
    falso.casa = comunicou_em(falso.casa, AGORA - timedelta(minutes=50), "bulb")

    assert any(l.dispositivo == "lampada" for l in dispositivos.ler(AGORA))


def test_em_silencio_diz_que_dispositivos_estao_calados_e_desde_quando(falso):
    quando = AGORA - timedelta(hours=8)
    falso.casa = comunicou_em(falso.casa, quando, "contactSensor")

    dispositivos.ler(AGORA)

    assert dispositivos.em_silencio() == {"porta": quando}


def test_o_silencio_mede_se_com_a_hora_real_e_nao_com_a_do_ciclo(falso):
    # O ciclo da Vila pode passar uma hora acelerada; o lastCommunicationTime do MCP é real.
    dispositivos.ler(AGORA + timedelta(days=3))

    assert dispositivos.em_silencio() == {}


def test_limite_do_silencio_configuravel(falso, monkeypatch):
    monkeypatch.setenv("SENSOR_SILENCIO_MINUTOS", "10")
    falso.casa = comunicou_em(falso.casa, AGORA - timedelta(minutes=15), "bulb")

    assert not any(l.dispositivo == "lampada" for l in dispositivos.ler(AGORA))


def test_limite_zero_desliga_o_filtro(falso, monkeypatch):
    monkeypatch.setenv("SENSOR_SILENCIO_MINUTOS", "0")
    falso.casa = comunicou_em(falso.casa, AGORA - timedelta(days=13), "bulb")

    assert any(l.dispositivo == "lampada" for l in dispositivos.ler(AGORA))


def test_limite_invalido_diz_qual(falso, monkeypatch):
    monkeypatch.setenv("SENSOR_SILENCIO_MINUTOS", "uma hora")

    with pytest.raises(ValueError, match="SENSOR_SILENCIO_MINUTOS"):
        dispositivos.ler(AGORA)


def test_leitura_injetada_aparece_mesmo_com_o_sensor_calado(falso):
    # Na demo, a sala a 15 °C tem de aparecer mesmo com o kit desligado.
    falso.casa = comunicou_em(falso.casa, AGORA - timedelta(hours=8), "temperatureSensor")
    simulacao.sobrepor("temperatura", "temperatureValue", 15.0)

    assert Leitura("temperatura", "temperatureValue", 15.0, AGORA) in dispositivos.ler(AGORA)


def test_sensor_calado_nao_gera_eventos(falso):
    dispositivos.ler(AGORA)
    casa = com_valor(falso.casa, "contactSensor", "sensorState", "normal")
    falso.casa = comunicou_em(casa, AGORA - timedelta(hours=2), "contactSensor")

    dispositivos.ler(AGORA)

    assert eventos.listar() == []


def test_executar_encontra_um_dispositivo_calado(falso):
    falso.casa = comunicou_em(falso.casa, AGORA - timedelta(hours=2), "bulb")
    falso.detalhes[LAMPADA] = [detalhes("power", "off")]
    dispositivos.ler(AGORA)

    assert dispositivos.executar("lampada", "power", "off") is True


# Leituras injetadas (demo)


def test_leitura_injetada_sobrepoe_a_real(falso):
    simulacao.sobrepor("temperatura", "temperatureValue", 15.0)

    leituras = dispositivos.ler(AGORA)

    assert Leitura("temperatura", "temperatureValue", 15.0, AGORA) in leituras
    assert Leitura("temperatura", "temperatureValue", 23.1, AGORA) not in leituras


def test_leitura_injetada_que_nao_existe_e_acrescentada(falso):
    simulacao.sobrepor("porta", "novo", "x")

    assert Leitura("porta", "novo", "x", AGORA) in dispositivos.ler(AGORA)


def test_remover_leitura_injetada_volta_a_real(falso):
    simulacao.sobrepor("temperatura", "temperatureValue", 15.0)
    simulacao.remover("temperatura", "temperatureValue")

    assert Leitura("temperatura", "temperatureValue", 23.1, AGORA) in dispositivos.ler(AGORA)


def test_porta_injetada_gera_evento(falso):
    dispositivos.ler(AGORA)
    simulacao.sobrepor("porta", "sensorState", "normal")
    dispositivos.ler(AGORA)

    assert [(e.dispositivo, e.descricao) for e in eventos.listar()] == [("Porta da rua", "Fechou")]


def test_pedidos_dev_das_leituras():
    app = FastAPI()
    app.include_router(simulacao.router)
    api = TestClient(app)
    simulacao.limpar()

    r = api.post("/dev/leituras", json={"dispositivo": "temperatura", "tipo": "temperatureValue", "valor": 15})
    assert r.status_code == 200
    assert api.get("/dev/leituras").json() == [{"dispositivo": "temperatura", "tipo": "temperatureValue", "valor": 15}]

    assert api.delete("/dev/leituras/temperatura/temperatureValue").status_code == 204
    assert api.get("/dev/leituras").json() == []
    assert api.delete("/dev/leituras/temperatura/temperatureValue").status_code == 404

    api.post("/dev/leituras", json={"dispositivo": "porta", "tipo": "sensorState", "valor": "alarm"})
    assert api.delete("/dev/leituras").status_code == 204
    assert api.get("/dev/leituras").json() == []


def test_pedido_dev_recusa_dispositivo_vazio():
    app = FastAPI()
    app.include_router(simulacao.router)

    r = TestClient(app).post("/dev/leituras", json={"dispositivo": "", "tipo": "x", "valor": 1})

    assert r.status_code == 422


# executar()


def test_apagar_a_lampada_e_confirmar(falso):
    falso.detalhes[LAMPADA] = [detalhes("power", "off")]

    assert dispositivos.executar("lampada", "power", "off") is True
    assert ("update_device_capabilities", {"deviceId": LAMPADA, "body": {"type": "power", "value": "off"}}) in falso.chamadas


def test_desligar_a_tomada(falso):
    falso.detalhes[TOMADA] = [detalhes("power", "off")]

    assert dispositivos.executar("tomada", "power", "off") is True


def test_mudar_o_brilho(falso):
    falso.detalhes[LAMPADA] = [detalhes("brightness", 40)]

    assert dispositivos.executar("lampada", "brightness", 40) is True
    assert ("update_device_capabilities", {"deviceId": LAMPADA, "body": {"type": "brightness", "value": 40}}) in falso.chamadas


def test_confirmacao_espera_que_o_dispositivo_mude(falso):
    falso.detalhes[LAMPADA] = [detalhes("power", "on"), detalhes("power", "off")]

    assert dispositivos.executar("lampada", "power", "off") is True


def test_sem_confirmacao_devolve_false(falso):
    falso.detalhes[LAMPADA] = [detalhes("power", "on")]

    assert dispositivos.executar("lampada", "power", "off") is False


def test_executar_usa_os_ids_da_ultima_leitura(falso):
    dispositivos.ler(AGORA)
    falso.chamadas.clear()
    falso.detalhes[LAMPADA] = [detalhes("power", "off")]

    dispositivos.executar("lampada", "power", "off")

    assert ("get_home_devices", {}) not in falso.chamadas


@pytest.mark.parametrize(
    "dispositivo, tipo, valor",
    [
        ("porta", "power", "off"),  # a casa só comanda lâmpada e tomada
        ("lampada", "color_rgb", "255,0,0"),
        ("lampada", "power", "talvez"),
        ("tomada", "brightness", 50),  # a tomada não tem brilho
        ("lampada", "brightness", 0),
        ("lampada", "brightness", 101),
        ("lampada", "brightness", "50"),
        ("lampada", "brightness", True),
    ],
)
def test_executar_recusa_pedidos_invalidos(falso, dispositivo, tipo, valor):
    with pytest.raises(ValueError):
        dispositivos.executar(dispositivo, tipo, valor)
    assert not any(c[0] == "update_device_capabilities" for c in falso.chamadas)


# Várias threads (o ciclo lê, os pedidos da API executam)


def test_varias_threads_criam_um_so_cliente(monkeypatch):
    import threading
    import time

    criados = []

    def novo_cliente(config):
        time.sleep(0.05)  # alarga a janela em que duas threads podiam criar dois
        criados.append(config)
        return ClienteFalso()

    dispositivos.configurar(None)
    monkeypatch.setattr(dispositivos, "ClienteMCP", novo_cliente)
    monkeypatch.setattr(dispositivos.Config, "do_ambiente", classmethod(lambda cls: "config"))
    threads = [threading.Thread(target=dispositivos.ler, args=(AGORA,)) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(criados) == 1
    dispositivos.configurar(None)


def test_leituras_em_simultaneo_nao_duplicam_eventos(falso):
    import threading
    import time

    dispositivos.ler(AGORA)
    falso.casa = com_valor(falso.casa, "contactSensor", "sensorState", "normal")
    chamar = falso.chamar

    def devagar(ferramenta, argumentos=None):
        time.sleep(0.05)
        return chamar(ferramenta, argumentos)

    falso.chamar = devagar
    threads = [threading.Thread(target=dispositivos.ler, args=(AGORA,)) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(eventos.listar()) == 1


# intervalo_s()


def test_intervalo_por_omissao_e_10_segundos(monkeypatch):
    monkeypatch.delenv("POLLING_SEGUNDOS", raising=False)

    assert dispositivos.intervalo_s() == 10


def test_intervalo_configuravel(monkeypatch):
    monkeypatch.setenv("POLLING_SEGUNDOS", "30")

    assert dispositivos.intervalo_s() == 30


@pytest.mark.parametrize("texto", ["dez", "0", "-5"])
def test_intervalo_invalido(monkeypatch, texto):
    monkeypatch.setenv("POLLING_SEGUNDOS", texto)

    with pytest.raises(ValueError, match="POLLING_SEGUNDOS"):
        dispositivos.intervalo_s()


# alarme()


def test_alarme(falso):
    assert dispositivos.alarme() == "AWAY"
