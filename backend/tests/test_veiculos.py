"""US13: os veículos que a casa conhece (GET, POST e DELETE /veiculos)."""

import base64

import pytest
from fastapi.testclient import TestClient

from backend import camara, veiculos
from backend.contrato import Veiculo
from backend.dependencias import obter_modelo_dep
from backend.ia.visao import Observacao
from backend.main import app
from tests.conftest import ModeloFixo

AZUL = {"veiculo": True, "tipo": "carro", "cor": "azul", "marca": "Peugeot 206",
        "matricula": "35-19-TA", "descricao": "Peugeot 206 azul de frente", "conhecido_id": None}
FOTO = base64.b64encode(b"\xff\xd8foto\xff\xd9").decode()


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(camara, "reduzir", lambda jpeg: jpeg)  # sem ffmpeg nos testes
    modelo = ModeloFixo(AZUL)
    app.dependency_overrides[obter_modelo_dep] = lambda: modelo
    yield TestClient(app), modelo
    app.dependency_overrides.clear()


def test_sem_veiculos():
    assert veiculos.listar() == []


def test_guardar_listar_apagar():
    v = veiculos.guardar(Veiculo(descricao="Carro do Rui", matricula="AA-00-BB"))
    assert veiculos.listar() == [v]
    assert veiculos.apagar(v.id) is True
    assert veiculos.listar() == []
    assert veiculos.apagar(v.id) is False


def test_registar_visto_e_ler():
    obs = Observacao(veiculo=True, descricao="Carro branco", cor="branco")
    veiculos.registar_visto("/imagens/abc.jpg", obs)
    assert veiculos.visto("/imagens/abc.jpg") == obs
    assert veiculos.visto("/imagens/outra.jpg") is None
    assert veiculos.visto(None) is None


def test_registar_por_fotografia(api):
    cliente, modelo = api
    r = cliente.post("/veiculos", json={"imagem": FOTO})
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["descricao"] == "Peugeot 206 azul" and corpo["matricula"] == "35-19-TA"
    assert modelo.imagens == [b"\xff\xd8foto\xff\xd9"]
    assert cliente.get("/veiculos").json() == [corpo]


def test_registar_com_nome_dado(api):
    cliente, _ = api
    corpo = cliente.post("/veiculos", json={"imagem": "data:image/jpeg;base64," + FOTO,
                                            "nome": "o carro do meu irmão"}).json()
    assert corpo["descricao"] == "o carro do meu irmão" and corpo["cor"] == "azul"


def test_fotografia_sem_veiculo_da_422(api):
    cliente, modelo = api
    modelo.resposta = {**AZUL, "veiculo": False}
    assert cliente.post("/veiculos", json={"imagem": FOTO}).status_code == 422
    assert veiculos.listar() == []


def test_imagem_que_nao_e_base64_da_422(api):
    cliente, _ = api
    assert cliente.post("/veiculos", json={"imagem": "isto não é base64!"}).status_code == 422


def test_apagar_pela_api(api):
    cliente, _ = api
    v = veiculos.guardar(Veiculo(descricao="Carro do Rui"))
    assert cliente.delete(f"/veiculos/{v.id}").status_code == 204
    assert cliente.delete(f"/veiculos/{v.id}").status_code == 404
