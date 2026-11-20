"""A regra da porta: US08 (esquecida aberta) e US12 (aberta com a sala a arrefecer), um só aviso."""

from datetime import timedelta

import pytest

from backend.formatos import Contexto, Desvio, Leitura, Resolucao
from backend.regras import porta

from .conftest import AGORA

CONTEXTO = Contexto(ferias=[], rotinas=[], silencios=[], casa_vazia=False)


def minuto(m: float):
    return AGORA + timedelta(minutes=m)


def leituras(m: float, porta_estado: str | None, temperatura: float | None = None) -> list[Leitura]:
    em = minuto(m)
    lidas = []
    if porta_estado is not None:
        lidas.append(Leitura("porta", "sensorState", porta_estado, em))
    if temperatura is not None:
        lidas.append(Leitura("temperatura", "temperatureValue", temperatura, em))
    return lidas


def ver(m: float, porta_estado: str | None, temperatura: float | None = None) -> list[Desvio | Resolucao]:
    return porta.verificar(leituras(m, porta_estado, temperatura), CONTEXTO, minuto(m))


# US08


def test_porta_fechada_nao_da_nada():
    assert ver(0, "normal", 20.0) == []


def test_porta_fecha_antes_dos_cinco_minutos_nao_da_nada():
    assert ver(0, "alarm", 20.0) == []
    assert ver(4, "alarm", 20.0) == []
    assert ver(4.5, "normal", 20.0) == []


def test_aberta_cinco_minutos_da_aviso_de_seguranca():
    ver(0, "alarm", 20.0)

    [desvio] = ver(5, "alarm", 20.0)

    assert desvio.us == "US08"
    assert desvio.classe == "seguranca"
    assert desvio.resumo == "A porta da rua está aberta há mais de 5 minutos, desde as 15:00."
    assert desvio.imediato is False


def test_o_aviso_repete_igual_enquanto_a_porta_esta_aberta():
    ver(0, "alarm", 20.0)
    primeiro = ver(5, "alarm", 20.0)

    assert ver(6, "alarm", 20.0) == primeiro
    assert ver(30, "alarm", 20.0) == primeiro


def test_porta_fecha_depois_do_aviso_resolve_com_a_hora():
    ver(0, "alarm", 20.0)
    ver(5, "alarm", 20.0)

    assert ver(12, "normal", 20.0) == [Resolucao("US08", "a porta fechou às 15:12", minuto(12))]
    assert ver(13, "normal", 20.0) == []


def test_nova_abertura_conta_do_zero():
    ver(0, "alarm")
    ver(5, "alarm")
    ver(6, "normal")

    assert ver(10, "alarm") == []
    assert ver(14, "alarm") == []
    [desvio] = ver(15, "alarm")
    assert desvio.resumo.endswith("desde as 15:10.")


def test_volta_sem_leitura_da_porta_mantem_o_aviso():
    # Uma falha do MCP não pode resolver o aviso por engano.
    ver(0, "alarm")
    aviso = ver(5, "alarm")

    assert ver(6, None) == aviso


def test_volta_sem_leitura_conta_como_a_ultima_conhecida():
    ver(0, "alarm")

    [desvio] = ver(5, None)
    assert desvio.us == "US08"


def test_valor_desconhecido_da_porta_conta_como_sem_leitura():
    ver(0, "alarm")
    aviso = ver(5, "alarm")

    assert ver(6, "") == aviso


def test_sem_nenhuma_leitura_nao_da_nada():
    assert ver(0, None) == []


def test_hora_sem_fuso_conta_como_hora_local():
    ver(0, "alarm")
    sem_fuso = minuto(5).astimezone().replace(tzinfo=None)  # o mesmo instante, sem fuso

    [desvio] = porta.verificar(leituras(5, "alarm"), CONTEXTO, sem_fuso)

    assert desvio.us == "US08"


def test_estado_com_hora_no_futuro_recomeca():
    # Ex.: correu-se um CSV de outro dia contra a mesma base de dados.
    ver(60, "alarm")

    assert ver(0, "alarm") == []
    [desvio] = ver(5, "alarm")
    assert desvio.resumo.endswith("desde as 15:00.")


def test_minutos_da_porta_configuraveis(monkeypatch):
    monkeypatch.setenv("PORTA_MINUTOS", "1")
    ver(0, "alarm")

    [desvio] = ver(1, "alarm")
    assert "há mais de 1 minuto," in desvio.resumo


# US12


