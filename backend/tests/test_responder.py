from datetime import datetime

from backend.contexto.repositorio import carregar_contexto
from backend.contrato import Anomalia
from backend.formatos import Rotina
from backend.resposta.responder import aplicar, responder
from tests.conftest import AGORA, LX, ModeloFixo

ROTINA = {"descricao": "a empregada vem às terças à tarde", "dias": [1], "hora": "14:00"}


def anomalia(classe="bem_estar") -> Anomalia:
    return Anomalia(
        classe=classe, titulo="A porta não abriu", explicacao="Ninguém abriu a porta.", detetada_em=AGORA
    )


def test_sem_motivo_resolve_sem_proposta():
    d = responder(anomalia(), "US09", "está tudo bem", AGORA, ModeloFixo({"motivo": "nenhum", "rotina": None}))
    assert d.anomalia.estado == "resolvida"
    assert d.anomalia.resposta.texto == "está tudo bem"
    assert d.anomalia.resposta.em == AGORA
    assert d.anomalia.resolucao.texto == "Resolvida com a resposta «está tudo bem»"
    assert d.anomalia.proposta_silencio is None
    assert d.proposta is None


def test_modelo_sem_resposta_resolve_sem_proposta():
    d = responder(anomalia(), "US09", "está tudo bem", AGORA, ModeloFixo(None))
    assert d.anomalia.estado == "resolvida"
    assert d.anomalia.proposta_silencio is None
    assert d.proposta is None


def test_modelo_com_motivo_invalido_resolve_sem_proposta():
    for resposta in ({"motivo": "talvez"}, {"motivo": 3}, {"rotina": None}, ["temporario"]):
        d = responder(anomalia(), "US09", "x", AGORA, ModeloFixo(resposta))
        assert d.anomalia.estado == "resolvida"
        assert d.proposta is None


def test_modelo_que_falha_resolve_sem_proposta():
    class Falha:
        def completar_json(self, sistema, mensagem):
            raise RuntimeError("sem rede")

    d = responder(anomalia(), "US09", "x", AGORA, Falha())
    assert d.anomalia.estado == "resolvida"
    assert d.proposta is None


def test_pergunta_ao_modelo_leva_anomalia_e_texto():
    modelo = ModeloFixo(None)
    responder(anomalia(), "US09", "a empregada vem às terças", AGORA, modelo)
    sistema, mensagem = modelo.chamadas[0]
    assert "A porta não abriu" in mensagem
    assert "a empregada vem às terças" in mensagem
    assert "recorrente" in sistema


def test_temporario_propoe_silencio_ate_fim_do_dia():
    d = responder(anomalia(), "US09", "hoje é excecional", AGORA, ModeloFixo({"motivo": "temporario"}))
    p = d.anomalia.proposta_silencio
    assert p.ate == datetime(2026, 11, 17, 23, 59, 59, tzinfo=LX)
    assert p.estado == "pendente"
    assert "«A porta não abriu»" in p.texto
    assert d.proposta == {
        "tipo": "silencio",
        "us": "US09",
        "ate": "2026-11-17T23:59:59+00:00",
        "motivo": "hoje é excecional",
    }


def test_temporario_sem_us_nao_propoe():
    d = responder(anomalia(), None, "x", AGORA, ModeloFixo({"motivo": "temporario"}))
    assert d.anomalia.proposta_silencio is None
    assert d.proposta is None


def test_temporario_em_seguranca_nao_propoe():
    d = responder(anomalia("seguranca"), "US09", "x", AGORA, ModeloFixo({"motivo": "temporario"}))
    assert d.anomalia.proposta_silencio is None
    assert d.proposta is None


def test_recorrente_propoe_rotina():
    d = responder(anomalia(), "US09", "a empregada vem às terças", AGORA, ModeloFixo({"motivo": "recorrente", "rotina": ROTINA}))
    assert d.proposta == {"tipo": "rotina", **ROTINA}
    p = d.anomalia.proposta_silencio
    assert p.estado == "pendente"
    assert p.texto == (
        "Passo a contar com isto: a empregada vem às terças à tarde. Não aviso enquanto não o removeres, ok?"
    )
    assert p.ate.year == 2036


def test_recorrente_em_seguranca_propoe():
    d = responder(anomalia("seguranca"), "US09", "x", AGORA, ModeloFixo({"motivo": "recorrente", "rotina": ROTINA}))
    assert d.proposta["tipo"] == "rotina"
    assert d.anomalia.proposta_silencio is not None


def test_recorrente_com_rotina_invalida_nao_propoe():
    for rotina in (None, {"descricao": "x", "dias": [9], "hora": None}, "terças"):
        d = responder(anomalia(), "US09", "x", AGORA, ModeloFixo({"motivo": "recorrente", "rotina": rotina}))
        assert d.anomalia.estado == "resolvida"
        assert d.anomalia.proposta_silencio is None
        assert d.proposta is None


def test_aplicar_silencio_e_rotina():
    aplicar({"tipo": "silencio", "us": "US09", "ate": "2026-11-17T23:59:59+00:00", "motivo": "hoje"})
    aplicar({"tipo": "rotina", **ROTINA})
    contexto = carregar_contexto(AGORA)
    assert [(s.us, s.motivo) for s in contexto.silencios] == [("US09", "hoje")]
    assert contexto.silencios[0].ate == datetime.fromisoformat("2026-11-17T23:59:59+00:00")
    assert contexto.rotinas == [Rotina("a empregada vem às terças à tarde", [1], datetime(2026, 1, 1, 14).time())]
