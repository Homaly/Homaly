from datetime import datetime, time, timedelta

from backend.contexto import repositorio as repo
from backend.contrato import MensagemConversa
from backend.formatos import Contexto, Periodo, Rotina, Silencio
from tests.conftest import AGORA, LX


def test_contexto_vazio():
    assert repo.carregar_contexto(AGORA) == Contexto([], [], [], False)


def _ferias() -> Periodo:
    return Periodo(
        datetime(2026, 11, 17, tzinfo=LX), datetime(2026, 11, 24, tzinfo=LX), "viagem"
    )


def test_ferias_dentro_do_periodo_casa_vazia():
    repo.guardar_periodo(_ferias())
    contexto = repo.carregar_contexto(datetime(2026, 11, 20, 12, 0, tzinfo=LX))
    assert contexto.casa_vazia is True
    assert contexto.ferias == [_ferias()]


def test_ferias_fora_do_periodo():
    repo.guardar_periodo(_ferias())
    contexto = repo.carregar_contexto(datetime(2026, 11, 25, 12, 0, tzinfo=LX))
    assert contexto.casa_vazia is False


def test_rotina_round_trip():
    rotinas = [Rotina("empregada", [1], time(14, 0)), Rotina("x", [0, 2], None)]
    for r in rotinas:
        repo.guardar_rotina(r)
    assert repo.carregar_contexto(AGORA).rotinas == rotinas


def test_silencio_round_trip():
    silencios = [
        Silencio("US08", AGORA + timedelta(hours=2), "estou em casa"),
        Silencio("US09", None, "até remover"),
    ]
    for s in silencios:
        repo.guardar_silencio(s)
    assert repo.carregar_contexto(AGORA).silencios == silencios


def test_aparelho_substitui():
    repo.guardar_aparelho("aquecedor")
    assert repo.carregar_contexto(AGORA).aparelho_tomada == "aquecedor"
    repo.guardar_aparelho("desumidificador")
    assert repo.carregar_contexto(AGORA).aparelho_tomada == "desumidificador"


def test_mensagens_por_ordem():
    segunda = MensagemConversa(autor="casa", texto="segunda", em=AGORA + timedelta(minutes=1))
    primeira = MensagemConversa(autor="pessoa", texto="primeira", em=AGORA)
    repo.guardar_mensagem(segunda)
    repo.guardar_mensagem(primeira)
    assert repo.listar_mensagens() == [primeira, segunda]


def test_proposta_guardar_ler_apagar():
    dados = {"us": "US08", "ate": "2026-11-17T18:00:00+00:00", "n": [1, 2]}
    repo.guardar_proposta("a1", dados)
    assert repo.ler_proposta("a1") == dados
    repo.apagar_proposta("a1")
    assert repo.ler_proposta("a1") is None
