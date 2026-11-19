"""US15: a válvula da água é simulada (o kit não a tem) e a casa fecha-a pela ação da anomalia."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from backend import anomalias, dispositivos
from backend.contrato import AcaoProposta, Anomalia
from backend.dependencias import obter_agora
from backend.dispositivos import mudancas, simulacao
from backend.formatos import Leitura
from backend.ia.avaliar import registar_us
from backend.main import app
from backend.resposta.router import obter_publicar
from tests.conftest import AGORA

EM = datetime(2026, 11, 18, 3, 0)


@pytest.fixture(autouse=True)
def sem_injetadas():
    simulacao.limpar()
    yield
    simulacao.limpar()


def test_fechar_a_valvula_corta_o_caudal():
    simulacao.sobrepor("agua", "caudal", 0.3)
    assert dispositivos.executar("agua", "valvula", "fechada")  # não passa pelo MCP
    leituras = {(l.dispositivo, l.tipo): l.valor for l in simulacao.aplicar([], EM)}
    assert leituras == {("agua", "valvula"): "fechada", ("agua", "caudal"): 0.0}


def test_abrir_a_valvula_nao_inventa_caudal():
    assert dispositivos.executar("agua", "valvula", "aberta")
    assert ("agua", "caudal") not in simulacao.listar()


def test_valor_desconhecido_da_valvula_e_recusado():
    with pytest.raises(ValueError):
        dispositivos.executar("agua", "valvula", "meio-aberta")


def test_fechar_a_agua_fica_no_historico():
    observador = mudancas.Observador()
    observador.ver([Leitura("agua", "valvula", "aberta", EM)])
    (evento,) = observador.ver([Leitura("agua", "valvula", "fechada", EM)])
    assert (evento.dispositivo, evento.descricao) == ("Válvula da água", "Fechou")


def test_aceitar_a_acao_fecha_a_agua_e_resolve():
    publicadas: list[Anomalia] = []

    def publicar(a: Anomalia) -> None:
        anomalias.guardar(a)
        publicadas.append(a)

    app.dependency_overrides[obter_publicar] = lambda: publicar
    app.dependency_overrides[obter_agora] = lambda: AGORA
    try:
        a = Anomalia(
            classe="eficiencia",
            titulo="Água a correr sem parar",
            explicacao="x",
            detetada_em=AGORA,
            acao_proposta=AcaoProposta(descricao="Fechar a água"),
        )
        anomalias.guardar(a)
        registar_us(a.id, "US15")
        simulacao.sobrepor("agua", "caudal", 6.0)
        r = TestClient(app).post(f"/anomalias/{a.id}/acao", json={"aceitar": True})
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    assert r.json()["estado"] == "resolvida"
    assert r.json()["resolucao"]["texto"] == "Feito: Fechar a água."
    assert simulacao.listar()[("agua", "caudal")] == 0.0


def test_voltar_a_injetar_caudal_abre_a_valvula():
    dispositivos.executar("agua", "valvula", "fechada")
    simulacao.sobrepor("agua", "caudal", 6.0)
    assert simulacao.listar()[("agua", "valvula")] == "aberta"
