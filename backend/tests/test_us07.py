"""Os casos de dados/us07.csv."""

from datetime import datetime, time

from backend.formatos import Contexto, Periodo, Rotina
from backend.regras import us07
from tests.regras_casa import Registo

FERIAS = Periodo(datetime(2026, 11, 23), datetime(2026, 11, 29, 23, 59), "férias no Algarve")
EMPREGADA = Rotina("a empregada vem às terças", dias=[1], hora=time(22, 0))


def test_casos_da_us07():
    contexto = Contexto(ferias=[FERIAS], rotinas=[EMPREGADA], silencios=[], casa_vazia=False)
    r = Registo(us07, contexto).correr("us07.csv")

    avisos = [(quando, d.imediato) for quando, d in r.avaliados]
    assert avisos == [
        (datetime(2026, 11, 17, 3, 10), False),  # madrugada
        (datetime(2026, 11, 23, 15, 0), True),  # férias
        (datetime(2026, 11, 24, 22, 0), True),  # férias, mesmo à hora da rotina
    ]
    assert all(d.classe == "seguranca" for _, d in r.avaliados)
    # Só se resolve com resposta: nada passa a resolvida quando a porta fecha.
    assert all(estado == "ativa" for _, estado, _ in r.publicadas)


def test_resumo_e_habitual():
    r = Registo(us07, Contexto([FERIAS], [], [], False)).correr("us07.csv")
    madrugada, ferias = r.avaliados[0][1], r.avaliados[1][1]
    assert madrugada.resumo == "A porta abriu às 03:10, num dia útil, a uma hora em que nunca abre."
    assert madrugada.habitual == "Nos dias úteis, a porta costuma abrir entre as 07:30 e as 19:30."
    assert ferias.resumo == "A porta abriu às 15:00 com a casa vazia (férias no Algarve)."


def test_sem_rotina_a_terca_as_22_avisa():
    r = Registo(us07, Contexto([], [], [], False)).correr("us07.csv")
    assert datetime(2026, 12, 1, 22, 0) in [quando for quando, _ in r.avaliados]
