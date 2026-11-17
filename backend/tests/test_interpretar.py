from datetime import datetime, time

from backend.conversa.interpretar import NAO_PERCEBI, interpretar
from backend.formatos import Rotina
from tests.conftest import AGORA, LX, ModeloFixo


def test_ferias():
    modelo = ModeloFixo(
        {
            "tipo": "ferias",
            "inicio": "2026-11-18",
            "fim": "2026-11-25",
            "motivo": "férias",
            "resposta": "Boas férias! Até dia 25.",
        }
    )
    r = interpretar("vou de férias até dia 25", AGORA, modelo)
    assert r.periodo is not None
    assert r.periodo.inicio == datetime(2026, 11, 18, tzinfo=LX)
    assert r.periodo.fim == datetime(2026, 11, 25, tzinfo=LX)
    assert r.resposta == "Boas férias! Até dia 25."
    sistema, mensagem = modelo.chamadas[0]
    assert "2026-11-17" in sistema + mensagem
    assert "terça" in sistema + mensagem


def test_ferias_com_fuso_mantem_o_fuso():
    modelo = ModeloFixo(
        {
            "tipo": "ferias",
            "inicio": "2026-11-18T00:00:00+00:00",
            "fim": "2026-11-25T00:00:00+00:00",
            "motivo": "x",
            "resposta": "Ok.",
        }
    )
    r = interpretar("férias", AGORA, modelo)
    assert r.periodo is not None
    assert r.periodo.inicio.utcoffset().total_seconds() == 0


def test_rotina():
    modelo = ModeloFixo(
        {
            "tipo": "rotina",
            "descricao": "a empregada vem",
            "dias": [1],
            "hora": "14:00",
            "resposta": "Anotado.",
        }
    )
    r = interpretar("a empregada vem às terças às 14h", AGORA, modelo)
    assert r.rotina == Rotina("a empregada vem", [1], time(14, 0))
    assert r.resposta == "Anotado."


def test_rotina_sem_hora():
    modelo = ModeloFixo(
        {"tipo": "rotina", "descricao": "a empregada vem", "dias": [1], "hora": None, "resposta": "Anotado."}
    )
    r = interpretar("a empregada vem às terças", AGORA, modelo)
    assert r.rotina is not None
    assert r.rotina.hora is None


def test_aparelho():
    modelo = ModeloFixo({"tipo": "aparelho", "nome": "aquecedor", "resposta": "Combinado."})
    r = interpretar("na tomada está o aquecedor", AGORA, modelo)
    assert r.aparelho == "aquecedor"
    assert r.resposta == "Combinado."
    assert r.periodo is None and r.rotina is None


def test_aparelho_sem_nome():
    modelo = ModeloFixo({"tipo": "aparelho", "nome": "", "resposta": "Combinado."})
    assert interpretar("na tomada está", AGORA, modelo).resposta == NAO_PERCEBI


def _nao_percebeu(resposta):
    r = interpretar("blá", AGORA, ModeloFixo(resposta))
    assert r.resposta == NAO_PERCEBI
    assert r.periodo is None and r.rotina is None and r.aparelho is None


def test_nao_percebi():
    _nao_percebeu({"tipo": "nao_percebi"})


def test_tipo_desconhecido():
    _nao_percebeu({"tipo": "outra", "resposta": "x"})


def test_modelo_sem_resposta():
    _nao_percebeu(None)


def test_modelo_que_falha():
    class Avariado:
        def completar_json(self, sistema, mensagem):
            raise RuntimeError("sem rede")

    assert interpretar("olá", AGORA, Avariado()).resposta == NAO_PERCEBI


def test_resposta_vazia():
    _nao_percebeu({"tipo": "aparelho", "nome": "aquecedor", "resposta": "  "})


def test_ferias_ao_contrario():
    _nao_percebeu(
        {"tipo": "ferias", "inicio": "2026-11-25", "fim": "2026-11-18", "motivo": "x", "resposta": "Ok."}
    )


def test_dia_invalido():
    _nao_percebeu({"tipo": "rotina", "descricao": "x", "dias": [7], "hora": None, "resposta": "Ok."})


def test_dias_vazios_ou_bool():
    _nao_percebeu({"tipo": "rotina", "descricao": "x", "dias": [], "hora": None, "resposta": "Ok."})
    _nao_percebeu({"tipo": "rotina", "descricao": "x", "dias": [True], "hora": None, "resposta": "Ok."})


def test_hora_invalida():
    _nao_percebeu({"tipo": "rotina", "descricao": "x", "dias": [1], "hora": "25:99", "resposta": "Ok."})


def test_data_ilegivel():
    _nao_percebeu(
        {"tipo": "ferias", "inicio": "amanhã", "fim": "2026-11-25", "motivo": "x", "resposta": "Ok."}
    )
