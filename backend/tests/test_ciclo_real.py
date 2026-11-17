"""O ciclo com as peças reais: MCP (falso no cliente), IA, contexto, histórico e avisos."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from backend import anomalias, ciclo, dispositivos
from backend.ciclo import Ciclo, ao_vivo
from backend.contrato import Anomalia, TextoEm
from backend.dispositivos.mcp import ErroDispositivos
from backend.formatos import Contexto, Desvio
from backend.ia.avaliar import us_da_anomalia
from backend.regras import us07, us09, us14
from backend.relogio import Relogio

from .conftest import LX
from .test_dispositivos import ClienteFalso, com_valor, json_real

TERCA_0310 = datetime(2026, 11, 17, 3, 10, tzinfo=LX)


def test_porta_de_madrugada_chega_a_base_de_dados():
    for regra in (us07, us09, us14):
        regra.reiniciar()
    casa = json_real("mcp_get_home_devices.txt")
    cliente = ClienteFalso(com_valor(casa, "contactSensor", "sensorState", "normal"))
    dispositivos.configurar(cliente)
    try:
        relogio = Relogio(TERCA_0310)  # hora real a andar, mas a começar às 03:10
        c, ler = ciclo.real(relogio)
        c.passo(ler(), relogio.agora())
        cliente.casa = com_valor(casa, "contactSensor", "sensorState", "alarm")
        c.passo(ler(), relogio.agora())
    finally:
        dispositivos.configurar(None)

    [a] = anomalias.listar()
    assert (a.classe, a.estado) == ("seguranca", "ativa")
    assert us_da_anomalia(a.id) == "US07"


def test_nao_reescreve_uma_anomalia_que_o_responsavel_resolveu():
    guardada: dict[str, Anomalia] = {}
    publicadas: list[Anomalia] = []
    desvios = [Desvio(us="US08", classe="seguranca", resumo="porta aberta", habitual=None)]

    def publicar(a: Anomalia) -> None:
        publicadas.append(a)
        guardada[a.id] = a.model_copy(deep=True)

    c = Ciclo(
        regras=[lambda l, ctx, agora: list(desvios)],
        avaliar=lambda d, ctx: Anomalia(classe=d.classe, titulo="t", explicacao=d.resumo),
        publicar=publicar,
        obter_contexto=lambda: Contexto([], [], [], False),
        registar_historico=lambda d, m, a: None,
        obter_anomalia=guardada.get,
    )
    c.passo([], TERCA_0310)
    [a] = publicadas
    # O responsável responde pela PWA: a anomalia fica resolvida na base de dados.
    guardada[a.id] = a.model_copy(update={"estado": "resolvida", "resposta": TextoEm(texto="está tudo bem")})

    desvios[:] = []
    c.passo([], TERCA_0310 + timedelta(minutes=1))
    assert len(publicadas) == 1  # não voltou a publicar por cima da resposta
    assert guardada[a.id].resposta.texto == "está tudo bem"


def test_uma_volta_que_falha_nao_para_o_ciclo():
    vistos: list[datetime] = []
    leituras = iter([ErroDispositivos("o MCP não respondeu"), RuntimeError("outra falha"), [], []])

    def ler():
        valor = next(leituras)
        if isinstance(valor, Exception):
            raise valor
        return valor

    c = Ciclo(
        regras=[lambda l, ctx, agora: vistos.append(agora) or []],
        avaliar=lambda d, ctx: None,
        publicar=lambda a: None,
        obter_contexto=lambda: Contexto([], [], [], False),
        registar_historico=lambda d, m, a: None,
    )
    ao_vivo(c, ler, Relogio(TERCA_0310, real=lambda: TERCA_0310), intervalo=0, passos=4, dormir=lambda s: None)
    assert len(vistos) == 2


def test_a_app_so_arranca_o_ciclo_com_CICLO_1(monkeypatch):
    from backend.main import app

    arrancados: list[bool] = []

    class Parar:
        def set(self):
            arrancados.append(False)

    monkeypatch.setattr(ciclo, "arrancar", lambda: arrancados.append(True) or Parar())
    monkeypatch.delenv("CICLO", raising=False)
    with TestClient(app):
        pass
    assert arrancados == []

    monkeypatch.setenv("CICLO", "1")
    with TestClient(app):
        assert arrancados == [True]
    assert arrancados == [True, False]  # pára quando a app fecha
