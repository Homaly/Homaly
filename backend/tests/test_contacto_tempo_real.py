"""US05 com o relógio acelerado da demo: os prazos do contacto externo contam em tempo real.

O tempo de espera é o que o responsável tem para responder e as tentativas são as do textbee:
nenhuma pessoa nem rede anda 60 vezes mais depressa.
O texto das SMS continua com as horas da anomalia (as simuladas).
"""

from datetime import datetime, timedelta

import pytest

from backend import anomalias, contacto_externo, definicoes, relogio
from backend.contacto_externo import envios, mensagens, sms
from backend.contrato import Anomalia, Contacto, Definicoes, TextoEm
from backend.relogio import Relogio

from .conftest import LX

SIMULADA = datetime(2026, 11, 19, 8, 50, tzinfo=LX)
FOLGA = timedelta(seconds=30)


@pytest.fixture(autouse=True)
def acelerado(monkeypatch):
    """O relógio da app começa às 08:50 de 19/11 e anda 60x mais depressa."""
    monkeypatch.setattr(relogio, "_partilhado", Relogio(SIMULADA, fator=60))
    enviadas: list[str] = []
    monkeypatch.setattr(sms, "enviar", lambda para, texto: enviadas.append(texto))
    definicoes.guardar(Definicoes(contacto=Contacto(nome="Ana", telemovel="912345678"), espera_minutos=5))
    return enviadas


def alerta() -> Anomalia:
    a = Anomalia(classe="seguranca", titulo="Porta aberta", explicacao="A porta está aberta.", detetada_em=SIMULADA)
    anomalias.guardar(a)
    return a


def perto(a: datetime, b: datetime) -> bool:
    return abs(a - b) <= FOLGA


def test_o_tempo_de_espera_conta_em_minutos_reais():
    a = alerta()
    contacto_externo.ContactoExterno().agendar(a)

    enviar_em = envios.obter(a.id).enviar_em
    assert perto(enviar_em, datetime.now().astimezone() + timedelta(minutes=5))


def test_com_o_relogio_acelerado_a_sms_nao_sai_antes_de_o_responsavel_poder_responder(acelerado):
    a = alerta()
    contacto_externo.ContactoExterno().agendar(a)

    contacto_externo.verificar()  # segundos reais depois (= minutos simulados)

    assert acelerado == []
    assert envios.obter(a.id).estado == "pendente"


def test_a_sms_continua_com_a_hora_simulada_da_anomalia(acelerado):
    a = alerta()
    definicoes.guardar(Definicoes(contacto=Contacto(nome="Ana", telemovel="912345678"), espera_minutos=0))
    contacto_externo.ContactoExterno().agendar(a)
    contacto_externo.verificar()

    [texto] = acelerado
    assert "às 08:50" in texto


def test_o_resolvido_pela_resposta_diz_a_hora_simulada_da_resposta():
    respondida = Anomalia(
        classe="seguranca",
        titulo="Porta aberta",
        explicacao="x",
        detetada_em=SIMULADA,
        estado="resolvida",
        resposta=TextoEm(texto="já fechei", em=SIMULADA + timedelta(minutes=7)),
    )
    real = datetime.now().astimezone()

    texto = mensagens.resolvido(respondida, None, real)

    assert "Resolvido às 08:57" in texto
