"""O histórico é normal: passado pelas regras, não pode dar avisos (ver backend.afinacao)."""

from datetime import date

from backend import afinacao, habitual


def test_o_historico_completo_nao_da_avisos():
    mudancas = afinacao._mudancas(habitual.HISTORICO)
    dias = [d for bloco in afinacao.blocos(mudancas) for d in bloco]
    assert afinacao.avisos_em(habitual.carregar(), mudancas, dias) == []


def test_cada_semana_com_o_habitual_das_outras_nao_da_avisos():
    falsos, menor, _ = afinacao.relatorio()
    assert sum(falsos.values()) == 0
    assert all(folga is not None and folga.total_seconds() >= 0 for folga in menor.values())


def test_os_pollings_levam_a_camara_e_a_lampada():
    mudancas = afinacao._mudancas(habitual.HISTORICO)
    _, leituras = next(afinacao.pollings(mudancas, [date(2026, 10, 21)]))
    assert {(l.dispositivo, l.tipo) for l in leituras} >= {
        ("porta", "sensorState"), ("tomada", "instantPower"), ("lampada", "power"), ("camara", "motionDetected")
    }
