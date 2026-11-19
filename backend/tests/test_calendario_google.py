import base64
import json
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from backend.calendario import google
from tests.conftest import AGORA

CRED = google.Credenciais("id-teste", "segredo-teste", "http://localhost:8000/calendario/google/retorno")


def id_token(email: str) -> str:
    carga = base64.urlsafe_b64encode(json.dumps({"email": email}).encode()).decode().rstrip("=")
    return f"cabecalho.{carga}.assinatura"


def cliente(tratar):
    pedidos: list[httpx.Request] = []

    def guardar(pedido: httpx.Request) -> httpx.Response:
        pedidos.append(pedido)
        return tratar(pedido)

    return httpx.Client(transport=httpx.MockTransport(guardar)), pedidos


def test_credenciais_vem_do_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "segredo")
    monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)
    assert google.credenciais() == google.Credenciais("id", "segredo", google.REDIRECT_POR_OMISSAO)


def test_sem_segredo_nao_ha_credenciais(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id")
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    assert google.credenciais() is None


TOKEN_OK = {"refresh_token": "r1", "access_token": "a1", "scope": f"openid {google.PERMISSAO_CALENDARIO}"}


def test_url_autorizar_pede_so_leitura_e_acesso_continuo():
    url = urlparse(google.url_autorizar(CRED, "abc", "verificador"))
    q = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert url.netloc == "accounts.google.com"
    assert q["client_id"] == "id-teste"
    assert q["redirect_uri"] == CRED.redirect_uri
    assert q["state"] == "abc"
    assert q["access_type"] == "offline"
    assert q["prompt"] == "consent"
    assert "calendar.readonly" in q["scope"] and "email" in q["scope"]
    assert q["code_challenge_method"] == "S256" and q["code_challenge"] != "verificador"
    assert "segredo" not in google.url_autorizar(CRED, "abc", "verificador")


def test_trocar_codigo_da_o_refresh_token_e_o_email():
    c, pedidos = cliente(lambda _: httpx.Response(200, json={**TOKEN_OK, "id_token": id_token("ana@gmail.com")}))
    assert google.trocar_codigo(CRED, "codigo", "verificador", cliente=c) == google.Ligacao("r1", "ana@gmail.com")
    corpo = parse_qs(pedidos[0].content.decode())
    assert corpo["code"] == ["codigo"] and corpo["grant_type"] == ["authorization_code"]
    assert corpo["code_verifier"] == ["verificador"]
    assert corpo["redirect_uri"] == [CRED.redirect_uri]


def test_trocar_codigo_sem_refresh_token_falha():
    c, _ = cliente(lambda _: httpx.Response(200, json={"access_token": "a1"}))
    with pytest.raises(google.ErroGoogle):
        google.trocar_codigo(CRED, "codigo", "v", cliente=c)


def test_sem_permissao_do_calendario_revoga_e_falha():
    c, pedidos = cliente(lambda p: httpx.Response(200, json={**TOKEN_OK, "scope": "openid email"}))
    with pytest.raises(google.ErroGoogle, match="permissão"):
        google.trocar_codigo(CRED, "codigo", "v", cliente=c)
    assert pedidos[-1].url.path == "/revoke"


def test_codigo_recusado_diz_o_motivo_sem_segredos():
    c, _ = cliente(lambda _: httpx.Response(400, json={"error": "invalid_grant"}))
    with pytest.raises(google.ErroGoogle, match="invalid_grant") as erro:
        google.trocar_codigo(CRED, "codigo", "v", cliente=c)
    assert "segredo" not in str(erro.value)


def test_id_token_estragado_fica_sem_email():
    c, _ = cliente(lambda _: httpx.Response(200, json={**TOKEN_OK, "id_token": "nao-e-jwt"}))
    assert google.trocar_codigo(CRED, "codigo", "v", cliente=c).email is None


def test_token_de_acesso():
    c, pedidos = cliente(lambda _: httpx.Response(200, json={"access_token": "a2"}))
    assert google.token_de_acesso(CRED, "r1", cliente=c) == "a2"
    assert parse_qs(pedidos[0].content.decode())["grant_type"] == ["refresh_token"]


def test_google_em_baixo_e_erro_google():
    def cair(_):
        raise httpx.ConnectError("sem rede")

    c, _ = cliente(cair)
    with pytest.raises(google.ErroGoogle):
        google.token_de_acesso(CRED, "r1", cliente=c)


def test_listar_eventos_pede_as_repeticoes_como_um_so_e_tira_os_cancelados():
    itens = [{"summary": "Empregada", "status": "confirmed"}, {"summary": "Antigo", "status": "cancelled"}]
    c, pedidos = cliente(lambda _: httpx.Response(200, json={"items": itens}))
    eventos = google.listar_eventos("a1", AGORA, AGORA + timedelta(days=90), cliente=c)
    assert [e["summary"] for e in eventos] == ["Empregada"]
    assert pedidos[0].headers["Authorization"] == "Bearer a1"
    assert pedidos[0].url.params["singleEvents"] == "false"
    assert pedidos[0].url.params["timeMin"] == AGORA.isoformat()


def test_listar_eventos_recusado():
    c, _ = cliente(lambda _: httpx.Response(401, json={}))
    with pytest.raises(google.ErroGoogle, match="401"):
        google.listar_eventos("a1", AGORA, AGORA, cliente=c)


def test_revogar():
    c, pedidos = cliente(lambda _: httpx.Response(200))
    assert google.revogar("r1", cliente=c)
    assert parse_qs(pedidos[0].content.decode())["token"] == ["r1"]
    c, _ = cliente(lambda _: httpx.Response(400))
    assert not google.revogar("r1", cliente=c)


def test_convites_por_aceitar_ou_recusados_ficam_de_fora():
    def convite(titulo, resposta):
        return {"summary": titulo, "attendees": [{"email": "x@y.pt", "self": True, "responseStatus": resposta}]}

    itens = [convite("Aceite", "accepted"), convite("Por responder", "needsAction"), convite("Recusado", "declined")]
    c, _ = cliente(lambda _: httpx.Response(200, json={"items": itens}))
    assert [e["summary"] for e in google.listar_eventos("a1", AGORA, AGORA, cliente=c)] == ["Aceite"]


def test_listar_eventos_segue_as_paginas():
    paginas = {None: {"items": [{"summary": "1"}], "nextPageToken": "p2"}, "p2": {"items": [{"summary": "2"}]}}
    c, pedidos = cliente(lambda p: httpx.Response(200, json=paginas[p.url.params.get("pageToken")]))
    assert [e["summary"] for e in google.listar_eventos("a1", AGORA, AGORA, cliente=c)] == ["1", "2"]
    assert len(pedidos) == 2