def test_sala_desce_dois_graus_com_a_porta_aberta_da_aviso_de_eficiencia():
    ver(0, "alarm", 20.5)
    assert ver(1, "alarm", 19.0) == []

    [desvio] = ver(2, "alarm", 18.4)

    assert desvio.us == "US12"
    assert desvio.classe == "eficiencia"
    assert desvio.resumo == (
        "A porta da rua está aberta desde as 15:00 e a sala já desceu 2,1 °C (de 20,5 °C para 18,4 °C)."
    )


def test_descida_menor_que_dois_graus_nao_da_nada():
    ver(0, "alarm", 20.0)

    assert ver(3, "alarm", 18.5) == []


def test_o_aviso_da_us12_nao_muda_enquanto_a_sala_continua_a_arrefecer():
    ver(0, "alarm", 20.0)
    aviso = ver(1, "alarm", 18.0)

    assert ver(2, "alarm", 17.0) == aviso


def test_us12_primeiro_passa_a_seguranca_aos_cinco_minutos_com_a_mesma_us():
    ver(0, "alarm", 20.0)
    ver(2, "alarm", 18.0)

    [desvio] = ver(5, "alarm", 17.5)

    assert desvio.us == "US12"  # o mesmo aviso: o ciclo atualiza-o em vez de criar outro
    assert desvio.classe == "seguranca"
    assert desvio.resumo == (
        "A porta da rua está aberta há mais de 5 minutos, desde as 15:00, e a sala já desceu 2 °C."
    )


def test_us08_primeiro_acrescenta_a_descida_ao_mesmo_aviso():
    ver(0, "alarm", 20.0)
    ver(5, "alarm", 19.5)

    [desvio] = ver(7, "alarm", 17.9)

    assert desvio.us == "US08"
    assert desvio.classe == "seguranca"
    assert desvio.resumo.endswith("desde as 15:00, e a sala já desceu 2,1 °C.")


def test_porta_fecha_resolve_o_aviso_da_us12():
    ver(0, "alarm", 20.0)
    ver(2, "alarm", 18.0)

    assert ver(3, "normal", 18.0) == [Resolucao("US12", "a porta fechou às 15:03", minuto(3))]


def test_temperatura_inicial_chega_depois_da_porta_abrir():
    ver(0, "alarm", None)
    ver(1, "alarm", 20.0)

    [desvio] = ver(2, "alarm", 18.0)
    assert desvio.us == "US12"


def test_descida_configuravel(monkeypatch):
    monkeypatch.setenv("PORTA_QUEDA_GRAUS", "0.5")
    ver(0, "alarm", 20.0)

    [desvio] = ver(1, "alarm", 19.5)
    assert desvio.us == "US12"


def test_configuracao_invalida_diz_qual(monkeypatch):
    monkeypatch.setenv("PORTA_MINUTOS", "cinco")

    with pytest.raises(ValueError, match="PORTA_MINUTOS"):
        ver(0, "alarm")


# Várias aberturas e várias divisões (inventário CASA, em conftest.py)


def casa_volta(m: float, **valores) -> list[Desvio | Resolucao]:
    """Uma volta com o estado de cada sensor do inventário de teste: porta_rua="alarm", temp_quarto=18.0."""
    em = minuto(m)
    lidas = []
    for nome, valor in valores.items():
        chave = nome.replace("_", "-")
        dispositivo = "temperatura" if chave.startswith("temp") else "porta"
        tipo = "temperatureValue" if dispositivo == "temperatura" else "sensorState"
        lidas.append(Leitura(dispositivo, tipo, valor, em, chave))
    return porta.verificar(lidas, CONTEXTO, em)


@pytest.mark.usefixtures("casa")
def test_janela_aberta_com_o_quarto_a_arrefecer_mais_do_que_o_resto_da_casa():
    casa_volta(0, janela_quarto="alarm", temp_quarto=20.0, temp_sala=21.0)

    [desvio] = casa_volta(10, janela_quarto="alarm", temp_quarto=17.8, temp_sala=20.8)

    assert desvio.us == "US12"
    assert desvio.classe == "eficiencia"
    assert desvio.resumo == (
        "A janela do quarto está aberta desde as 15:00 e o quarto já desceu 2,2 °C "
        "(de 20 °C para 17,8 °C). O resto da casa desceu só 0,2 °C."
    )


@pytest.mark.usefixtures("casa")
def test_a_casa_toda_a_arrefecer_nao_e_da_janela():
    casa_volta(0, janela_quarto="alarm", temp_quarto=20.0, temp_sala=21.0)

    assert casa_volta(10, janela_quarto="alarm", temp_quarto=17.8, temp_sala=19.5) == []  # 2,2 contra 1,5


