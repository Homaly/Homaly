"""O cliente do servidor MCP (dispositivos.mcp), contra um Keycloak e um servidor simulados."""

import json
from pathlib import Path

import httpx
import pytest

from backend.dispositivos.mcp import ClienteMCP, Config, ErroDispositivos

DADOS = Path(__file__).parent / "dados"
CONFIG = Config(
    url="https://mcp.exemplo",
    client_id="cliente",
    client_type="tipo",
    api_key="chave",
    utilizador="equipa",
    palavra_passe="segredo",
)


def sse(mensagem: dict) -> httpx.Response:
    texto = f"event: message\ndata: {json.dumps(mensagem)}\n\n"
    return httpx.Response(200, text=texto, headers={"content-type": "text/event-stream"})


def resultado(pedido: dict, conteudo: dict) -> httpx.Response:
    return sse(
        {"jsonrpc": "2.0", "id": pedido["id"], "result": {"content": [{"type": "text", "text": json.dumps(conteudo)}]}}
    )


class Servidor:
    """Um Keycloak e um servidor MCP falsos; guarda os pedidos que recebeu."""

    def __init__(self, ferramentas: dict | None = None):
        self.ferramentas = ferramentas or {}
        self.pedidos: list[httpx.Request] = []
        self.tokens = 0
        self.sessoes = 0
        self.recusar_token: set[str] = set()  # tokens que passam a dar 401
        self.sessoes_validas: set[str] = set()

    def transporte(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.responder)

    def responder(self, pedido: httpx.Request) -> httpx.Response:
        self.pedidos.append(pedido)
        if pedido.url.path.endswith("/openid-connect/token"):
            self.tokens += 1
            return httpx.Response(200, json={"access_token": f"t{self.tokens}", "expires_in": 86400})
        token = pedido.headers.get("authorization", "").removeprefix("Bearer ")
        if token in self.recusar_token:
            return httpx.Response(401)
        corpo = json.loads(pedido.content)
        if corpo["method"] == "initialize":
            self.sessoes += 1
            sessao = f"s{self.sessoes}"
            self.sessoes_validas.add(sessao)
            r = sse({"jsonrpc": "2.0", "id": corpo["id"], "result": {"protocolVersion": "2025-06-18"}})
            r.headers["mcp-session-id"] = sessao
            return r
        if pedido.headers.get("mcp-session-id") not in self.sessoes_validas:
            return httpx.Response(404)
        if corpo["method"] == "notifications/initialized":
            return httpx.Response(202)
        nome = corpo["params"]["name"]
        resposta = self.ferramentas[nome]
        return resposta(corpo) if callable(resposta) else resultado(corpo, resposta)


def cliente(servidor: Servidor) -> ClienteMCP:
    return ClienteMCP(CONFIG, httpx.Client(transport=servidor.transporte()))


def test_chama_uma_ferramenta_e_devolve_o_json():
    servidor = Servidor({"get_home_security_status": {"status": "DISARMED"}})

    assert cliente(servidor).chamar("get_home_security_status") == {"status": "DISARMED"}


def test_le_a_resposta_real_em_stream():
    texto = (DADOS / "mcp_get_home_devices.txt").read_text()
    servidor = Servidor(
        {"get_home_devices": lambda p: httpx.Response(200, text=texto, headers={"content-type": "text/event-stream"})}
    )

    dados = cliente(servidor).chamar("get_home_devices")

    assert {d["type"] for d in dados["devices"]} >= {"contactSensor", "bulb", "plug"}


def test_prefere_structured_content():
    def resposta(p):
        return sse({"jsonrpc": "2.0", "id": p["id"], "result": {"content": [], "structuredContent": {"a": 1}}})

    assert cliente(Servidor({"x": resposta})).chamar("x") == {"a": 1}


def test_texto_que_nao_e_json_vem_como_texto():
    def resposta(p):
        return sse({"jsonrpc": "2.0", "id": p["id"], "result": {"content": [{"type": "text", "text": "Feito"}]}})

    assert cliente(Servidor({"x": resposta})).chamar("x") == {"texto": "Feito"}


def test_envia_os_cabecalhos_que_o_servidor_exige():
    servidor = Servidor({"x": {}})
    cliente(servidor).chamar("x")

    chamada = servidor.pedidos[-1]
    assert chamada.headers["user-agent"] == "homaly-backend/0.1"
    assert chamada.headers["authorization"] == "Bearer t1"
    assert chamada.headers["x-api-key"] == "chave"
    assert chamada.headers["x-client-type"] == "tipo"
    assert chamada.headers["mcp-session-id"] == "s1"
    token = servidor.pedidos[0]
    assert token.headers["user-agent"] == "homaly-backend/0.1"
    assert b"grant_type=password" in token.content


def test_reaproveita_o_token_e_a_sessao():
    servidor = Servidor({"x": {}})
    c = cliente(servidor)
    c.chamar("x")
    c.chamar("x")

    assert (servidor.tokens, servidor.sessoes) == (1, 1)


def test_token_recusado_pede_outro_e_repete():
    servidor = Servidor({"x": {"ok": True}})
    c = cliente(servidor)
    c.chamar("x")
    servidor.recusar_token.add("t1")

    assert c.chamar("x") == {"ok": True}
    assert servidor.tokens == 2


