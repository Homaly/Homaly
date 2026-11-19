from datetime import UTC, datetime, time, timedelta, timezone

from backend.formatos import Rotina
from backend.resposta.padrao import rotina_repetida
from tests.conftest import AGORA, LX

# AGORA é uma terça às 15:00.
SEMANA = timedelta(days=7)
DIA = timedelta(days=1)
UTEIS = [0, 1, 2, 3, 4]


def _repetida(anteriores, quando=AGORA, us="US07", rotinas=(), recusadas=()):
    return rotina_repetida(us, quando, list(anteriores), list(rotinas), list(recusadas))


def test_tres_tercas_a_mesma_hora_propoe_as_tercas():
    r = _repetida([AGORA - SEMANA + timedelta(minutes=20), AGORA - 2 * SEMANA - timedelta(minutes=10)])
    assert r == Rotina("a porta abre a esta hora", [1], time(15, 0))


def test_duas_vezes_ainda_nao_e_habitual():
    assert _repetida([AGORA - SEMANA]) is None


def test_fora_da_margem_de_uma_hora_nao_conta():
    assert _repetida([AGORA - SEMANA + timedelta(minutes=61), AGORA - 2 * SEMANA]) is None


def test_mais_de_quatro_semanas_nao_conta():
    assert _repetida([AGORA - SEMANA, AGORA - 5 * SEMANA]) is None


def test_dois_avisos_no_mesmo_dia_contam_uma_vez():
    passada = AGORA - SEMANA
    assert _repetida([passada, passada + timedelta(minutes=5)]) is None


def test_outros_dias_da_semana_nao_contam_como_tercas():
    assert _repetida([AGORA - SEMANA, AGORA - 3 * DIA]) is None


def test_tres_dias_uteis_seguidos_propoe_os_dias_uteis():
    # Terça, quarta e quinta.
    quinta = AGORA + 2 * DIA
    r = _repetida([AGORA, AGORA + DIA], quando=quinta)
    assert r is not None and r.dias == UTEIS


def test_tres_dias_seguidos_com_fim_de_semana_propoe_todos_os_dias():
    # Sábado, domingo e segunda.
    segunda = AGORA - DIA
    r = _repetida([segunda - DIA, segunda - 2 * DIA], quando=segunda)
    assert r is not None and r.dias == list(range(7))


def test_a_hora_e_a_mediana_arredondada_a_cinco_minutos():
    r = _repetida([AGORA - SEMANA + timedelta(minutes=32), AGORA - 2 * SEMANA + timedelta(minutes=50)])
    assert r.hora == time(15, 30)


def test_horas_guardadas_em_utc_contam_na_hora_local():
    # Em julho Lisboa está em UTC+1: as 09:00 UTC são as 10:00 de Lisboa.
    quando = datetime(2026, 7, 14, 10, 0, tzinfo=LX)
    anteriores = [datetime(2026, 7, 7, 9, 0, tzinfo=UTC), datetime(2026, 6, 30, 9, 0, tzinfo=UTC)]
    assert _repetida(anteriores, quando=quando).hora == time(10, 0)


def test_a_porta_esquecida_aberta_nunca_e_rotina():
    assert _repetida([AGORA - SEMANA, AGORA - 2 * SEMANA], us="US08") is None


def test_sem_historia_nao_propoe():
    assert _repetida([AGORA - SEMANA, AGORA - 2 * SEMANA], us=None) is None


def test_ja_ha_uma_rotina_que_explica():
    existente = Rotina("a empregada vem", [1], time(14, 30))
    assert _repetida([AGORA - SEMANA, AGORA - 2 * SEMANA], rotinas=[existente]) is None


def test_rotina_sem_hora_desse_dia_tambem_explica():
    existente = Rotina("a empregada vem às terças", [1], None)
    assert _repetida([AGORA - SEMANA, AGORA - 2 * SEMANA], rotinas=[existente]) is None


def test_rotina_de_outro_dia_nao_impede():
    existente = Rotina("ginásio", [3], time(15, 0))
    assert _repetida([AGORA - SEMANA, AGORA - 2 * SEMANA], rotinas=[existente]) is not None


def test_o_que_foi_recusado_nao_volta_a_ser_proposto():
    recusada = Rotina("a porta abre a esta hora", [1], time(15, 0))
    assert _repetida([AGORA - SEMANA, AGORA - 2 * SEMANA], recusadas=[recusada]) is None


def test_historia_sem_frase_usa_uma_frase_geral():
    r = _repetida([AGORA - SEMANA, AGORA - 2 * SEMANA], us="US99")
    assert r.descricao == "isto acontece"


def test_avisos_futuros_nao_contam():
    assert _repetida([AGORA + SEMANA, AGORA + 2 * SEMANA]) is None


def test_a_meia_noite_a_hora_nao_salta_para_o_meio_dia():
    # Quarta 00:05; antes, três quartas entre as 00:00 e as 00:55.
    quando = datetime(2026, 11, 18, 0, 5, tzinfo=LX)
    anteriores = [quando - SEMANA - timedelta(minutes=5), quando - 2 * SEMANA + timedelta(minutes=50), quando - 3 * SEMANA]
    r = _repetida(anteriores, quando=quando)
    assert r is not None and r.hora in (time(0, 0), time(0, 5), time(0, 10))


def test_a_mediana_atravessa_a_meia_noite():
    from backend.resposta.padrao import _mediana

    quando = datetime(2026, 11, 18, 0, 5, tzinfo=LX)
    horas = [quando, quando.replace(hour=23, minute=55), quando.replace(hour=23, minute=55), quando]
    assert _mediana(quando, horas) == time(0, 0)


def test_quatro_semanas_contam_o_dia_todo():
    # Há quatro semanas às 14:30, meia hora antes da hora de AGORA nesse dia: ainda conta.
    assert _repetida([AGORA - 4 * SEMANA - timedelta(minutes=30), AGORA - SEMANA]) is not None


def test_desvio_fixo_conta_com_a_hora_de_verao():
    # O JSON traz desvios fixos: +01:00 no verão. Em julho, 09:00 UTC são as 10:00 de Lisboa.
    quando = datetime(2026, 7, 14, 10, 0, tzinfo=LX).astimezone(timezone(timedelta(hours=1)))
    anteriores = [datetime(2026, 7, 7, 9, 0, tzinfo=UTC), datetime(2026, 6, 30, 9, 0, tzinfo=UTC)]
    assert _repetida(anteriores, quando=quando) is not None
