"""O envio de SMS pelo textbee (contacto_externo.sms), com o servidor simulado."""

import json

import httpx
import pytest

from backend.contacto_externo import sms


@pytest.fixture(autouse=True)
def sem_textbee(monkeypatch):
    monkeypatch.delenv("TEXTBEE_API_KEY", raising=False)
    monkeypatch.delenv("TEXTBEE_DEVICE_ID", raising=False)
    monkeypatch.delenv("SMS_MAXIMO_HORA", raising=False)
    sms.limpar_falsas()
    sms.limpar_limite()


def textbee(monkeypatch, responder):
    pedidos: list[httpx.Request] = []

    def guardar(pedido):
        pedidos.append(pedido)
        return responder(pedido)

    monkeypatch.setenv("TEXTBEE_API_KEY", "chave-teste")
    monkeypatch.setattr(sms, "_http", lambda: httpx.Client(transport=httpx.MockTransport(guardar)))
    return pedidos


def test_envia_pelo_textbee(monkeypatch):
    pedidos = textbee(monkeypatch, lambda p: httpx.Response(201, json={"data": {"success": True}}))

    sms.enviar("+351912345678", "Olá")

    [pedido] = pedidos
    assert str(pedido.url) == "https://api.textbee.dev/api/v1/gateway/send-sms"
    assert pedido.headers["x-api-key"] == "chave-teste"
    assert json.loads(pedido.content) == {"recipients": ["+351912345678"], "message": "Olá"}
    assert sms.falsas() == []


def test_com_device_id_escolhe_o_telemovel(monkeypatch):
    pedidos = textbee(monkeypatch, lambda p: httpx.Response(201, json={}))
    monkeypatch.setenv("TEXTBEE_DEVICE_ID", "telemovel-1")

    sms.enviar("+351912345678", "Olá")

    assert json.loads(pedidos[0].content)["deviceId"] == "telemovel-1"


@pytest.mark.parametrize("estado", [400, 401, 500])
def test_textbee_recusa_levanta_erro(monkeypatch, estado):
    textbee(monkeypatch, lambda p: httpx.Response(estado, json={"error": "x"}))

    with pytest.raises(sms.ErroSMS, match=str(estado)):
        sms.enviar("+351912345678", "Olá")


def test_falha_de_rede_levanta_erro(monkeypatch):
    def falhar(pedido):
        raise httpx.ConnectError("sem rede")

    textbee(monkeypatch, falhar)

    with pytest.raises(sms.ErroSMS):
        sms.enviar("+351912345678", "Olá")


def test_sem_textbee_a_sms_fica_so_registada():
    sms.enviar("+351912345678", "Olá")

    [falsa] = sms.falsas()
    assert (falsa["para"], falsa["texto"]) == ("+351912345678", "Olá")


def test_a_chave_nunca_aparece_no_erro(monkeypatch):
    textbee(monkeypatch, lambda p: httpx.Response(401, text="chave-teste inválida"))

    with pytest.raises(sms.ErroSMS) as erro:
        sms.enviar("+351912345678", "Olá")
    assert "chave-teste" not in str(erro.value)


def aceita(pedido):
    return httpx.Response(201, json={"data": {"success": True}})


def texto(pedido: httpx.Request) -> str:
    return json.loads(pedido.content)["message"]


def test_no_maximo_sms_maximo_hora_por_hora(monkeypatch):
    monkeypatch.setenv("SMS_MAXIMO_HORA", "2")
    pedidos = textbee(monkeypatch, aceita)
    agora = [1000.0]
    monkeypatch.setattr(sms, "_relogio", lambda: agora[0])
    sms.enviar("+351912345678", "1")
    sms.enviar("+351912345678", "2")

    with pytest.raises(sms.LimiteSMS, match="limite"):
        sms.enviar("+351912345678", "3")

    agora[0] += 3601  # passou uma hora
    sms.enviar("+351912345678", "4")
    assert [texto(p) for p in pedidos] == ["1", "2", "4"]


def test_por_omissao_o_limite_e_dez(monkeypatch):
    textbee(monkeypatch, aceita)
    monkeypatch.setattr(sms, "_relogio", lambda: 1000.0)
    for i in range(10):
        sms.enviar("+351912345678", str(i))

    with pytest.raises(sms.LimiteSMS, match="limite"):
        sms.enviar("+351912345678", "11")


def test_o_limite_e_um_erro_de_sms():
    assert issubclass(sms.LimiteSMS, sms.ErroSMS)


def test_sem_chave_nao_gasta_o_limite(monkeypatch):
    # Sem textbee não sai SMS nenhuma, por isso não se gasta tarifário.
    monkeypatch.setenv("SMS_MAXIMO_HORA", "1")
    monkeypatch.setattr(sms, "_relogio", lambda: 1000.0)
    for i in range(3):
        sms.enviar("+351912345678", str(i))

    assert len(sms.falsas()) == 3


def test_uma_sms_que_o_textbee_recusa_nao_gasta_o_limite(monkeypatch):
    monkeypatch.setenv("SMS_MAXIMO_HORA", "1")
    monkeypatch.setattr(sms, "_relogio", lambda: 1000.0)
    respostas = iter([httpx.Response(500), httpx.Response(201)])
    pedidos = textbee(monkeypatch, lambda p: next(respostas))

    with pytest.raises(sms.ErroSMS):
        sms.enviar("+351912345678", "falha")
    sms.enviar("+351912345678", "passa")

    assert [texto(p) for p in pedidos] == ["falha", "passa"]


def test_uma_sms_sem_ligacao_ao_textbee_nao_gasta_o_limite(monkeypatch):
    monkeypatch.setenv("SMS_MAXIMO_HORA", "1")
    monkeypatch.setattr(sms, "_relogio", lambda: 1000.0)
    tentativas = iter([httpx.ConnectError("sem rede"), None])

    def responder(pedido):
        erro = next(tentativas)
        if erro:
            raise erro
        return httpx.Response(201)

    textbee(monkeypatch, responder)
    with pytest.raises(sms.ErroSMS):
        sms.enviar("+351912345678", "falha")
    sms.enviar("+351912345678", "passa")  # não levanta LimiteSMS


def test_limite_invalido_diz_qual(monkeypatch):
    monkeypatch.setenv("SMS_MAXIMO_HORA", "muitas")

    with pytest.raises(ValueError, match="SMS_MAXIMO_HORA"):
        sms.enviar("+351912345678", "Olá")
