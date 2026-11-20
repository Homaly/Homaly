"""US04: o contacto externo, o tempo de espera e o nome da casa (GET e PUT /definicoes)."""

import pytest
from fastapi.testclient import TestClient

from backend import definicoes
from backend.contrato import Contacto, Definicoes
from backend.main import app

api = TestClient(app)


def test_sem_nada_guardado_nao_ha_contacto_e_a_espera_e_cinco_minutos():
    assert api.get("/definicoes").json() == {"contacto": None, "esperaMinutos": 5}


def test_guardar_e_ler_o_contacto_o_tempo_de_espera_e_o_nome_da_casa():
    corpo = {"contacto": {"nome": "Vizinha Ana", "telemovel": "+351912345678"}, "esperaMinutos": 3, "nomeCasa": "Casa da D. Maria"}

    assert api.put("/definicoes", json=corpo).json() == corpo
    assert api.get("/definicoes").json() == corpo


def test_remover_o_contacto():
    api.put("/definicoes", json={"contacto": {"nome": "Ana", "telemovel": "912345678"}, "esperaMinutos": 5})

    api.put("/definicoes", json={"contacto": None, "esperaMinutos": 5})

    assert definicoes.obter().contacto is None


def test_espera_zero_e_valida():
    assert api.put("/definicoes", json={"contacto": None, "esperaMinutos": 0}).status_code == 200


def test_espera_de_trinta_segundos_guarda_se_como_meio_minuto():
    corpo = {"contacto": None, "esperaMinutos": 0.5}

    assert api.put("/definicoes", json=corpo).json() == corpo
    assert definicoes.obter().espera_minutos == 0.5


@pytest.mark.parametrize(
    "escrito, guardado",
    [
        ("912345678", "+351912345678"),
        ("912 345 678", "+351912345678"),
        ("+351 912 345 678", "+351912345678"),
        ("00351912345678", "+351912345678"),
        ("96-123-45-67", "+351961234567"),
        ("+34 612 345 678", "+34612345678"),  # um número estrangeiro, já com o indicativo
    ],
)
def test_o_telemovel_fica_no_formato_internacional(escrito, guardado):
    corpo = {"contacto": {"nome": "Ana", "telemovel": escrito}, "esperaMinutos": 5}

    assert api.put("/definicoes", json=corpo).json()["contacto"]["telemovel"] == guardado


@pytest.mark.parametrize(
    "corpo",
    [
        {"contacto": {"nome": "Ana", "telemovel": "12345"}, "esperaMinutos": 5},  # curto demais
        {"contacto": {"nome": "Ana", "telemovel": "212345678"}, "esperaMinutos": 5},  # fixo, não recebe SMS
        {"contacto": {"nome": "Ana", "telemovel": "91234567a"}, "esperaMinutos": 5},
        {"contacto": {"nome": "", "telemovel": "912345678"}, "esperaMinutos": 5},
        {"contacto": {"nome": "A" * 61, "telemovel": "912345678"}, "esperaMinutos": 5},
        {"contacto": None, "esperaMinutos": -1},
        {"contacto": None, "esperaMinutos": 1441},  # mais de um dia
        {"contacto": None, "esperaMinutos": 5, "nomeCasa": "C" * 61},
    ],
)
def test_recusa_definicoes_invalidas(corpo):
    r = api.put("/definicoes", json=corpo)

    assert r.status_code == 422
    assert api.get("/definicoes").json() == {"contacto": None, "esperaMinutos": 5}  # nada mudou


def test_nome_da_casa_vazio_fica_sem_nome():
    corpo = {"contacto": None, "esperaMinutos": 5, "nomeCasa": "   "}

    assert "nomeCasa" not in api.put("/definicoes", json=corpo).json()


def test_espacos_a_mais_saem():
    corpo = {"contacto": {"nome": "  Ana  ", "telemovel": "912345678"}, "esperaMinutos": 5, "nomeCasa": " Casa "}

    guardadas = api.put("/definicoes", json=corpo).json()

    assert (guardadas["contacto"]["nome"], guardadas["nomeCasa"]) == ("Ana", "Casa")


def test_obter_e_guardar_em_python():
    definicoes.guardar(Definicoes(contacto=Contacto(nome="Ana", telemovel="912345678"), espera_minutos=2))

    assert definicoes.obter().contacto == Contacto(nome="Ana", telemovel="+351912345678")
    assert definicoes.obter().espera_minutos == 2
