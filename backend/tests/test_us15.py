"""Os casos de dados/us15.csv: torneira esquecida, fio de água de madrugada, cano rebentado, férias."""

from datetime import datetime

import pytest

from backend.formatos import Contexto, Leitura, Periodo
from backend.regras import us15
from tests.regras_casa import Registo

FERIAS = Periodo(datetime(2026, 11, 23), datetime(2026, 11, 29, 23, 59), "férias no Algarve")


@pytest.fixture
def registo():
    return Registo(us15, Contexto([FERIAS], [], [], False)).correr("us15.csv")


def test_casos_da_us15(registo):
    assert registo.publicadas == [
        (datetime(2026, 11, 17, 19, 0), "ativa", "eficiencia"),  # torneira: 1 h a correr
        (datetime(2026, 11, 17, 19, 20), "resolvida", "eficiencia"),
        (datetime(2026, 11, 18, 3, 0), "ativa", "eficiencia"),  # fio de água de madrugada
        (datetime(2026, 11, 18, 3, 20), "resolvida", "eficiencia"),
        (datetime(2026, 11, 18, 12, 5), "ativa", "seguranca"),  # cano: 5 min de muita água
        (datetime(2026, 11, 18, 12, 7), "resolvida", "seguranca"),
        (datetime(2026, 11, 24, 10, 0), "ativa", "seguranca"),  # de férias: logo que corre
        (datetime(2026, 11, 24, 10, 5), "resolvida", "seguranca"),
    ]


def test_resumos(registo):
    torneira, fio, cano, ferias = (d for _, d in registo.avaliados)
    assert torneira.resumo == (
        "A água está a correr sem parar desde as 18:00, há mais de 1 h. Uma torneira pode ter ficado aberta."
    )
    assert fio.resumo == (
        "Corre um fio de água sem parar desde as 02:00, há mais de 1 h. Pode ser um autoclismo ou uma torneira a pingar."
    )
    assert cano.resumo == (
        "Está a correr muita água sem parar desde as 12:00 (mais de 12 litros por minuto). Pode ser um cano rebentado."
    )
    assert ferias.resumo == "Está a correr água desde as 10:00, com a casa vazia (férias no Algarve)."
    assert [d.imediato for d in (torneira, fio, cano, ferias)] == [False, False, True, True]


def test_resolve_com_os_litros_que_correram(registo):
    assert registo.resolucoes == [
        "a água parou às 19:20 (correram cerca de 480 litros)",
        "a água parou às 03:20 (correram cerca de 24 litros)",
        "a água parou às 12:07 (correram cerca de 140 litros)",
        "a água parou às 10:05 (correram cerca de 8 litros)",
    ]


def _ler(caudal: float, h: int, m: int = 0) -> list[Leitura]:
    return [Leitura("agua", "caudal", caudal, datetime(2026, 11, 18, h, m))]


def test_uso_normal_nao_avisa():
    us15.reiniciar()
    contexto = Contexto([], [], [], False)
    assert us15.verificar(_ler(8, 8), contexto, datetime(2026, 11, 18, 8)) == []
    assert us15.verificar(_ler(8, 8, 20), contexto, datetime(2026, 11, 18, 8, 20)) == []
    fim = us15.verificar(_ler(0, 8, 30), contexto, datetime(2026, 11, 18, 8, 30))
    assert [r.texto for r in fim] == ["a água parou às 08:30 (correram cerca de 240 litros)"]


def test_sem_leitura_do_contador_conta_como_parada():
    """O contador só existe injetado: se a leitura foi removida, o aviso fecha-se."""
    us15.reiniciar()
    contexto = Contexto([], [], [], False)
    us15.verificar(_ler(1, 2), contexto, datetime(2026, 11, 18, 2))
    (fim,) = us15.verificar([], contexto, datetime(2026, 11, 18, 2, 30))
    assert fim.texto == "o contador da água deixou de dar leituras às 02:30"
    assert us15.verificar([], contexto, datetime(2026, 11, 18, 2, 40)) == []


def test_o_aviso_de_cano_nao_se_cala_com_a_agua_a_correr():
    """Depois do cano (segurança), o caudal desce para 8 L/min: o aviso fica até a água parar."""
    us15.reiniciar()
    contexto = Contexto([], [], [], False)
    for m in range(6):
        saida = us15.verificar(_ler(15, 12, m), contexto, datetime(2026, 11, 18, 12, m))
    assert saida[0].classe == "seguranca"
    saida = us15.verificar(_ler(8, 12, 10), contexto, datetime(2026, 11, 18, 12, 10))
    assert [d.classe for d in saida] == ["seguranca"]
    saida = us15.verificar(_ler(8, 13, 30), contexto, datetime(2026, 11, 18, 13, 30))  # passa 1 h
    assert [d.classe for d in saida] == ["seguranca"]


def test_uma_descida_curta_nao_recomeca_a_contagem_do_cano():
    us15.reiniciar()
    contexto = Contexto([], [], [], False)
    for m, caudal in enumerate([15, 15, 11.9, 15, 15, 15]):
        saida = us15.verificar(_ler(caudal, 12, m), contexto, datetime(2026, 11, 18, 12, m))
    assert [d.classe for d in saida] == ["seguranca"]


def test_depois_de_um_reinicio_a_agua_parada_fecha_o_aviso():
    us15.reiniciar()
    (fim,) = us15.verificar(_ler(0, 9), Contexto([], [], [], False), datetime(2026, 11, 18, 9))
    assert fim.texto == "a água já não estava a correr às 09:00"


def test_limites_vem_do_ambiente(monkeypatch):
    monkeypatch.setenv("AGUA_MINUTOS", "2")
    us15.reiniciar()
    contexto = Contexto([], [], [], False)
    us15.verificar(_ler(5, 9), contexto, datetime(2026, 11, 18, 9))
    assert us15.verificar(_ler(5, 9, 2), contexto, datetime(2026, 11, 18, 9, 2))[0].classe == "eficiencia"
