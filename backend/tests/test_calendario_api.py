from datetime import datetime, time, timedelta
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import regras
from backend.calendario import armazem
from backend.calendario.router import obter_cliente_google, texto_compromisso, texto_ferias, texto_rotina
from backend.contexto.repositorio import carregar_contexto, guardar_rotina
from backend.dependencias import obter_agora, obter_modelo_dep
from backend.formatos import Compromisso, Periodo, Rotina
from backend.main import app
from tests.conftest import AGORA, LX, ModeloFixo
from tests.test_calendario_extrair import DENTISTA, EMPREGADA, FERIAS
from backend.calendario import router as calendario_router
from tests.test_calendario_google import TOKEN_OK, id_token

# AGORA é uma terça, 17 de novembro de 2026, às 15:00.
RESPOSTA_IA = {
    "ferias": [{"inicio": "2026-12-01", "fim": "2026-12-08", "motivo": "Férias no Algarve"}],
    "rotinas": [{"descricao": "a empregada vem", "dias": [1], "hora": "10:00"}],
    "compromissos": [{"descricao": "Dentista", "inicio": "2026-11-17T16:00", "fim": "2026-11-17T17:00"}],
}


class GoogleFalsa:
    """Responde como a Google aos pedidos de token, eventos e revogação."""

    def __init__(self):
        self.pedidos: list[httpx.Request] = []
        self.token = httpx.Response(200, json={**TOKEN_OK, "id_token": id_token("ana@gmail.com")})
        self.eventos = httpx.Response(200, json={"items": [EMPREGADA, FERIAS, DENTISTA]})
        self.revogar = httpx.Response(200)

    def __call__(self, pedido: httpx.Request) -> httpx.Response:
        self.pedidos.append(pedido)
        if pedido.url.path == "/token":
            return self.token
        if pedido.url.path == "/revoke":
            return self.revogar
        return self.eventos

    def caminhos(self) -> list[str]:
        return [p.url.path for p in self.pedidos]


@pytest.fixture
def google_falsa(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "id-teste")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "segredo-teste")
    monkeypatch.setenv("APP_URL", "https://homaly.test")
    monkeypatch.setattr(calendario_router, "_ultima_leitura_pedida", 0.0)
    falsa = GoogleFalsa()
    cliente_http = httpx.Client(transport=httpx.MockTransport(falsa))
    app.dependency_overrides[obter_cliente_google] = lambda: cliente_http
    app.dependency_overrides[obter_agora] = lambda: AGORA
    app.dependency_overrides[obter_modelo_dep] = lambda: ModeloFixo(RESPOSTA_IA)
    yield falsa
    app.dependency_overrides.clear()


@pytest.fixture
def cliente():
    return TestClient(app, follow_redirects=False)


def _ligar(cliente) -> httpx.Response:
    r = cliente.get("/calendario/google/ligar")
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    return cliente.get("/calendario/google/retorno", params={"state": state, "code": "codigo"})


