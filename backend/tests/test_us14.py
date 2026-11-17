"""Os casos de dados/us14.csv."""

from datetime import datetime

from backend.formatos import Contexto, Periodo
from backend.regras import us14
from tests.regras_casa import Registo

FERIAS = Periodo(datetime(2026, 11, 23), datetime(2026, 11, 29, 23, 59), "férias no Algarve")


def test_casos_da_us14():
    contexto = Contexto([FERIAS], [], [], False, aparelho_tomada="o desumidificador")
    r = Registo(us14, contexto).correr("us14.csv")

    assert r.publicadas == [
        (datetime(2026, 11, 18, 17, 0), "ativa", "eficiencia"),  # 3 h a gastar
        (datetime(2026, 11, 18, 17, 30), "resolvida", "eficiencia"),  # deixou de gastar
        (datetime(2026, 11, 23, 10, 0), "ativa", "seguranca"),  # de férias: logo que gasta
        (datetime(2026, 11, 23, 10, 30), "resolvida", "seguranca"),
    ]
    eficiencia, ferias = r.avaliados[0][1], r.avaliados[1][1]
    assert eficiencia.resumo == "O desumidificador está a gastar desde as 14:00, há mais de 3 h de seguida."
    assert not eficiencia.imediato
    assert ferias.imediato
    assert ferias.resumo == "O desumidificador está a gastar desde as 10:00, com a casa vazia (férias no Algarve)."


def test_sem_nome_diz_o_aparelho_na_tomada():
    r = Registo(us14, Contexto([], [], [], False)).correr("us14.csv")
    assert r.avaliados[0][1].resumo.startswith("O aparelho na tomada está a gastar desde as 14:00")


def test_resolve_dizendo_quando_deixou_de_gastar():
    contexto = Contexto([FERIAS], [], [], False, aparelho_tomada="o desumidificador")
    r = Registo(us14, contexto).correr("us14.csv")
    assert r.resolucoes == ["o desumidificador deixou de gastar às 17:30", "o desumidificador deixou de gastar às 10:30"]
    r = Registo(us14, Contexto([], [], [], False)).correr("us14.csv")
    assert r.resolucoes[0] == "o aparelho na tomada deixou de gastar às 17:30"
