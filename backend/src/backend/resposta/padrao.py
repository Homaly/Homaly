"""A casa repara quando um aviso começa a ser habitual e propõe uma rotina (US02).

Não depende do que a pessoa responde: olha só para os avisos anteriores da mesma história.
"A mesma coisa" é um aviso da mesma US a menos de `MARGEM_ROTINA` (1 h) da hora deste.
Começa a ser habitual com `REPETICOES` dias diferentes:
- no mesmo dia da semana, nas últimas `SEMANAS` semanas: rotina nesse dia;
- em dias seguidos: rotina nos dias úteis se forem todos úteis, senão todos os dias.
A rotina só se guarda se a pessoa aceitar (`responder.aplicar`).
"""

from datetime import date, datetime, time, timedelta
from statistics import median
from zoneinfo import ZoneInfo

from backend.formatos import Rotina
from backend.ia.avaliar import AVISA_SEMPRE
from backend.regras import MARGEM_ROTINA

REPETICOES = 3
SEMANAS = 4
ARREDONDAR_MINUTOS = 5
DIAS_UTEIS = [0, 1, 2, 3, 4]
TODOS_OS_DIAS = list(range(7))

# O que se repete, dito como rotina ("Passo a contar com isso: a porta abre a esta hora").
DESCRICAO_POR_US = {
    "US07": "a porta abre a esta hora",
    "US09": "a porta só abre mais tarde",
    "US10": "a casa fica mais fria",
    "US11": "a luz fica acesa mais tempo",
    "US12": "a porta fica aberta com a sala a arrefecer",
    "US14": "o aparelho da tomada fica ligado mais tempo",
}
DESCRICAO_GERAL = "isto acontece"


def rotina_repetida(
    us: str | None,
    quando: datetime,
    anteriores: list[datetime],
    rotinas: list[Rotina],
    recusadas: list[Rotina],
) -> Rotina | None:
    """A rotina a propor se o aviso de `quando` já se repetiu; senão `None`.

    `anteriores` são as horas de deteção dos outros avisos da mesma US (em qualquer fuso).
    """
    if us is None or us in AVISA_SEMPRE:
        return None
    quando = _local(quando, quando)
    perto = _a_mesma_hora(quando, [_local(a, quando) for a in anteriores])
    escolhidos = _mesmo_dia_da_semana(quando, perto) or _dias_seguidos(quando, perto)
    if escolhidos is None:
        return None
    dias, horas = escolhidos
    rotina = Rotina(DESCRICAO_POR_US.get(us, DESCRICAO_GERAL), dias, _mediana(quando, horas))
    if _explicada(rotina, rotinas) or _recusada(rotina, recusadas):
        return None
    return rotina


def _minutos_entre(a: time, b: time) -> int:
    """Distância entre duas horas do dia, passando a meia-noite se for mais perto."""
    d = abs((a.hour * 60 + a.minute) - (b.hour * 60 + b.minute))
    return min(d, 24 * 60 - d)


def _perto(a: time, b: time) -> bool:
    return _minutos_entre(a, b) <= MARGEM_ROTINA.total_seconds() // 60


def _local(d: datetime, quando: datetime) -> datetime:
    """`d` na hora local, com a hora de verão certa para esse dia.

    Um fuso com nome (Europe/Lisbon) já sabe a hora de verão; um desvio fixo (+00:00, como o
    que vem do JSON) não sabe, por isso usa-se o fuso da máquina, como o resto da casa.
    """
    return d.astimezone(quando.tzinfo) if isinstance(quando.tzinfo, ZoneInfo) else d.astimezone()


def _a_mesma_hora(quando: datetime, anteriores: list[datetime]) -> dict[date, datetime]:
    """Um aviso por dia (o primeiro), nos dias antes de `quando`, a menos da margem da sua hora."""
    primeiro_dia = quando.date() - timedelta(weeks=SEMANAS)
    por_dia: dict[date, datetime] = {}
    for a in sorted(anteriores):
        if primeiro_dia <= a.date() < quando.date() and _perto(a.time(), quando.time()):
            por_dia.setdefault(a.date(), a)
    return por_dia


def _mesmo_dia_da_semana(
    quando: datetime, por_dia: dict[date, datetime]
) -> tuple[list[int], list[datetime]] | None:
    iguais = [a for d, a in por_dia.items() if d.weekday() == quando.weekday()]
    if len(iguais) + 1 < REPETICOES:
        return None
    return [quando.weekday()], [quando, *iguais]


def _dias_seguidos(
    quando: datetime, por_dia: dict[date, datetime]
) -> tuple[list[int], list[datetime]] | None:
    antes = [quando.date() - timedelta(days=n) for n in range(1, REPETICOES)]
    if not all(d in por_dia for d in antes):
        return None
    uteis = all(d.weekday() in DIAS_UTEIS for d in [quando.date(), *antes])
    return (DIAS_UTEIS if uteis else TODOS_OS_DIAS), [quando, *(por_dia[d] for d in antes)]


def _mediana(quando: datetime, horas: list[datetime]) -> time:
    """A hora do meio, contada a partir da de `quando` para não se perder à meia-noite
    (23:55 e 00:05 dão 00:00, não 12:00)."""
    base = quando.hour * 60 + quando.minute
    desvios = [((h.hour * 60 + h.minute - base + 12 * 60) % (24 * 60)) - 12 * 60 for h in horas]
    minutos = base + median(desvios)
    arredondado = int(round(minutos / ARREDONDAR_MINUTOS) * ARREDONDAR_MINUTOS) % (24 * 60)
    return time(arredondado // 60, arredondado % 60)


def _cobre(existente: Rotina, nova: Rotina) -> bool:
    """`existente` já fala dos dias e da hora de `nova` (sem hora, basta o dia)."""
    if not set(nova.dias) <= set(existente.dias):
        return False
    return existente.hora is None or (nova.hora is not None and _perto(existente.hora, nova.hora))


def _explicada(rotina: Rotina, rotinas: list[Rotina]) -> bool:
    return any(_cobre(r, rotina) for r in rotinas)


def _recusada(rotina: Rotina, recusadas: list[Rotina]) -> bool:
    return any(_cobre(r, rotina) for r in recusadas)