@pytest.mark.usefixtures("casa")
def test_a_referencia_e_a_media_das_outras_divisoes():
    casa_volta(0, janela_quarto="alarm", temp_quarto=20.0, temp_sala=21.0, temp_cozinha=22.0)

    # A sala desceu 0,4 e a cozinha 1,6: o resto da casa desceu 1 °C, o quarto 2,1.
    [desvio] = casa_volta(10, janela_quarto="alarm", temp_quarto=17.9, temp_sala=20.6, temp_cozinha=20.4)
    assert desvio.resumo.endswith("O resto da casa desceu só 1 °C.")


@pytest.mark.usefixtures("casa")
def test_janela_numa_divisao_sem_sensor_de_temperatura_nao_avisa():
    casa_volta(0, janela_quarto="alarm", temp_sala=21.0)

    assert casa_volta(30, janela_quarto="alarm", temp_sala=18.0) == []


@pytest.mark.usefixtures("casa")
def test_uma_janela_aberta_nunca_passa_a_seguranca():
    casa_volta(0, janela_quarto="alarm", temp_quarto=20.0)

    assert casa_volta(30, janela_quarto="alarm", temp_quarto=20.0) == []
    [desvio] = casa_volta(40, janela_quarto="alarm", temp_quarto=17.5)
    assert (desvio.us, desvio.classe) == ("US12", "eficiencia")
    assert casa_volta(60, janela_quarto="alarm", temp_quarto=17.0) == [desvio]


@pytest.mark.usefixtures("casa")
def test_janela_fecha_resolve_com_o_nome_da_janela():
    casa_volta(0, janela_quarto="alarm", temp_quarto=20.0)
    casa_volta(10, janela_quarto="alarm", temp_quarto=17.5)

    assert casa_volta(12, janela_quarto="normal", temp_quarto=17.5) == [
        Resolucao("US12", "a janela do quarto fechou às 15:12", minuto(12))
    ]


@pytest.mark.usefixtures("casa")
def test_cada_abertura_tem_o_seu_estado():
    # A janela da sala abre às 15:00 e a do quarto às 15:05: cada uma conta desde a sua hora.
    casa_volta(0, janela_sala="alarm", janela_quarto="normal", temp_sala=21.0, temp_quarto=20.0)
    casa_volta(5, janela_sala="alarm", janela_quarto="alarm", temp_sala=20.0, temp_quarto=20.0)
    casa_volta(6, janela_sala="normal", janela_quarto="alarm", temp_sala=20.0, temp_quarto=20.0)

    # A sala desceu 1 °C e fechou; o quarto desce 2 °C desde as 15:05.
    [desvio] = casa_volta(15, janela_sala="normal", janela_quarto="alarm", temp_sala=20.0, temp_quarto=18.0)
    assert desvio.resumo.startswith("A janela do quarto está aberta desde as 15:05 e o quarto já desceu 2 °C")


@pytest.mark.usefixtures("casa")
def test_a_segunda_abertura_espera_que_a_primeira_feche():
    # O ciclo só tem um aviso da US12 de cada vez.
    casa_volta(0, janela_sala="alarm", janela_quarto="alarm", temp_sala=20.0, temp_quarto=20.0, temp_cozinha=20.0)
    [sala] = casa_volta(10, janela_sala="alarm", janela_quarto="alarm", temp_sala=18.0, temp_quarto=18.0, temp_cozinha=20.0)
    assert sala.resumo.startswith("A janela da sala")

    assert casa_volta(11, janela_sala="alarm", janela_quarto="alarm", temp_sala=18.0, temp_quarto=18.0, temp_cozinha=20.0) == [sala]
    [resolvida] = casa_volta(12, janela_sala="normal", janela_quarto="alarm", temp_sala=18.0, temp_quarto=18.0, temp_cozinha=20.0)
    assert resolvida == Resolucao("US12", "a janela da sala fechou às 15:12", minuto(12))
    [quarto] = casa_volta(13, janela_sala="normal", janela_quarto="alarm", temp_sala=18.0, temp_quarto=18.0, temp_cozinha=20.0)
    assert quarto.resumo.startswith("A janela do quarto")


@pytest.mark.usefixtures("casa")
def test_porta_e_janela_abertas_ao_mesmo_tempo_dao_us08_e_us12():
    casa_volta(0, porta_rua="alarm", janela_quarto="alarm", temp_quarto=20.0, temp_sala=21.0)

    desvios = casa_volta(5, porta_rua="alarm", janela_quarto="alarm", temp_quarto=17.9, temp_sala=21.0)

    assert {(d.us, d.classe) for d in desvios} == {("US08", "seguranca"), ("US12", "eficiencia")}