def test_sessao_recusada_abre_outra_e_repete():
    servidor = Servidor({"x": {"ok": True}})
    c = cliente(servidor)
    c.chamar("x")
    servidor.sessoes_validas.clear()

    assert c.chamar("x") == {"ok": True}
    assert servidor.sessoes == 2


def test_erro_da_ferramenta_levanta_erro_dispositivos():
    def resposta(p):
        return sse(
            {"jsonrpc": "2.0", "id": p["id"], "result": {"isError": True, "content": [{"type": "text", "text": "falhou"}]}}
        )

    with pytest.raises(ErroDispositivos, match="falhou"):
        cliente(Servidor({"x": resposta})).chamar("x")


def test_erro_json_rpc_levanta_erro_dispositivos():
    def resposta(p):
        return sse({"jsonrpc": "2.0", "id": p["id"], "error": {"code": -32602, "message": "argumentos"}})

    with pytest.raises(ErroDispositivos, match="argumentos"):
        cliente(Servidor({"x": resposta})).chamar("x")


def test_falha_de_rede_levanta_erro_dispositivos():
    def falhar(pedido):
        raise httpx.ConnectError("sem rede")

    c = ClienteMCP(CONFIG, httpx.Client(transport=httpx.MockTransport(falhar)))

    with pytest.raises(ErroDispositivos):
        c.chamar("x")


def test_pagina_html_com_200_levanta_erro_dispositivos():
    # Ex.: uma página do Cloudflare em vez da resposta do MCP.
    servidor = Servidor({"x": lambda p: httpx.Response(200, text="<html>…</html>", headers={"content-type": "text/html"})})

    with pytest.raises(ErroDispositivos):
        cliente(servidor).chamar("x")


def test_stream_partido_levanta_erro_dispositivos():
    def resposta(p):
        return httpx.Response(200, text='data: {"jsonrpc": "2.0", "id"', headers={"content-type": "text/event-stream"})

    with pytest.raises(ErroDispositivos):
        cliente(Servidor({"x": resposta})).chamar("x")


@pytest.mark.parametrize(
    "resposta",
    [
        httpx.Response(200, json={"token_type": "Bearer"}),  # sem access_token
        httpx.Response(200, text="<html>login</html>"),  # não é JSON
    ],
)
def test_token_estranho_levanta_erro_dispositivos(resposta):
    def responder(pedido):
        return resposta

    c = ClienteMCP(CONFIG, httpx.Client(transport=httpx.MockTransport(responder)))

    with pytest.raises(ErroDispositivos, match="token"):
        c.chamar("x")


def test_evento_com_varias_linhas_data_e_juntado():
    def resposta(p):
        mensagem = json.dumps({"jsonrpc": "2.0", "id": p["id"], "result": {"structuredContent": {"a": 1}}}, indent=1)
        linhas = "\n".join(f"data: {linha}" for linha in mensagem.splitlines())
        return httpx.Response(200, text=f"event: message\n{linhas}\n\n", headers={"content-type": "text/event-stream"})

    assert cliente(Servidor({"x": resposta})).chamar("x") == {"a": 1}


def test_ignora_mensagens_de_outros_pedidos_no_stream():
    def resposta(p):
        outra = {"jsonrpc": "2.0", "id": 999, "result": {"structuredContent": {"errado": True}}}
        certa = {"jsonrpc": "2.0", "id": p["id"], "result": {"structuredContent": {"certo": True}}}
        texto = f"data: {json.dumps(certa)}\n\ndata: {json.dumps(outra)}\n\n"
        return httpx.Response(200, text=texto, headers={"content-type": "text/event-stream"})

    assert cliente(Servidor({"x": resposta})).chamar("x") == {"certo": True}


def test_400_e_um_erro_do_pedido_e_nao_repete():
    servidor = Servidor({"x": lambda p: httpx.Response(400)})

    with pytest.raises(ErroDispositivos, match="400"):
        cliente(servidor).chamar("x")
    assert servidor.sessoes == 1


def test_cloudflare_403_nao_repete():
    servidor = Servidor({"x": lambda p: httpx.Response(403)})

    with pytest.raises(ErroDispositivos, match="403"):
        cliente(servidor).chamar("x")


def test_config_do_ambiente_diz_o_que_falta(monkeypatch):
    for nome in ("MCP_URL", "MCP_CLIENT_ID", "MCP_CLIENT_TYPE", "MCP_API_KEY", "KEYCLOAK_USER", "KEYCLOAK_PASSWORD"):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setenv("MCP_URL", "https://mcp.exemplo/")

    with pytest.raises(ErroDispositivos, match="MCP_API_KEY"):
        Config.do_ambiente()


def test_config_do_ambiente(monkeypatch):
    valores = {
        "MCP_URL": "https://mcp.exemplo/",
        "MCP_CLIENT_ID": "c",
        "MCP_CLIENT_TYPE": "t",
        "MCP_API_KEY": "k",
        "KEYCLOAK_USER": "u",
        "KEYCLOAK_PASSWORD": "p",
    }
    for k, v in valores.items():
        monkeypatch.setenv(k, v)

    assert Config.do_ambiente() == Config("https://mcp.exemplo", "c", "t", "k", "u", "p")