def test_sem_chaves_nao_esta_configurado_e_ligar_volta_com_erro(cliente, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("APP_URL", raising=False)
    assert cliente.get("/calendario").json()["configurado"] is False
    r = cliente.get("/calendario/google/ligar")
    assert r.status_code == 303
    assert r.headers["location"] == "http://localhost:5173/definicoes?calendario=erro"


def test_ligar_manda_para_a_google(cliente, google_falsa):
    r = cliente.get("/calendario/google/ligar")
    assert r.status_code == 303
    assert r.headers["location"].startswith("https://accounts.google.com/")


def test_ligar_le_o_calendario_e_volta_a_app(cliente, google_falsa):
    r = _ligar(cliente)
    assert r.headers["location"] == "https://homaly.test/definicoes?calendario=ligado"
    assert google_falsa.caminhos() == ["/token", "/token", "/calendar/v3/calendars/primary/events"]

    estado = cliente.get("/calendario").json()
    assert estado["ligado"] and estado["email"] == "ana@gmail.com"
    assert estado["lidoEm"] == AGORA.isoformat() and estado["erro"] is None
    assert estado["itens"] == [
        {"tipo": "ferias", "texto": "Férias no Algarve: de 1 de dezembro a 8 de dezembro"},
        {"tipo": "rotina", "texto": "a empregada vem: terça-feira, às 10:00"},
        {"tipo": "compromisso", "texto": "Dentista: hoje, das 16:00 às 17:00"},
    ]


def test_o_que_vem_do_calendario_entra_no_contexto(cliente, google_falsa):
    _ligar(cliente)
    contexto = carregar_contexto(AGORA)
    assert contexto.rotinas == [Rotina("a empregada vem", [1], time(10, 0))]
    assert [c.descricao for c in contexto.compromissos] == ["Dentista"]
    assert not contexto.casa_vazia
    assert carregar_contexto(datetime(2026, 12, 3, 12, tzinfo=LX)).casa_vazia
    assert carregar_contexto(AGORA + timedelta(days=1)).compromissos == []
    # A empregada às terças às 10:00 cala a porta a abrir a essa hora (US07).
    assert regras.explicado_por_rotina(contexto, AGORA.replace(hour=10, minute=20))


def test_state_desconhecido_nao_liga(cliente, google_falsa):
    r = cliente.get("/calendario/google/retorno", params={"state": "inventado", "code": "codigo"})
    assert r.headers["location"].endswith("calendario=erro")
    assert google_falsa.pedidos == []
    assert cliente.get("/calendario").json()["ligado"] is False


def test_o_state_so_serve_uma_vez(cliente, google_falsa):
    r = cliente.get("/calendario/google/ligar")
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    cliente.get("/calendario/google/retorno", params={"state": state, "code": "codigo"})
    r = cliente.get("/calendario/google/retorno", params={"state": state, "code": "codigo"})
    assert r.headers["location"].endswith("calendario=erro")


def test_a_pessoa_cancela_na_google(cliente, google_falsa):
    r = cliente.get("/calendario/google/ligar")
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    r = cliente.get("/calendario/google/retorno", params={"state": state, "error": "access_denied"})
    assert r.headers["location"].endswith("calendario=erro")
    assert cliente.get("/calendario").json()["ligado"] is False


def test_codigo_recusado_pela_google(cliente, google_falsa):
    google_falsa.token = httpx.Response(400, json={"error": "invalid_grant"})
    assert _ligar(cliente).headers["location"].endswith("calendario=erro")
    assert cliente.get("/calendario").json()["ligado"] is False


def test_leitura_que_falha_fica_ligado_com_o_erro_e_guarda_os_itens(cliente, google_falsa):
    _ligar(cliente)
    google_falsa.token = httpx.Response(400, json={"error": "invalid_grant"})
    estado = cliente.post("/calendario/sincronizar").json()
    assert estado["ligado"]
    assert estado["erro"] == "A Google deixou de dar acesso ao calendário. Ligue outra vez."
    assert len(estado["itens"]) == 3


def test_ler_outra_vez_substitui_os_itens(cliente, google_falsa):
    _ligar(cliente)
    app.dependency_overrides[obter_modelo_dep] = lambda: ModeloFixo({"rotinas": [], "ferias": [], "compromissos": []})
    assert cliente.post("/calendario/sincronizar").json()["itens"] == []
    assert carregar_contexto(AGORA).rotinas == []


def test_sincronizar_sem_ligacao_409(cliente, google_falsa):
    assert cliente.post("/calendario/sincronizar").status_code == 409


def test_remover_revoga_e_apaga_so_o_que_veio_do_calendario(cliente, google_falsa):
    guardar_rotina(Rotina("o jardineiro vem", [2], None))  # dito no chat
    _ligar(cliente)
    estado = cliente.delete("/calendario").json()
    assert estado["ligado"] is False and estado["itens"] == []
    assert google_falsa.caminhos()[-1] == "/revoke"
    assert armazem.ligacao() is None
    assert carregar_contexto(AGORA).rotinas == [Rotina("o jardineiro vem", [2], None)]


def test_remover_apaga_mesmo_que_a_google_nao_responda(cliente, google_falsa):
    _ligar(cliente)
    google_falsa.revogar = httpx.Response(503)
    assert cliente.delete("/calendario").json()["ligado"] is False


def test_textos():
    assert texto_rotina(Rotina("ginásio", [0, 2, 4], time(8, 30))) == "ginásio: segunda-feira, quarta-feira e sexta-feira, às 08:30"
    assert texto_rotina(Rotina("passear o cão", list(range(7)), None)) == "passear o cão: todos os dias"
    assert texto_rotina(Rotina("trabalho", [0, 1, 2, 3, 4], time(9))) == "trabalho: dias úteis, às 09:00"
    um_dia = Periodo(datetime(2026, 12, 1, tzinfo=LX), datetime(2026, 12, 1, 23, tzinfo=LX), "Porto")
    assert texto_ferias(um_dia, AGORA) == "Porto: 1 de dezembro"
    amanha = Compromisso("Reunião", AGORA + timedelta(days=1), AGORA + timedelta(days=1, hours=1))
    assert texto_compromisso(amanha, AGORA) == "Reunião: amanhã, das 15:00 às 16:00"
    depois = Compromisso("Jantar", AGORA + timedelta(days=3), AGORA + timedelta(days=3, hours=2))
    assert texto_compromisso(depois, AGORA) == "Jantar: 20 de novembro, das 15:00 às 17:00"


def test_o_retorno_noutro_browser_nao_liga(cliente, google_falsa):
    """Um link de retorno feito por outra pessoa (sem o cookie de quem começou) não liga nada."""
    r = cliente.get("/calendario/google/ligar")
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    outro_browser = TestClient(app, follow_redirects=False)
    r = outro_browser.get("/calendario/google/retorno", params={"state": state, "code": "codigo-do-atacante"})
    assert r.headers["location"].endswith("calendario=erro")
    assert google_falsa.pedidos == []
    assert armazem.ligacao() is None


def test_o_cookie_do_state_e_httponly(cliente, google_falsa):
    cabecalho = cliente.get("/calendario/google/ligar").headers["set-cookie"]
    assert "HttpOnly" in cabecalho and "samesite=lax" in cabecalho.lower()


def test_uma_leitura_que_acaba_depois_de_remover_nao_traz_nada_de_volta(cliente, google_falsa):
    _ligar(cliente)
    armazem.apagar_tudo()
    assert armazem.guardar_leitura(armazem.Itens(rotinas=[Rotina("x", [1], None)]), AGORA) is False
    assert carregar_contexto(AGORA).rotinas == []


def test_ligar_outra_conta_apaga_os_itens_da_anterior(cliente, google_falsa):
    _ligar(cliente)
    armazem.guardar_ligacao("outra@gmail.com", "r2", AGORA)
    assert len(armazem.itens()) == 0


def test_acesso_negado_na_leitura_pede_para_ligar_outra_vez(cliente, google_falsa):
    _ligar(cliente)
    google_falsa.eventos = httpx.Response(403, json={})
    assert cliente.post("/calendario/sincronizar").json()["erro"].endswith("Ligue outra vez.")


def test_ler_agora_seguido_so_le_uma_vez(cliente, google_falsa):
    _ligar(cliente)
    antes = len(google_falsa.pedidos)
    cliente.post("/calendario/sincronizar")
    cliente.post("/calendario/sincronizar")
    assert len(google_falsa.pedidos) - antes == 2  # um token e uma lista de eventos


def test_a_primeira_leitura_rebenta_e_fica_ligado_com_erro(cliente, google_falsa, monkeypatch):
    def rebentar(*_a, **_k):
        raise RuntimeError("avaria")

    monkeypatch.setattr(calendario_router, "sincronizar", rebentar)
    assert _ligar(cliente).headers["location"].endswith("calendario=ligado")
    assert cliente.get("/calendario").json()["erro"] is not None
