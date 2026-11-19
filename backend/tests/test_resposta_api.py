import sys
import types
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from backend import anomalias, db, regras
from backend.contexto.repositorio import apagar_proposta, carregar_contexto, ler_proposta, rotinas_recusadas
from backend.contrato import Anomalia
from backend.dependencias import obter_agora
from backend.main import app
from backend.resposta.router import _publicar, obter_publicar
from tests.conftest import AGORA

# AGORA é uma terça às 15:00.
SEMANA = timedelta(days=7)
BEM = "Está tudo bem"


@pytest.fixture
def cliente():
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def publicadas():
    publicadas: list[Anomalia] = []

    def publicar(a: Anomalia) -> None:
        anomalias.guardar(a)
        publicadas.append(a)

    app.dependency_overrides[obter_publicar] = lambda: publicar
    app.dependency_overrides[obter_agora] = lambda: AGORA
    return publicadas


def _anomalia(us="US07", detetada_em=AGORA, estado="ativa") -> Anomalia:
    a = Anomalia(classe="seguranca", titulo="A porta abriu", explicacao="x", detetada_em=detetada_em, estado=estado)
    anomalias.guardar(a)
    with db.ligar() as con:
        con.execute("INSERT INTO anomalia_us (anomalia_id, us) VALUES (?, ?)", (a.id, us))
    return a


def _terceira_terca(us="US07") -> Anomalia:
    """Dois avisos iguais nas terças anteriores (já resolvidos) e o de hoje, por responder."""
    _anomalia(us, AGORA - SEMANA, "resolvida")
    _anomalia(us, AGORA - 2 * SEMANA, "resolvida")
    return _anomalia(us)


def _responder(cliente, a, texto=BEM):
    return cliente.post(f"/anomalias/{a.id}/resposta", json={"texto": texto})


def _decidir(cliente, a, aceitar):
    return cliente.post(f"/anomalias/{a.id}/silencio", json={"aceitar": aceitar})


def test_a_primeira_vez_so_resolve(cliente, publicadas):
    a = _anomalia()
    r = _responder(cliente, a)
    assert r.status_code == 200
    assert r.json()["estado"] == "resolvida"
    assert r.json()["resposta"]["texto"] == BEM
    assert "propostaSilencio" not in r.json()
    assert ler_proposta(a.id) is None
    assert len(publicadas) == 1


def test_a_terceira_vez_propoe_e_aceitar_guarda_a_rotina(cliente, publicadas):
    a = _terceira_terca()
    r = _responder(cliente, a)
    assert r.status_code == 200
    assert r.json()["propostaSilencio"]["estado"] == "pendente"
    assert ler_proposta(a.id)["tipo"] == "rotina"
    assert carregar_contexto(AGORA).rotinas == []

    r = _decidir(cliente, a, True)
    assert r.status_code == 200
    assert r.json()["propostaSilencio"]["estado"] == "aceite"
    assert len(publicadas) == 2
    assert ler_proposta(a.id) is None
    rotinas = carregar_contexto(AGORA).rotinas
    assert [(r.descricao, r.dias, f"{r.hora:%H:%M}") for r in rotinas] == [("a porta abre a esta hora", [1], "15:00")]


def test_a_rotina_aceite_cala_o_proximo_aviso_igual(cliente, publicadas):
    a = _terceira_terca()
    _responder(cliente, a)
    _decidir(cliente, a, True)
    seguinte = AGORA + SEMANA + timedelta(minutes=20)
    assert regras.explicado_por_rotina(carregar_contexto(seguinte), seguinte)


def test_avisos_de_outra_historia_nao_contam(cliente, publicadas):
    _anomalia("US09", AGORA - SEMANA, "resolvida")
    _anomalia("US09", AGORA - 2 * SEMANA, "resolvida")
    a = _anomalia("US07")
    assert "propostaSilencio" not in _responder(cliente, a).json()


def test_recusar_guarda_a_recusa_e_nao_volta_a_propor(cliente, publicadas):
    a = _terceira_terca()
    _responder(cliente, a)
    r = _decidir(cliente, a, False)
    assert r.status_code == 200
    assert r.json()["propostaSilencio"]["estado"] == "recusada"
    assert carregar_contexto(AGORA).rotinas == []
    assert len(rotinas_recusadas()) == 1
    assert anomalias.obter(a.id).proposta_silencio.estado == "recusada"

    # Na terça seguinte, o mesmo aviso já não traz proposta.
    app.dependency_overrides[obter_agora] = lambda: AGORA + SEMANA
    seguinte = _anomalia("US07", AGORA + SEMANA)
    assert "propostaSilencio" not in _responder(cliente, seguinte).json()


def test_responder_duas_vezes_409(cliente, publicadas):
    a = _anomalia()
    assert _responder(cliente, a).status_code == 200
    assert _responder(cliente, a).status_code == 409
    assert len(publicadas) == 1


def test_decidir_sem_proposta_409(cliente, publicadas):
    a = _anomalia()
    assert _decidir(cliente, a, True).status_code == 409
    _responder(cliente, a)
    assert _decidir(cliente, a, True).status_code == 409


def test_decidir_sem_proposta_guardada_409(cliente, publicadas):
    a = _terceira_terca()
    _responder(cliente, a)
    apagar_proposta(a.id)
    assert _decidir(cliente, a, True).status_code == 409


def test_aceitar_duas_vezes_409(cliente, publicadas):
    a = _terceira_terca()
    _responder(cliente, a)
    assert _decidir(cliente, a, True).status_code == 200
    assert _decidir(cliente, a, True).status_code == 409
    assert len(carregar_contexto(AGORA).rotinas) == 1


def test_anomalia_inexistente_404(cliente, publicadas):
    assert cliente.post("/anomalias/nao-existe/resposta", json={"texto": "x"}).status_code == 404
    assert cliente.post("/anomalias/nao-existe/silencio", json={"aceitar": True}).status_code == 404
    assert publicadas == []


@pytest.mark.parametrize("texto", ["", "   "])
def test_texto_vazio_422(cliente, publicadas, texto):
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


def test_esta_tudo_bem_num_aviso_com_acao_nao_cala_o_resto_do_dia(cliente, publicadas):
    """Fecha só este aviso: se voltar a acontecer no mesmo dia, a casa pergunta outra vez."""
    a = Anomalia(classe="eficiencia", titulo="Aparelho ligado há 3 h", explicacao="x", detetada_em=AGORA)
    anomalias.guardar(a)
    with db.ligar() as con:
        con.execute("INSERT INTO anomalia_us (anomalia_id, us) VALUES (?, ?)", (a.id, "US14"))
    r = _responder(cliente, a)
    assert r.json()["estado"] == "resolvida"
    assert carregar_contexto(AGORA).silencios == []
