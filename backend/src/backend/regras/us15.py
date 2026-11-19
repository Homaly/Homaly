"""US15: água a correr sem parar (fuga, torneira esquecida ou cano rebentado).

Lê o contador de água ("agua", "caudal", em litros por minuto). O kit não o tem: na demo o
caudal entra por `/dev/leituras`. "A correr" é caudal acima de AGUA_LIMITE_LMIN (0,1 L/min).

- Casa vazia (férias ditas à casa): segurança e imediato, logo que a água corre.
- Muita água (CANO_LMIN, 12 L/min, ou mais) durante CANO_MINUTOS (5): segurança e imediato,
  porque pode ser um cano rebentado.
- Água a correr sem parar há AGUA_MINUTOS (60): eficiência. Se o caudal médio for baixo (menos
  de FUGA_LMIN, 2 L/min), é um fio de água, como um autoclismo a pingar; senão, uma torneira
  que ficou aberta.

Quando a água pára, a regra devolve a Resolucao com os litros que correram. O resumo não muda
enquanto o desvio dura (só a classe, quando sobe para segurança), para o ciclo não voltar a
publicar a cada polling. Depois de avisar, o aviso só acaba quando a água pára: nunca desce de
segurança para eficiência nem se cala com a água ainda a correr.

Sem leitura do contador (a injetada foi removida), conta como água parada: o contador só existe
simulado. Com a água parada e sem estado (depois de um reinício), devolve na mesma a Resolucao,
para o ciclo fechar o aviso que reconstruiu.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from backend import habitual
from backend.formatos import Contexto, Desvio, Leitura, Resolucao
from backend.regras import casa_vazia, com_a_casa_vazia

from ._comum import com_fuso, decimal, hora, numero, ultima

DISPOSITIVO = "agua"
TIPO = "caudal"  # litros por minuto


def limite_lmin() -> float:
    return numero("AGUA_LIMITE_LMIN", 0.1)


def minutos_a_correr() -> timedelta:
    return timedelta(minutes=numero("AGUA_MINUTOS", 60))


def fuga_lmin() -> float:
    return numero("FUGA_LMIN", 2)


def cano_lmin() -> float:
    return numero("CANO_LMIN", 12)


def minutos_cano() -> timedelta:
    return timedelta(minutes=numero("CANO_MINUTOS", 5))


@dataclass(frozen=True)
class Estado:
    desde: datetime  # quando a água começou a correr
    lida_em: datetime  # a última leitura
    caudal: float  # o caudal da última leitura, L/min
    litros: float = 0.0  # os litros que já correram
    alto_desde: datetime | None = None  # desde quando corre muita água
    fio: bool | None = None  # decidido quando passa AGUA_MINUTOS: fio de água ou torneira
    avisado: Desvio | None = None  # o desvio mais grave até agora: fica até a água parar


_estado: Estado | None = None


def reiniciar() -> None:
    global _estado
    _estado = None


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio | Resolucao]:
    global _estado
    agora = com_fuso(agora)
    lido = ultima(leituras, DISPOSITIVO, TIPO)
    numero_lido = isinstance(lido, (int, float)) and not isinstance(lido, bool)
    if not numero_lido or float(lido) <= limite_lmin():
        if _estado is None:
            if not numero_lido:
                return []
            return [Resolucao("US15", f"a água já não estava a correr às {hora(agora)}", agora)]
        litros = _somar(_estado, agora).litros
        _estado = None
        if not numero_lido:
            return [Resolucao("US15", f"o contador da água deixou de dar leituras às {hora(agora)}", agora)]
        return [Resolucao("US15", f"a água parou às {hora(agora)} (correram cerca de {_litros(litros)})", agora)]
    _estado = _decidir_fio(_avancar(_estado, float(lido), agora), agora)
    desvio = _mais_grave(_estado.avisado, _desvio(_estado, contexto, agora))
    _estado = replace(_estado, avisado=desvio)
    return [desvio] if desvio else []


def _mais_grave(antes: Desvio | None, agora: Desvio | None) -> Desvio | None:
    """O aviso não desce de segurança nem desaparece enquanto a água corre."""
    if agora is None:
        return antes
    if antes is not None and antes.classe == "seguranca" and agora.classe != "seguranca":
        return antes
    return agora


def _avancar(estado: Estado | None, caudal: float, agora: datetime) -> Estado:
    """O estado depois de mais uma leitura com a água a correr."""
    if estado is None:
        estado = Estado(desde=agora, lida_em=agora, caudal=caudal)
    estado = replace(_somar(estado, agora), lida_em=agora, caudal=caudal)
    if caudal >= cano_lmin():
        estado = replace(estado, alto_desde=estado.alto_desde or agora)
    elif caudal < cano_lmin() / 2:  # uma descida curta (ex.: 11,9) não recomeça a contagem
        estado = replace(estado, alto_desde=None)
    return estado


def _decidir_fio(estado: Estado, agora: datetime) -> Estado:
    """Ao passar AGUA_MINUTOS, decide uma vez se é um fio de água (o resumo não muda depois)."""
    if estado.fio is not None or agora - estado.desde < minutos_a_correr():
        return estado
    return replace(estado, fio=_caudal_medio(_somar(estado, agora), agora) < fuga_lmin())


def _somar(estado: Estado, agora: datetime) -> Estado:
    """Junta os litros desde a última leitura, ao caudal dessa leitura."""
    minutos = max((agora - estado.lida_em).total_seconds() / 60, 0.0)
    return replace(estado, litros=estado.litros + estado.caudal * minutos)


def _caudal_medio(estado: Estado, agora: datetime) -> float:
    minutos = (agora - estado.desde).total_seconds() / 60
    return estado.litros / minutos if minutos > 0 else estado.caudal


def _desvio(estado: Estado, contexto: Contexto, agora: datetime) -> Desvio | None:
    if casa_vazia(contexto, agora):
        return Desvio(
            us="US15",
            classe="seguranca",
            resumo=f"Está a correr água desde as {hora(estado.desde)}, {com_a_casa_vazia(contexto, agora)}.",
            habitual="Com a casa vazia, a água não devia correr.",
            imediato=True,
        )
    if estado.alto_desde is not None and agora - estado.alto_desde >= minutos_cano():
        return Desvio(
            us="US15",
            classe="seguranca",
            resumo=(
                f"Está a correr muita água sem parar desde as {hora(estado.alto_desde)}"
                f" (mais de {decimal(cano_lmin())} litros por minuto). Pode ser um cano rebentado."
            ),
            habitual=f"Mesmo no banho, a água não corre assim mais de {habitual.duracao(minutos_cano())} de seguida.",
            imediato=True,
        )
    if estado.fio is None:
        return None
    duracao = habitual.duracao(minutos_a_correr())
    if estado.fio:
        resumo = (
            f"Corre um fio de água sem parar desde as {hora(estado.desde)}, há mais de {duracao}."
            " Pode ser um autoclismo ou uma torneira a pingar."
        )
    else:
        resumo = (
            f"A água está a correr sem parar desde as {hora(estado.desde)}, há mais de {duracao}."
            " Uma torneira pode ter ficado aberta."
        )
    return Desvio(
        us="US15",
        classe="eficiencia",
        resumo=resumo,
        habitual=f"Num dia normal, a água não corre mais de {duracao} de seguida.",
    )


def _litros(litros: float) -> str:
    redondo = round(litros)
    return "1 litro" if redondo == 1 else f"{redondo} litros"
