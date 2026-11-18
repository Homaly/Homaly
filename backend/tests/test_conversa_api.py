from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from backend.contexto.repositorio import carregar_contexto
from backend.conversa.interpretar import NAO_PERCEBI
from backend.dependencias import obter_agora, obter_modelo_dep
from backend.main import app
from tests.conftest import AGORA, LX, ModeloFixo

FERIAS = {
    "tipo": "ferias",
    "inicio": "2026-11-18",
    "fim": "2026-11-25",
    "motivo": "férias",
    "resposta": "Boas férias! Até dia 25.",
}


@pytest.fixture
def cliente():
    yield TestClient(app)
    app.dependency_overrides.clear()


def _com(resposta):
    app.dependency_overrides[obter_modelo_dep] = lambda: ModeloFixo(resposta)
    app.dependency_overrides[obter_agora] = lambda: AGORA


def test_post_conversa_ferias_guarda_contexto(cliente):
    _com(FERIAS)
    r = cliente.post("/conversa", json={"texto": "vou de férias até dia 25"})
    assert r.status_code == 200
    assert r.json()["autor"] == "casa"
    assert r.json()["texto"] == "Boas férias! Até dia 25."
    assert carregar_contexto(datetime(2026, 11, 20, tzinfo=LX)).casa_vazia is True

    mensagens = cliente.get("/conversa").json()
    assert [m["autor"] for m in mensagens] == ["pessoa", "casa"]
    assert mensagens[0]["texto"] == "vou de férias até dia 25"


def test_post_conversa_rotina_guarda_contexto(cliente):
    _com({"tipo": "rotina", "descricao": "a empregada vem", "dias": [1], "hora": "14:00", "resposta": "Anotado."})
    assert cliente.post("/conversa", json={"texto": "a empregada vem às terças às 14h"}).status_code == 200
    assert len(carregar_contexto(AGORA).rotinas) == 1


def test_post_conversa_aparelho_guarda_contexto(cliente):
    _com({"tipo": "aparelho", "nome": "aquecedor", "resposta": "Combinado."})
    assert cliente.post("/conversa", json={"texto": "na tomada está o aquecedor"}).status_code == 200
    assert carregar_contexto(AGORA).aparelho_tomada == "aquecedor"


def test_post_conversa_nao_percebi_nao_guarda(cliente):
    _com(None)
    r = cliente.post("/conversa", json={"texto": "blá"})
    assert r.json()["texto"] == NAO_PERCEBI
    contexto = carregar_contexto(AGORA)
    assert contexto.ferias == [] and contexto.rotinas == [] and contexto.aparelho_tomada is None
    assert contexto.casa_vazia is False


def test_post_conversa_texto_vazio(cliente):
    _com(FERIAS)
    assert cliente.post("/conversa", json={"texto": "   "}).status_code == 422
    assert cliente.get("/conversa").json() == []


def test_pergunta_recebe_o_estado_da_casa(cliente):
    """O POST /conversa passa ao modelo o que a casa sabe: o contexto e os avisos ativos."""
    from backend import anomalias
    from backend.contexto import repositorio
    from backend.contrato import Anomalia

    repositorio.guardar_aparelho("aquecedor")
    anomalias.guardar(Anomalia(classe="seguranca", titulo="Porta da rua aberta", explicacao="x", detetada_em=AGORA))
    modelo = ModeloFixo({"tipo": "resposta", "resposta": "A porta da rua está aberta."})
    app.dependency_overrides[obter_modelo_dep] = lambda: modelo
    app.dependency_overrides[obter_agora] = lambda: AGORA

    r = cliente.post("/conversa", json={"texto": "está tudo bem?"})

    assert r.json()["texto"] == "A porta da rua está aberta."
    sistema, _ = modelo.chamadas[0]
    assert "Porta da rua aberta" in sistema
    assert "aquecedor" in sistema
