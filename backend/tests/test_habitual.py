from datetime import datetime, time, timedelta

from backend import habitual
from backend.sinais import Sinal


def test_janelas_da_porta_por_tipo_de_dia():
    h = habitual.padrao()
    assert h.porta == {"util": (time(7, 30), time(19, 30)), "fim_de_semana": (time(9, 30), time(23, 0))}


def test_margem_de_uma_hora():
    h = habitual.padrao()
    terca = datetime(2026, 11, 17)
    assert h.porta_normal(terca.replace(hour=6, minute=30))
    assert not h.porta_normal(terca.replace(hour=6, minute=29))
    assert h.porta_normal(terca.replace(hour=20, minute=30))
    assert not h.porta_normal(terca.replace(hour=20, minute=31))
    assert not h.porta_normal(datetime(2026, 11, 21, 8, 0))  # sábado
    assert not h.porta_normal(datetime(2026, 11, 21, 3, 0))


def test_tomada_no_maximo_uma_hora_e_aviso_as_tres():
    h = habitual.padrao()
    assert h.tomada_max == timedelta(hours=1)
    assert h.limite_tomada == timedelta(hours=3)
    assert h.texto_tomada() == "Costuma estar a gastar no máximo 1 h de seguida."


def test_a_semana_de_ferias_nao_conta(tmp_path):
    csv = tmp_path / "h.csv"
    csv.write_text(
        "dispositivo,tipo,valor,em\n"
        "porta,sensorState,alarm,2026-10-20T08:00:00\n"
        "porta,sensorState,alarm,2026-11-03T03:00:00\n"  # dentro das férias do histórico
        "tomada,instantPower,200,2026-11-03T10:00:00\n"
        "tomada,instantPower,0,2026-11-03T20:00:00\n"
    )
    h = habitual.carregar(csv)
    assert h.porta == {"util": (time(8, 0), time(8, 0))}
    assert h.tomada_max == timedelta(0)


def test_primeira_abertura_e_limite_da_us09():
    h = habitual.padrao()
    assert h.primeira_abertura == {"util": time(8, 30), "fim_de_semana": time(11, 0)}
    assert h.limite_porta_nao_abriu(datetime(2026, 11, 20)) == time(9, 0)  # sexta
    assert h.limite_porta_nao_abriu(datetime(2026, 11, 21)) == time(11, 30)  # sábado
    assert h.texto_primeira_abertura(datetime(2026, 11, 20)) == (
        "Nos dias úteis, a porta costuma abrir pela primeira vez até às 08:30."
    )


def test_excluir_dias(tmp_path):
    csv = tmp_path / "h.csv"
    csv.write_text(
        "dispositivo,tipo,valor,em\n"
        "porta,sensorState,alarm,2026-10-20T08:00:00\n"
        "porta,sensorState,alarm,2026-10-21T09:15:00\n"
    )
    h = habitual.carregar(csv, excluir={datetime(2026, 10, 21).date()})
    assert h.primeira_abertura == {"util": time(8, 0)}


def test_primeiro_sinal_e_limite_da_us09():
    h = habitual.padrao()
    assert h.primeiro_sinal == {"util": time(7, 15), "fim_de_semana": time(8, 0)}
    assert h.limite_sem_sinais(datetime(2026, 11, 20)) == time(8, 45)  # sexta
    assert h.limite_sem_sinais(datetime(2026, 11, 21)) == time(9, 30)  # sábado
    assert h.texto_primeiro_sinal(datetime(2026, 11, 20)) == (
        "Nos dias úteis, o primeiro sinal de vida costuma chegar até às 07:15."
    )


def test_horas_com_atividade():
    h = habitual.padrao()
    assert {7, 19, 20, 21, 22} <= h.atividade["util"]
    assert not {3, 12, 15} & h.atividade["util"]  # a dormir ou no trabalho
    assert {13, 14} <= h.atividade["fim_de_semana"]
    assert 3 not in h.atividade["fim_de_semana"]


def test_tempo_ativo_so_conta_as_horas_com_atividade():
    h = habitual.Habitual(porta={}, tomada_max=timedelta(0), primeira_abertura={},
                          primeiro_sinal={}, atividade={"util": frozenset({6, 7, 19, 20, 21, 22}),
                                                        "fim_de_semana": frozenset()})
    sexta = lambda hh, mm=0: datetime(2026, 11, 20, hh, mm)
    assert h.tempo_ativo(sexta(19, 30), sexta(22, 30)) == timedelta(hours=3)
    assert h.tempo_ativo(sexta(0, 30), sexta(7, 0)) == timedelta(hours=1)  # Review Focus 4: o sono não conta
    assert h.tempo_ativo(sexta(22, 30), datetime(2026, 11, 21, 9, 0)) == timedelta(minutes=30)  # sábado sem atividade
    assert h.texto_atividade(sexta(10)) == (
        "Nos dias úteis, costuma haver atividade das 06:00 às 08:00 e das 19:00 às 23:00."
    )


def test_os_sinais_das_ferias_nao_contam(tmp_path):
    csv = tmp_path / "h.csv"
    csv.write_text(
        "dispositivo,tipo,valor,em\n"
        "lampada,power,on,2026-10-20T06:50:00\n"
        "lampada,power,off,2026-11-03T03:00:00\n"  # dentro das férias do histórico
    )
    assert habitual.sinais_de_vida(csv) == [Sinal("lampada", "a luz ligada", datetime(2026, 10, 20, 6, 50))]
    assert habitual.carregar(csv).primeiro_sinal == {"util": time(6, 50)}
