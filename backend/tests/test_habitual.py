from datetime import datetime, time, timedelta

from backend import habitual


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
