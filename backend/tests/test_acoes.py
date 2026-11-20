import sys

import pytest
from fastapi.testclient import TestClient

from backend import acoes, anomalias, db
from backend.contexto.repositorio import carregar_contexto
from backend.contrato import AcaoProposta, Anomalia
from backend.dependencias import obter_agora
from backend.ia.avaliar import registar_us
from backend.main import app
from backend.resposta.router import obter_publicar
from tests.conftest import AGORA


class Executor:
    """Um `dispositivos.executar` de teste: guarda as chamadas e devolve o combinado."""

    def __init__(self, resultado: bool | Exception = True):
        self.resultado = resultado
        self.chamadas: list[tuple[str, ...]] = []

    def __call__(self, dispositivo: str, tipo: str, valor: str, *id: str) -> bool:
        self.chamadas.append((dispositivo, tipo, valor, *id))
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado


@pytest.fixture
def publicadas():
    return []


@pytest.fixture
def cliente(publicadas):
    def publicar(a: Anomalia) -> None:
        anomalias.guardar(a)
        publicadas.append(a)

    app.dependency_overrides[obter_publicar] = lambda: publicar
    app.dependency_overrides[obter_agora] = lambda: AGORA
    yield TestClient(app)
    app.dependency_overrides.clear()


def _com(executor: Executor) -> Executor:
    app.dependency_overrides[acoes.obter_executar] = lambda: executor
    return executor


def _anomalia(us: str | None = "US11", acao: str | None = "Apagar a luz da sala", estado="ativa") -> Anomalia:
    a = Anomalia(
        classe="eficiencia",
        titulo="Luz da sala acesa há 5 horas",
        explicacao="x",
        detetada_em=AGORA,
        estado=estado,
        acao_proposta=AcaoProposta(descricao=acao) if acao else None,
    )
    anomalias.guardar(a)
    if us:
        registar_us(a.id, us)
    return a


def _decidir(cliente, a: Anomalia, aceitar: bool):
    return cliente.post(f"/anomalias/{a.id}/acao", json={"aceitar": aceitar})


def _registos(anomalia_id: str) -> list[tuple]:
    with db.ligar() as con:
        linhas = con.execute(
            "SELECT dispositivo, tipo, valor, resultado FROM acoes WHERE anomalia_id = ?",
            (anomalia_id,),
        ).fetchall()
    return [tuple(linha) for linha in linhas]


def test_aceitar_apaga_a_luz_e_resolve(cliente, publicadas):
    executor = _com(Executor(True))
    a = _anomalia()
    r = _decidir(cliente, a, True)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["estado"] == "resolvida"
    assert corpo["resposta"]["texto"] == "Aceitou: Apagar a luz da sala"
    assert corpo["resolucao"]["texto"] == "Feito: Apagar a luz da sala."
    assert executor.chamadas == [("lampada", "power", "off")]
    assert [p.id for p in publicadas] == [a.id]
    assert anomalias.obter(a.id).estado == "resolvida"
    assert _registos(a.id) == [("lampada", "power", "off", "feita")]


def test_aceitar_na_us14_desliga_a_tomada(cliente):
    executor = _com(Executor(True))
    a = _anomalia(us="US14", acao="Desligar o aquecedor")
    assert _decidir(cliente, a, True).status_code == 200
    assert executor.chamadas == [("tomada", "power", "off")]


def test_aceitar_muda_o_dispositivo_de_que_a_anomalia_fala(cliente):
    # Com várias lâmpadas, a regra diz qual (Desvio.dispositivo): a casa apaga essa.
    executor = _com(Executor(True))
    a = _anomalia()
    registar_us(a.id, "US11", "luz-quarto")
    assert _decidir(cliente, a, True).status_code == 200
    assert executor.chamadas == [("lampada", "power", "off", "luz-quarto")]


@pytest.mark.parametrize("resultado", [False, RuntimeError("MCP em baixo")])
def test_se_a_acao_falha_nada_muda(cliente, publicadas, resultado):
    _com(Executor(resultado))
    a = _anomalia()
    r = _decidir(cliente, a, True)
    assert r.status_code == 502
    assert publicadas == []
    guardada = anomalias.obter(a.id)
    assert guardada.estado == "ativa" and guardada.resposta is None
    assert _registos(a.id) == [("lampada", "power", "off", "falhou")]


def test_recusar_nao_age_e_nao_volta_a_perguntar_hoje(cliente, publicadas):
    executor = _com(Executor(True))
    a = _anomalia()
    r = _decidir(cliente, a, False)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["estado"] == "resolvida"
    assert corpo["resposta"]["texto"] == "Recusou: Apagar a luz da sala"
    assert "fim do dia" in corpo["resolucao"]["texto"]
    assert executor.chamadas == []
    silencios = carregar_contexto(AGORA).silencios
    assert [(s.us, s.ate) for s in silencios] == [
        ("US11", AGORA.replace(hour=23, minute=59, second=59))
    ]
    assert _registos(a.id) == [("lampada", "power", "off", "recusada")]


def test_recusar_sem_acao_conhecida_nao_silencia(cliente):
    _com(Executor(True))
    a = _anomalia(us="US08", acao="Fechar a porta")
    r = _decidir(cliente, a, False)
    assert r.status_code == 200
    assert r.json()["resolucao"]["texto"] == "A casa não agiu."
    assert carregar_contexto(AGORA).silencios == []


@pytest.mark.parametrize("us", ["US08", None])
def test_aceitar_acao_que_a_casa_nao_sabe_fazer(cliente, publicadas, us):
    executor = _com(Executor(True))
    a = _anomalia(us=us, acao="Fechar a porta")
    r = _decidir(cliente, a, True)
    assert r.status_code == 409
    assert executor.chamadas == [] and publicadas == []
    assert anomalias.obter(a.id).estado == "ativa"


def test_pedidos_invalidos(cliente):
    _com(Executor(True))
    assert cliente.post("/anomalias/nada/acao", json={"aceitar": True}).status_code == 404
    assert _decidir(cliente, _anomalia(acao=None), True).status_code == 409
    assert _decidir(cliente, _anomalia(estado="resolvida"), True).status_code == 409
    assert cliente.post(f"/anomalias/{_anomalia().id}/acao", json={}).status_code == 422


def test_com_dispositivos_usa_o_executar_real():
    from backend import dispositivos

    assert acoes.obter_executar() is dispositivos.executar


def test_sem_dispositivos_so_finge_em_desenvolvimento(monkeypatch):
    # Simula um backend sem o módulo dispositivos (None em sys.modules faz o import falhar);
    # nunca chama o executar real, que mudaria a lâmpada da casa.
    monkeypatch.setitem(sys.modules, "backend.dispositivos", None)
    monkeypatch.setenv("HOMALY_DEV", "1")
    assert acoes.obter_executar()("lampada", "power", "off") is True
    monkeypatch.delenv("HOMALY_DEV")
    assert acoes.obter_executar()("lampada", "power", "off") is False
