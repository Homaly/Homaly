"""US15: água a correr sem parar (fuga, torneira esquecida ou cano rebentado).

Lê o contador de água ("agua", "caudal", em litros por minuto). O kit não o tem: na demo o
caudal entra por `/dev/leituras`. "A correr" é caudal acima de AGUA_LIMITE_LMIN (0,1 L/min).

- Casa vazia (férias ditas à casa): segurança e imediato, logo que a água corre.
- Muita água (CANO_LMIN, 12 L/min, ou mais) durante CANO_MINUTOS (5): segurança e imediato,
  porque pode ser um cano rebentado.
- Água a correr sem parar há AGUA_MINUTOS (60): eficiência. Se o caudal médio for baixo (menos
  de FUGA_LMIN, 2 L/min), é um fio de água, como um autoclismo a pingar; senão, uma torneira
  que ficou aberta.

Com o resto da casa (os sinais de vida de backend.sinais e a saída de casa de backend.saida):

- Saíram de casa com a água a correr (a porta da rua abriu e as câmaras interiores não viram
  ninguém nos SAIDA_MINUTOS seguintes, depois de a água começar a correr): eficiência, logo, sem
  esperar pela hora. Uma torneira pode ter ficado aberta.
- A água corre há AGUA_SINAIS_MINUTOS (30) com um caudal de torneira ou de chuveiro (pelo menos
  FUGA_LMIN em média) e, desde que começou, nenhum sinal de vida, com a pessoa em casa: bem-estar.
  Pode ter acontecido alguma coisa no banho. Só se a casa está a ler algum dispositivo que dá
  sinais de vida (senão, não sabe).
- Um fio de água sem nenhum sinal de vida desde que começou: o aviso diz que ninguém mexeu na casa
  desde então, o que reforça a hipótese de uma fuga.

A gravidade só sobe (eficiência, bem-estar, segurança): um aviso não desce de classe.

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

from backend import dispositivos, habitual, saida, sinais
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


def minutos_sem_sinais() -> timedelta:
    return timedelta(minutes=numero("AGUA_SINAIS_MINUTOS", 30))


@dataclass(frozen=True)
class Estado:
    desde: datetime  # quando a água começou a correr
    lida_em: datetime  # a última leitura
    caudal: float  # o caudal da última leitura, L/min
    litros: float = 0.0  # os litros que já correram
    alto_desde: datetime | None = None  # desde quando corre muita água
    fio: bool | None = None  # decidido quando passa AGUA_MINUTOS: fio de água ou torneira
    avisado: Desvio | None = None  # o desvio mais grave até agora: fica até a água parar
    sinal_em: datetime | None = None  # o último sinal de vida desde que a água começou a correr
    saiu_em: datetime | None = None  # saíram de casa com a água a correr (a hora da porta)
    sem_sinais: bool = False  # decidido com o fio: nenhum sinal de vida desde que começou


def _comandado(dispositivo: str, tipo: str) -> bool:
    return dispositivos.comandado_ha_pouco(dispositivo, tipo)


_estado: Estado | None = None
_detetor = sinais.Detetor(comandado=_comandado)
_vigia = saida.Vigia()


def reiniciar() -> None:
    global _estado, _detetor, _vigia
    _estado = None
    _detetor = sinais.Detetor(comandado=_comandado)
    _vigia = saida.Vigia()


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio | Resolucao]:
    global _estado
    agora = com_fuso(agora)
    houve_sinal = bool(_detetor.ver(leituras))  # todas as voltas, para ter a leitura anterior
    visto = _vigia.ver(leituras, agora)
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
    _estado = _avancar(_estado, float(lido), agora)
    if houve_sinal:
        _estado = replace(_estado, sinal_em=agora)
    if visto.saiu is not None and visto.saiu >= _estado.desde and _estado.saiu_em is None:
        _estado = replace(_estado, saiu_em=visto.saiu)
    comunica = sinais.comunica(leituras)  # sem estes dispositivos, a casa não sabe se alguém mexe
    _estado = _decidir_fio(_estado, agora, comunica)
    desvio = _mais_grave(_estado.avisado, _desvio(_estado, contexto, agora, comunica))
    _estado = replace(_estado, avisado=desvio)
    return [desvio] if desvio else []


GRAVIDADE = {"eficiencia": 1, "bem_estar": 2, "seguranca": 3}


def _mais_grave(antes: Desvio | None, agora: Desvio | None) -> Desvio | None:
    """O aviso não desce de classe nem desaparece enquanto a água corre."""
    if agora is None:
        return antes
    if antes is not None and GRAVIDADE.get(antes.classe, 0) > GRAVIDADE.get(agora.classe, 0):
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


def _decidir_fio(estado: Estado, agora: datetime, comunica: bool) -> Estado:
    """Ao passar AGUA_MINUTOS, decide uma vez se é um fio de água (o resumo não muda depois)."""
    if estado.fio is not None or agora - estado.desde < minutos_a_correr():
        return estado
    fio = _caudal_medio(_somar(estado, agora), agora) < fuga_lmin()
    return replace(estado, fio=fio, sem_sinais=fio and comunica and estado.sinal_em is None)


def _somar(estado: Estado, agora: datetime) -> Estado:
    """Junta os litros desde a última leitura, ao caudal dessa leitura."""
    minutos = max((agora - estado.lida_em).total_seconds() / 60, 0.0)
    return replace(estado, litros=estado.litros + estado.caudal * minutos)


def _caudal_medio(estado: Estado, agora: datetime) -> float:
    minutos = (agora - estado.desde).total_seconds() / 60
    return estado.litros / minutos if minutos > 0 else estado.caudal


def _desvio(estado: Estado, contexto: Contexto, agora: datetime, comunica: bool) -> Desvio | None:
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
    if (
        comunica
        and estado.sinal_em is None
        and estado.saiu_em is None
        and agora - estado.desde >= minutos_sem_sinais()
        and _caudal_medio(_somar(estado, agora), agora) >= fuga_lmin()
    ):
        return Desvio(
            us="US15",
            classe="bem_estar",
            resumo=(
                f"A água está a correr desde as {hora(estado.desde)} e, desde então, não houve nenhum sinal"
                " de vida em casa. Pode ter acontecido alguma coisa a quem está no banho."
            ),
            habitual=f"Um banho não costuma durar mais de {habitual.duracao(minutos_sem_sinais())} sem mais nada a mexer na casa.",
        )
    if estado.saiu_em is not None:
        return Desvio(
            us="US15",
            classe="eficiencia",
            resumo=(
                f"A água está a correr desde as {hora(estado.desde)} e parece que saíram de casa às "
                f"{hora(estado.saiu_em)}: a porta da rua abriu e as câmaras não viram ninguém a seguir."
                " Uma torneira pode ter ficado aberta."
            ),
            habitual="Com a casa sem ninguém, a água não devia correr.",
        )
    if estado.fio is None:
        return None
    duracao = habitual.duracao(minutos_a_correr())
    if estado.fio:
        resumo = (
            f"Corre um fio de água sem parar desde as {hora(estado.desde)}, há mais de {duracao}."
            " Pode ser um autoclismo ou uma torneira a pingar."
        )
        if estado.sem_sinais:
            resumo += " Ninguém mexeu na casa desde então."
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
