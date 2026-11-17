"""Os pedidos /dev: anomalias à mão, e com ?contacto=true também a SMS ao contacto externo (US05)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend import definicoes, dev
from backend.contacto_externo import envios
from backend.contrato import Contacto, Definicoes

app = FastAPI()
app.include_router(dev.router)
api = TestClient(app)

PORTA = {"classe": "seguranca", "titulo": "Porta aberta", "explicacao": "A porta está aberta há 6 min."}


@pytest.fixture(autouse=True)
def com_contacto():
    definicoes.guardar(Definicoes(contacto=Contacto(nome="Ana", telemovel="912345678"), espera_minutos=1))


def test_por_omissao_nao_avisa_o_contacto():
    r = api.post("/dev/anomalias", json=PORTA)

    assert r.status_code == 200
    assert envios.obter(r.json()["id"]) is None


def test_com_contacto_agenda_a_sms_como_o_ciclo():
    r = api.post("/dev/anomalias?contacto=true&us=US08", json=PORTA)

    envio = envios.obter(r.json()["id"])
    assert envio is not None and envio.estado == "pendente"


def test_o_exemplo_nunca_avisa_o_contacto():
    api.post("/dev/exemplo")

    assert envios.obter("exemplo-porta") is None
