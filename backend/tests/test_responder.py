from datetime import datetime, time, timedelta

import pytest

from backend.contexto.repositorio import carregar_contexto, rotinas_recusadas
from backend.contrato import Anomalia
from backend.formatos import Rotina
from backend.resposta.responder import aplicar, recusar, responder
from tests.conftest import AGORA

# AGORA é uma terça às 15:00.
SEMANA = timedelta(days=7)
DUAS_TERCAS = [AGORA - SEMANA, AGORA - 2 * SEMANA]
ROTINA = {"descricao": "a empregada vem às terças à tarde", "dias": [1], "hora": "14:00"}


def anomalia(detetada_em: datetime = AGORA) -> Anomalia:
    return Anomalia(
        classe="seguranca", titulo="A porta abriu", explicacao="A porta abriu fora de horas.", detetada_em=detetada_em
    )


def _responder(a=None, us="US07", anteriores=(), rotinas=(), recusadas=(), agora=AGORA):
    return responder(a or anomalia(), us, "Está tudo bem", agora, list(anteriores), list(rotinas), list(recusadas))


def test_resolve_com_a_resposta():
    d = _responder()
    assert d.anomalia.estado == "resolvida"
    assert d.anomalia.resposta.texto == "Está tudo bem"
    assert d.anomalia.resposta.em == AGORA
    assert d.anomalia.resolucao.texto == "Resolvida com a resposta «Está tudo bem»"


def test_a_primeira_vez_nao_propoe_nada():
    d = _responder()
    assert d.anomalia.proposta_silencio is None
    assert d.proposta is None


def test_a_terceira_terca_propoe_rotina():
    d = _responder(anteriores=DUAS_TERCAS)
    assert d.proposta == {"tipo": "rotina", "descricao": "a porta abre a esta hora", "dias": [1], "hora": "15:00"}
    p = d.anomalia.proposta_silencio
    assert p.estado == "pendente"
    assert p.texto == (
        "Isto tem-se repetido: a porta abre a esta hora (terça-feira, às 15:00). "
        "Passo a contar com isso? Quando bater certo, não aviso."
    )
    assert p.ate.year == 2036


def test_conta_a_hora_do_aviso_e_nao_a_da_resposta():
    # Respondida às 18:00 (fora da margem), mas o aviso foi às 15:00 como os outros.
    d = _responder(anteriores=DUAS_TERCAS, agora=AGORA + timedelta(hours=3))
    assert d.proposta is not None
    assert d.proposta["hora"] == "15:00"


def test_ja_recusada_nao_propoe():
    recusada = Rotina("a porta abre a esta hora", [1], time(15, 0))
    d = _responder(anteriores=DUAS_TERCAS, recusadas=[recusada])
    assert d.proposta is None
    assert d.anomalia.proposta_silencio is None


def test_porta_esquecida_aberta_nao_propoe_rotina():
    """US08 avisa sempre (avaliar.AVISA_SEMPRE): uma rotina nunca a calaria."""
    assert _responder(us="US08", anteriores=DUAS_TERCAS).proposta is None


@pytest.mark.parametrize(
    "dias, hora, esperado",
    [
        ([0, 1, 2, 3, 4], time(19, 0), "dias úteis, às 19:00"),
        ([6, 0], None, "segunda-feira e domingo"),
        ([0, 2, 4], None, "segunda-feira, quarta-feira e sexta-feira"),
        (list(range(7)), None, "todos os dias"),
    ],
)
def test_quando(dias, hora, esperado):
    from backend.resposta.responder import _quando

    assert _quando(Rotina("x", dias, hora)) == esperado


def test_aplicar_rotina_e_silencio_antigo():
    aplicar({"tipo": "silencio", "us": "US09", "ate": "2026-11-17T23:59:59+00:00", "motivo": "hoje"})
    aplicar({"tipo": "rotina", **ROTINA})
    contexto = carregar_contexto(AGORA)
    assert [(s.us, s.motivo) for s in contexto.silencios] == [("US09", "hoje")]
    assert contexto.rotinas == [Rotina("a empregada vem às terças à tarde", [1], time(14, 0))]


def test_recusar_rotina_guarda_a_recusa():
    recusar({"tipo": "rotina", **ROTINA})
    assert rotinas_recusadas() == [Rotina("a empregada vem às terças à tarde", [1], time(14, 0))]
    assert carregar_contexto(AGORA).rotinas == []


def test_recusar_silencio_antigo_nao_guarda_nada():
    recusar({"tipo": "silencio", "us": "US09", "ate": "2026-11-17T23:59:59+00:00", "motivo": "hoje"})
    assert rotinas_recusadas() == []


def test_recusar_proposta_estragada_nao_rebenta():
    recusar({"tipo": "rotina", "descricao": "", "dias": [9]})
    assert rotinas_recusadas() == []
