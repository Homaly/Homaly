"""US14 com a porta e as câmaras de dentro: saiu, está na divisão ou noutra (regras/presenca.py)."""

from datetime import datetime, timedelta

import pytest

from backend import habitual
from backend.formatos import Contexto, Desvio, Leitura, Resolucao
from backend.regras import presenca, us14
from tests.regras_casa import Registo

DIA = datetime(2026, 11, 18)
AQUECEDOR = Contexto([], [], [], False, aparelho_tomada="o aquecedor")


@pytest.fixture(autouse=True)
def limpo(monkeypatch):
    for variavel in ("PRESENCA_MINUTOS", "TOMADA_DIVISAO", "CAMARA_DIVISAO"):
        monkeypatch.delenv(variavel, raising=False)
    # Os valores de uma demo; por omissão são 20 e 60 min (test_valores_por_omissao).
    monkeypatch.setenv("SAIU_MINUTOS", "5")
    monkeypatch.setenv("AUSENCIA_MINUTOS", "15")
    us14.reiniciar()
    yield
    us14.reiniciar()


def em(hhmm: str) -> datetime:
    h, m = map(int, hhmm.split(":"))
    return DIA.replace(hour=h, minute=m)


def passo(hhmm: str, watts: float = 1500, porta: str = "normal", contexto: Contexto = AQUECEDOR, **cameras):
    agora = em(hhmm)
    leituras = [Leitura("tomada", "instantPower", watts, agora), Leitura("porta", "sensorState", porta, agora)]
    leituras += [Leitura(camara, "motionDetected", valor, agora) for camara, valor in cameras.items()]
    return us14.verificar(leituras, contexto, agora)


def desvios(saidas) -> list[Desvio]:
    return [s for s in saidas if isinstance(s, Desvio)]


def test_saiu_e_deixou_o_aquecedor_a_gastar():
    r = Registo(us14, AQUECEDOR).correr("us14_saiu.csv")

    assert r.publicadas == [
        (datetime(2026, 11, 18, 14, 16), "ativa", "eficiencia"),  # 5 min depois de a porta fechar
        (datetime(2026, 11, 18, 14, 30), "resolvida", "eficiencia"),
    ]
    resumo = r.avaliados[0][1].resumo
    assert resumo == (
        "O aquecedor está a gastar desde as 14:05, e a porta fechou às 14:11 "
        "sem movimento em casa desde então: parece que saíram."
    )
    assert r.resolucoes == ["o aquecedor deixou de gastar às 14:30"]


def test_com_alguem_na_divisao_nunca_avisa():
    passo("09:55", watts=0, camara=True)
    inicio = em("10:00")
    for i in range(0, 4 * 60, 5):  # 4 h a gastar, sempre com alguém na sala
        hhmm = f"{(inicio + timedelta(minutes=i)):%H:%M}"
        assert passo(hhmm, camara=True) == []
    assert habitual.padrao().limite_tomada < timedelta(hours=4)  # sem câmaras já teria avisado


def test_noutra_divisao_avisa_e_resolve_quando_volta():
    passo("10:00", watts=0, camara=True)
    assert passo("10:05", camara=True) == []
    assert passo("10:10", camara=False, camara_cozinha=True) == []
    assert passo("10:15", camara=False, camara_cozinha=True) == []

    [desvio] = desvios(passo("10:20", camara=False, camara_cozinha=True))
    assert desvio.classe == "eficiencia"
    assert desvio.resumo == "O aquecedor está a gastar e não há ninguém na sala desde as 10:05 (há movimento na cozinha)."
    assert passo("10:21", camara=False, camara_quarto=True) == [desvio]  # o texto não muda

    [resolucao] = passo("10:25", camara=True)
    assert isinstance(resolucao, Resolucao)
    assert resolucao.texto == "voltou a haver alguém na sala às 10:25"


def test_sem_ninguem_a_mexer_se_conta_desde_que_comecou_a_gastar():
    passo("09:59", watts=0, camara=False)
    assert passo("10:00", camara=False) == []  # começa a gastar
    assert passo("10:14", camara=False) == []
    [desvio] = desvios(passo("10:15", camara=False))
    assert desvio.resumo == "O aquecedor está a gastar e não há ninguém na sala desde as 10:00."


