"""Um ficheiro por história, cada um com verificar(leituras, contexto, agora) -> list[Desvio | Resolucao]
(a Resolucao diz como o problema acabou).

O ciclo encontra os ficheiros sozinho: para acrescentar uma regra basta criar o ficheiro.
Aqui ficam as ajudas da US07, US09 e US14; as outras estão em _comum.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from backend.formatos import Contexto, Periodo

from ._comum import com_fuso

MARGEM_ROTINA = timedelta(hours=1)


def ferias_agora(contexto: Contexto, agora: datetime) -> Periodo | None:
    agora = com_fuso(agora)
    return next((p for p in contexto.ferias if com_fuso(p.inicio) <= agora <= com_fuso(p.fim)), None)


def casa_vazia(contexto: Contexto, agora: datetime) -> bool:
    """Férias ditas à casa. O kit não tem alarme de intrusão (o alarme é só de fumo)."""
    return contexto.casa_vazia or ferias_agora(contexto, agora) is not None


def com_a_casa_vazia(contexto: Contexto, agora: datetime) -> str:
    periodo = ferias_agora(contexto, agora)
    return f"com a casa vazia ({periodo.motivo})" if periodo and periodo.motivo else "com a casa vazia"


def explicado_por_rotina(contexto: Contexto, agora: datetime) -> bool:
    """Uma rotina desse dia da semana, a até uma hora da sua hora (ou o dia todo, sem hora)."""
    for r in contexto.rotinas:
        if agora.weekday() not in r.dias:
            continue
        if r.hora is None:
            return True
        if abs(agora - datetime.combine(agora.date(), r.hora)) <= MARGEM_ROTINA:
            return True
    return False
