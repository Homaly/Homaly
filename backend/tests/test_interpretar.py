from datetime import date, datetime, time

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
    # "até dia 25": o dia 25 conta todo, não só a meia-noite.
    assert r.periodo.fim == datetime.combine(date(2026, 11, 25), time.max, tzinfo=LX)
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


def _ferias(inicio, fim):
    modelo = ModeloFixo({"tipo": "ferias", "inicio": inicio, "fim": fim, "motivo": "", "resposta": "Ok."})
    return interpretar("férias", AGORA, modelo).periodo


def test_ferias_ate_domingo_contam_o_domingo_todo():
    periodo = _ferias("2026-11-17", "2026-11-22")
    domingo_a_tarde = datetime(2026, 11, 22, 15, 0, tzinfo=LX)
    assert periodo.inicio <= domingo_a_tarde <= periodo.fim
    assert periodo.fim < datetime(2026, 11, 23, tzinfo=LX)


def test_ferias_so_hoje():
    periodo = _ferias("2026-11-17", "2026-11-17")
    assert periodo is not None
    assert periodo.inicio <= AGORA <= periodo.fim


def test_ferias_a_partir_de_uma_hora():
    # "a partir de hoje à tarde": de manhã a casa ainda não está vazia.
    periodo = _ferias("2026-11-17T14:00", "2026-11-22")
    assert periodo.inicio == datetime(2026, 11, 17, 14, 0, tzinfo=LX)
    assert not periodo.inicio <= datetime(2026, 11, 17, 11, 0, tzinfo=LX) <= periodo.fim


def test_ferias_com_hora_de_fim_fica_essa_hora():
    periodo = _ferias("2026-11-17", "2026-11-22T18:00")
    assert periodo.fim == datetime(2026, 11, 22, 18, 0, tzinfo=LX)


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


# Perguntas: a casa responde com o que sabe e não guarda nada.


def test_pergunta_responde_sem_guardar():
    i = interpretar("a porta está fechada?", AGORA, ModeloFixo({"tipo": "resposta", "resposta": "Está fechada."}))
    assert i.resposta == "Está fechada."
    assert (i.periodo, i.rotina, i.aparelho) == (None, None, None)


def test_pergunta_sem_texto_nao_percebe():
    _nao_percebeu({"tipo": "resposta", "resposta": "  "})


def test_o_estado_da_casa_vai_para_o_modelo():
    modelo = ModeloFixo({"tipo": "resposta", "resposta": "x"})
    interpretar("está frio?", AGORA, modelo, estado={"sensores": {"temperatura": "14 °C"}})
    sistema, _ = modelo.chamadas[0]
    assert '"temperatura": "14 °C"' in sistema


def test_o_prompt_proibe_dizer_que_fez_alguma_coisa():
    modelo = ModeloFixo({"tipo": "nao_percebi"})
    interpretar("apaga a luz", AGORA, modelo)
    sistema, _ = modelo.chamadas[0]
    assert "Nunca digas que fizeste" in sistema
