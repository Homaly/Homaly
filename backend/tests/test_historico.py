"""US06: as anomalias e os desvios sem aviso aparecem no histórico (GET /eventos)."""

from datetime import timedelta

from fastapi.testclient import TestClient

from backend import acoes, anomalias, eventos, historico
from backend.contrato import AcaoProposta, Anomalia, TextoEm
from backend.dependencias import obter_agora
from backend.formatos import Desvio
from backend.ia.avaliar import registar_us
from backend.main import app
from backend.resposta.router import obter_publicar
from tests.conftest import AGORA


def _anomalia(us: str | None = "US11", **campos) -> Anomalia:
    a = Anomalia(classe="eficiencia", titulo="Luz da sala acesa há 5 horas", explicacao="x", detetada_em=AGORA, **campos)
    if us:
        registar_us(a.id, us)
    return a


def _eventos() -> list[tuple[str, str, str | None]]:
    return [(e.dispositivo, e.descricao, e.anomalia_id) for e in eventos.listar()]


def test_anomalia_nova_fica_no_historico():
    a = _anomalia()
    anomalias.guardar(a)
    [evento] = eventos.listar()
    assert (evento.dispositivo, evento.descricao, evento.anomalia_id) == ("Luz da sala", a.titulo, a.id)
    assert evento.em == AGORA


def test_guardar_de_novo_nao_repete():
    a = _anomalia()
    anomalias.guardar(a)
    anomalias.guardar(a.model_copy(update={"explicacao": "outra"}))
    anomalias.guardar(a)
    assert len(eventos.listar()) == 1


def test_resolvida_com_resolucao():
    a = _anomalia(us="US08")
    anomalias.guardar(a)
    fechou = AGORA + timedelta(minutes=12)
    anomalias.guardar(
        a.model_copy(update={"estado": "resolvida", "resolucao": TextoEm(texto="a porta fechou às 15:12", em=fechou)})
    )
    resolvida = eventos.listar()[0]  # a mais recente
    assert (resolvida.dispositivo, resolvida.descricao, resolvida.anomalia_id) == (
        "Porta da rua",
        "A porta fechou às 15:12",
        a.id,
    )
    assert resolvida.em == fechou
    # Guardar outra vez a anomalia resolvida não repete o evento.
    anomalias.guardar(anomalias.obter(a.id))
    assert len(eventos.listar()) == 2


def test_resolvida_so_com_resposta():
    a = _anomalia()
    anomalias.guardar(a)
    resposta = TextoEm(texto="Está tudo bem", em=AGORA + timedelta(minutes=1))
    anomalias.guardar(a.model_copy(update={"estado": "resolvida", "resposta": resposta}))
    assert eventos.listar()[0].descricao == "Resolvida: Está tudo bem"


def test_ja_resolvida_e_sem_us():
    a = _anomalia(us=None, estado="resolvida")
    anomalias.guardar(a)
    assert sorted(_eventos()) == sorted([("Casa", a.titulo, a.id), ("Casa", "Resolvida", a.id)])


def test_desvio_sem_aviso():
    desvio = Desvio(us="US07", classe="seguranca", resumo="A porta abriu às 03:12.", habitual=None)
    historico.registar_desvio(desvio, "silenciado pelo responsável", AGORA)
    assert _eventos() == [
        ("Porta da rua", "A porta abriu às 03:12. Não avisou: silenciado pelo responsável.", None)
    ]


def test_o_historico_nunca_impede_guardar(monkeypatch):
    def rebenta(anterior, nova):
        raise RuntimeError("histórico em baixo")

    monkeypatch.setattr(historico, "anomalia_mudou", rebenta)
    a = _anomalia()
    anomalias.guardar(a)
    assert anomalias.obter(a.id) == a


def test_aceitar_a_acao_fica_no_historico():
    publicar = lambda a: anomalias.guardar(a)  # noqa: E731
    app.dependency_overrides[obter_publicar] = lambda: publicar
    app.dependency_overrides[obter_agora] = lambda: AGORA + timedelta(hours=1)
    app.dependency_overrides[acoes.obter_executar] = lambda: (lambda d, t, v: True)
    try:
        a = _anomalia(acao_proposta=AcaoProposta(descricao="Apagar a luz"))
        anomalias.guardar(a)
        assert TestClient(app).post(f"/anomalias/{a.id}/acao", json={"aceitar": True}).status_code == 200
        corpo = TestClient(app).get("/eventos").json()
    finally:
        app.dependency_overrides.clear()
    assert [(e["descricao"], e["anomaliaId"]) for e in corpo] == [
        ("Feito: Apagar a luz.", a.id),  # do mais recente para o mais antigo
        ("Luz da sala acesa há 5 horas", a.id),
    ]
