import sys
import types

import pytest
from fastapi.testclient import TestClient

from backend import anomalias, db
from backend.contexto.repositorio import carregar_contexto, ler_proposta
from backend.contrato import Anomalia
from backend.dependencias import obter_agora, obter_modelo_dep
from backend.formatos import Desvio
from backend.ia import avaliar
from backend.main import app
from backend.resposta.router import _publicar, obter_publicar
from tests.conftest import AGORA, ModeloFixo

TEMPORARIO = {"motivo": "temporario", "rotina": None}
ROTINA = {"descricao": "a empregada vem às terças", "dias": [1], "hora": "14:00"}


@pytest.fixture
def cliente():
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def publicadas():
    return []


def _com(publicadas, resposta):
    def publicar(a: Anomalia) -> None:
        anomalias.guardar(a)
        publicadas.append(a)

    app.dependency_overrides[obter_publicar] = lambda: publicar
    app.dependency_overrides[obter_modelo_dep] = lambda: ModeloFixo(resposta)
    app.dependency_overrides[obter_agora] = lambda: AGORA


def _anomalia(classe="bem_estar") -> Anomalia:
    a = Anomalia(classe=classe, titulo="A porta não abriu", explicacao="x", detetada_em=AGORA)
    anomalias.guardar(a)
    with db.ligar() as con:
        con.execute("INSERT INTO anomalia_us (anomalia_id, us) VALUES (?, 'US09')", (a.id,))
    return a


def _responder(cliente, a, texto="hoje é excecional"):
    return cliente.post(f"/anomalias/{a.id}/resposta", json={"texto": texto})


def test_resposta_e_aceitar_silencio(cliente, publicadas):
    _com(publicadas, TEMPORARIO)
    a = _anomalia()
    r = _responder(cliente, a)
    assert r.status_code == 200
    assert r.json()["estado"] == "resolvida"
    assert r.json()["propostaSilencio"]["estado"] == "pendente"
    assert len(publicadas) == 1
    assert publicadas[0].estado == "resolvida"
    assert ler_proposta(a.id)["tipo"] == "silencio"
    assert carregar_contexto(AGORA).silencios == []

    r = cliente.post(f"/anomalias/{a.id}/silencio", json={"aceitar": True})
    assert r.status_code == 200
    assert r.json()["propostaSilencio"]["estado"] == "aceite"
    assert len(publicadas) == 2
    assert ler_proposta(a.id) is None
    desvio = Desvio(us="US09", classe="bem_estar", resumo="A porta não abriu.", habitual=None)
    assert avaliar(desvio, carregar_contexto(AGORA), agora=AGORA, modelo=ModeloFixo(None)) is None


def test_resposta_recorrente_aceitar_guarda_rotina(cliente, publicadas):
    _com(publicadas, {"motivo": "recorrente", "rotina": ROTINA})
    a = _anomalia()
    assert _responder(cliente, a, "a empregada vem às terças").status_code == 200
    assert cliente.post(f"/anomalias/{a.id}/silencio", json={"aceitar": True}).status_code == 200
    contexto = carregar_contexto(AGORA)
    assert [r.descricao for r in contexto.rotinas] == ["a empregada vem às terças"]
    assert contexto.silencios == []


def test_resposta_sem_proposta(cliente, publicadas):
    _com(publicadas, {"motivo": "nenhum"})
    a = _anomalia()
    r = _responder(cliente, a, "está tudo bem")
    assert r.status_code == 200
    assert "propostaSilencio" not in r.json()
    assert r.json()["resposta"]["texto"] == "está tudo bem"
    assert ler_proposta(a.id) is None
    assert len(publicadas) == 1


def test_recusar_silencio_nao_aplica(cliente, publicadas):
    _com(publicadas, TEMPORARIO)
    a = _anomalia()
    _responder(cliente, a)
    r = cliente.post(f"/anomalias/{a.id}/silencio", json={"aceitar": False})
    assert r.status_code == 200
    assert r.json()["propostaSilencio"]["estado"] == "recusada"
    assert carregar_contexto(AGORA).silencios == []
    assert ler_proposta(a.id) is None
    assert len(publicadas) == 2
    assert anomalias.obter(a.id).proposta_silencio.estado == "recusada"


def test_responder_duas_vezes_409(cliente, publicadas):
    _com(publicadas, TEMPORARIO)
    a = _anomalia()
    assert _responder(cliente, a).status_code == 200
    assert _responder(cliente, a).status_code == 409
    assert len(publicadas) == 1


def test_silencio_sem_proposta_409(cliente, publicadas):
    _com(publicadas, {"motivo": "nenhum"})
    a = _anomalia()
    assert cliente.post(f"/anomalias/{a.id}/silencio", json={"aceitar": True}).status_code == 409
    _responder(cliente, a)
    assert cliente.post(f"/anomalias/{a.id}/silencio", json={"aceitar": True}).status_code == 409


def test_silencio_sem_proposta_guardada_409(cliente, publicadas):
    _com(publicadas, TEMPORARIO)
    a = _anomalia()
    _responder(cliente, a)
    from backend.contexto.repositorio import apagar_proposta

    apagar_proposta(a.id)
    assert cliente.post(f"/anomalias/{a.id}/silencio", json={"aceitar": True}).status_code == 409


def test_aceitar_duas_vezes_409(cliente, publicadas):
    _com(publicadas, TEMPORARIO)
    a = _anomalia()
    _responder(cliente, a)
    assert cliente.post(f"/anomalias/{a.id}/silencio", json={"aceitar": True}).status_code == 200
    assert cliente.post(f"/anomalias/{a.id}/silencio", json={"aceitar": True}).status_code == 409
    assert len(carregar_contexto(AGORA).silencios) == 1


def test_anomalia_inexistente_404(cliente, publicadas):
    _com(publicadas, TEMPORARIO)
    assert cliente.post("/anomalias/nao-existe/resposta", json={"texto": "x"}).status_code == 404
    assert cliente.post("/anomalias/nao-existe/silencio", json={"aceitar": True}).status_code == 404
    assert publicadas == []


@pytest.mark.parametrize("texto", ["", "   "])
def test_texto_vazio_422(cliente, publicadas, texto):
    _com(publicadas, TEMPORARIO)
    a = _anomalia()
    assert _responder(cliente, a, texto).status_code == 422
    assert anomalias.obter(a.id).estado == "ativa"


def test_obter_publicar_sem_avisos_e_o_por_omissao(monkeypatch):
    monkeypatch.setitem(sys.modules, "backend.avisos", None)  # como se o avisos.py não existisse
    assert obter_publicar() is _publicar


def test_obter_publicar_usa_avisos_quando_existe(monkeypatch):
    def publicar(a: Anomalia) -> None: ...

    monkeypatch.setitem(sys.modules, "backend.avisos", types.SimpleNamespace(publicar=publicar))
    assert obter_publicar() is publicar
