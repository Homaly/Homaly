"""US14 com a saída de casa e as câmaras de dentro: saiu, está na divisão ou noutra (regras/presenca.py).

As câmaras e a tomada têm a divisão do inventário de teste (CASA, em conftest.py): `camara` é a do
kit, sem id (na sala); as outras têm o id do inventário.
"""

from datetime import datetime, timedelta

import pytest

from backend import habitual
from backend.formatos import Contexto, Desvio, Leitura, Resolucao
from backend.regras import presenca, us14
from tests.regras_casa import Registo

DIA = datetime(2026, 11, 18)
AQUECEDOR = Contexto([], [], [], False, aparelho_tomada="o aquecedor")


# O nome usado nos testes -> o id da câmara no inventário de teste ("" = a do kit, na sala).
CAMARAS = {"camara": "", "camara_cozinha": "cam-cozinha", "camara_quarto": "cam-quarto", "camara_entrada": "cam-rua"}


@pytest.fixture(autouse=True)
def limpo(monkeypatch, casa):
    for variavel in ("PRESENCA_MINUTOS", "SAIDA_MINUTOS"):
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


def passo(
    hhmm: str, watts: float = 1500, porta: str = "normal", contexto: Contexto = AQUECEDOR, tomada: str = "", **cameras
):
    agora = em(hhmm)
    leituras = [Leitura("tomada", "instantPower", watts, agora, tomada), Leitura("porta", "sensorState", porta, agora)]
    leituras += [Leitura("camara", "motionDetected", valor, agora, CAMARAS[c]) for c, valor in cameras.items()]
    return us14.verificar(leituras, contexto, agora)


def desvios(saidas) -> list[Desvio]:
    return [s for s in saidas if isinstance(s, Desvio)]


def test_saiu_e_deixou_o_aquecedor_a_gastar():
    r = Registo(us14, AQUECEDOR).correr("us14_saiu.csv")

    assert r.publicadas == [
        # Saiu às 14:15 (5 min sem movimento depois da porta), mas a câmara viu alguém na sala às
        # 14:05 e isso conta como alguém a usar o aparelho durante PRESENCA_MINUTOS (10).
        (datetime(2026, 11, 18, 14, 16), "ativa", "eficiencia"),
        (datetime(2026, 11, 18, 14, 30), "resolvida", "eficiencia"),
    ]
    resumo = r.avaliados[0][1].resumo
    assert resumo == (
        "O aquecedor está a gastar desde as 14:05, e parece que saíram de casa às 14:10: "
        "a porta da rua abriu e as câmaras não viram ninguém a seguir."
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


def test_a_tomada_noutra_divisao():
    # A divisão da tomada vem do inventário: tomada-quarto está no quarto.
    passo("10:00", watts=0, tomada="tomada-quarto", camara_quarto=True)
    assert passo("10:05", tomada="tomada-quarto", camara=True, camara_quarto=True) == []
    [desvio] = desvios(passo("10:20", tomada="tomada-quarto", camara=True, camara_quarto=False))
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


def test_saida_curta_nao_avisa(monkeypatch):
    # Sai às 14:10 e volta às 14:20, antes dos SAIU_MINUTOS (15): a porta a abrir outra vez
    # suspende a saída, e o movimento a seguir desfá-la. Como no histórico (o lixo, o café).
    monkeypatch.setenv("SAIU_MINUTOS", "15")
    monkeypatch.setenv("AUSENCIA_MINUTOS", "120")  # só a saída conta neste teste
    passo("14:00", watts=0, camara=True)
    passo("14:05", camara=True)
    passo("14:10", porta="alarm", camara=False)
    assert passo("14:15", camara=False) == []  # saiu
    assert passo("14:20", porta="alarm", camara=False) == []  # voltou
    assert passo("14:22", camara=True) == []
    assert passo("14:40", camara=True) == []


def test_saida_longa_avisa(monkeypatch):
    monkeypatch.setenv("SAIU_MINUTOS", "15")
    monkeypatch.setenv("AUSENCIA_MINUTOS", "120")
    passo("14:00", watts=0, camara=True)
    passo("14:05", camara=True)
    passo("14:10", porta="alarm", camara=False)
    assert passo("14:24", camara=False) == []

    [desvio] = desvios(passo("14:25", camara=False))
    assert "parece que saíram de casa às 14:10" in desvio.resumo


def test_movimento_depois_da_saida_desfaz_a_saida():
    passo("14:00", watts=0, camara=True)
    passo("14:05", camara=True)
    passo("14:10", porta="alarm", camara=False)
    passo("14:15", camara=False)  # saiu (o aviso espera pelos 10 min da sala)

    assert passo("14:16", camara=False, camara_cozinha=True) == []  # afinal está alguém em casa


# Várias tomadas: cada uma com o seu estado, um aviso de cada vez, com o id da tomada


def duas(hhmm: str, quarto: float = 1500, cozinha: float = 1500, **cameras):
    agora = em(hhmm)
    leituras = [
        Leitura("tomada", "instantPower", quarto, agora, "tomada-quarto"),
        Leitura("tomada", "instantPower", cozinha, agora, "tomada-cozinha"),
        Leitura("porta", "sensorState", "normal", agora),
    ]
    leituras += [Leitura("camara", "motionDetected", valor, agora, CAMARAS[c]) for c, valor in cameras.items()]
    return us14.verificar(leituras, AQUECEDOR, agora)


def depois(hhmm: str, td: timedelta) -> str:
    return f"{em(hhmm) + td:%H:%M}"


def test_duas_tomadas_um_aviso_de_cada_vez():
    limite = habitual.padrao().limite_tomada  # sem câmaras: o limite do histórico
    duas("10:00", cozinha=0)
    duas("10:30")

    [quarto] = desvios(duas(depois("10:00", limite)))
    assert quarto.dispositivo == "tomada-quarto"
    assert quarto.resumo.startswith("A tomada do quarto está a gastar desde as 10:00")  # com várias, o nome do inventário
    assert duas(depois("10:30", limite)) == [quarto]  # a da cozinha também já merece, mas espera

    [resolucao] = duas(depois("10:31", limite), quarto=0)
    assert resolucao == Resolucao("US14", f"a tomada do quarto deixou de gastar às {depois('10:31', limite)}", em(depois("10:31", limite)))
    [cozinha] = desvios(duas(depois("10:32", limite), quarto=0))
    assert cozinha.dispositivo == "tomada-cozinha"
    assert cozinha.resumo.startswith("A tomada da máquina de lavar está a gastar desde as 10:30")


def test_a_outra_tomada_a_parar_nao_resolve_o_aviso():
    limite = habitual.padrao().limite_tomada
    duas("10:00", cozinha=0)
    duas("10:30")
    [quarto] = desvios(duas(depois("10:00", limite)))
    assert duas(depois("10:01", limite), cozinha=0) == [quarto]


def test_com_varias_tomadas_o_nome_do_inventario_diz_se_pode_ficar_sozinho():
    duas("09:55", quarto=0, cozinha=0, camara=False)
    duas("10:00", camara=False)
    [quarto] = desvios(duas("10:15", camara=False))  # o quarto: ninguém lá há AUSENCIA_MINUTOS (15)
    assert quarto.dispositivo == "tomada-quarto"
    duas("10:16", quarto=0, camara=False)
    assert duas("10:45", quarto=0, camara=False) == []  # a máquina de lavar pode ficar sozinha