def test_movimento_depois_de_a_porta_fechar_nao_e_saida():
    passo("14:00", watts=0, camara=True)
    passo("14:05", camara=True)
    passo("14:10", porta="alarm", camara=False)
    passo("14:11", camara=False)
    passo("14:13", camara=False, camara_cozinha=True)  # alguém ficou em casa
    assert passo("14:16", camara=False) == []
    [desvio] = desvios(passo("14:20", camara=False))  # mas ninguém na sala há 15 min
    assert "não há ninguém na sala desde as 14:05 (há movimento na cozinha)" in desvio.resumo


def test_a_maquina_de_lavar_pode_ficar_sozinha():
    maquina = Contexto([], [], [], False, aparelho_tomada="a máquina de lavar")
    passo("14:00", watts=0, contexto=maquina, camara=True)
    passo("14:05", contexto=maquina, camara=True)
    passo("14:10", porta="alarm", contexto=maquina, camara=False)
    passo("14:11", contexto=maquina, camara=False)
    assert passo("14:30", contexto=maquina, camara=False) == []
    limite = habitual.padrao().limite_tomada
    depois = f"{em('14:05') + limite:%H:%M}"
    [desvio] = desvios(passo(depois, contexto=maquina, camara=False))
    assert "há mais de" in desvio.resumo  # o aviso de sempre, ao fim de 3x o habitual


def test_a_camara_da_entrada_nao_conta():
    passo("14:00", watts=0, camara_entrada=True)
    passo("14:05", camara_entrada=True)
    passo("14:10", porta="alarm", camara_entrada=False)
    passo("14:11", camara_entrada=False)
    assert passo("14:30", camara_entrada=False) == []  # sem câmaras de dentro: como antes
    assert not presenca.ha_cameras_dentro()


def test_a_tomada_noutra_divisao(monkeypatch):
    monkeypatch.setenv("TOMADA_DIVISAO", "quarto")
    passo("10:00", watts=0, camara_quarto=True)
    assert passo("10:05", camara=True, camara_quarto=True) == []
    [desvio] = desvios(passo("10:20", camara=True, camara_quarto=False))
    assert desvio.resumo == "O aquecedor está a gastar e não há ninguém no quarto desde as 10:05 (há movimento na sala)."


def test_casa_vazia_continua_a_ser_seguranca():
    from backend.formatos import Periodo

    ferias = Contexto([Periodo(DIA, DIA.replace(hour=23, minute=59), "férias")], [], [], False,
                      aparelho_tomada="o aquecedor")
    passo("10:00", watts=0, contexto=ferias, camara=True)
    [desvio] = desvios(passo("10:05", contexto=ferias, camara=True))
    assert desvio.classe == "seguranca" and desvio.imediato


def test_valores_por_omissao(monkeypatch):
    monkeypatch.delenv("SAIU_MINUTOS")
    monkeypatch.delenv("AUSENCIA_MINUTOS")
    assert us14.saiu_minutos() == timedelta(minutes=20)
    assert us14.ausencia_minutos() == timedelta(minutes=60)
    assert us14.presenca_minutos() == timedelta(minutes=10)


@pytest.mark.parametrize(("valor", "anterior", "esperado"), [
    (True, None, True), (False, True, False), ("true", None, True), ("off", None, False),
    ("", None, False), (1, None, True), ("2026-11-18T10:00", None, True),
    ("2026-11-18T10:00", "2026-11-18T10:00", False),  # a mesma hora: não houve movimento novo
])
def test_movimento(valor, anterior, esperado):
    assert presenca.movimento(valor, anterior) is esperado


@pytest.mark.parametrize(("aparelho", "esperado"), [
    ("o aquecedor", True), ("o ferro de engomar", True), ("a televisão", True), (None, True),
    ("a Máquina da Loiça", False), ("o frigorífico", False), ("o desumidificador", False),
])
def test_precisa_de_alguem(aparelho, esperado):
    assert us14.precisa_de_alguem(aparelho) is esperado
