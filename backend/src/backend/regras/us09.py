"""US09: a porta não abriu até à hora habitual (Bem-estar e rotina).

A hora limite vem do histórico: a primeira abertura do dia mais tardia desse tipo
de dia, mais 30 min (backend.habitual.limite_porta_nao_abriu).
"A porta abriu hoje" é qualquer leitura aberta (alarm) desde a meia-noite.

- Casa vazia (férias ditas à casa): não avisa; é normal a porta não abrir. Se a anomalia
  já estava ativa, resolve-se com esse motivo ("a casa ficou vazia…"), não "sozinha".
- "Vou ficar em casa" é a IA que o vê, no contexto: a regra produz o desvio na mesma.
- Se o primeiro polling do dia já é depois da hora limite (o ciclo arrancou tarde),
  a casa não sabe se a porta abriu de manhã e não avisa nesse dia.
- O desvio dura até a porta abrir, mesmo depois da meia-noite; quando ela abre, o
  ciclo resolve a anomalia com "a porta abriu às HH:MM" (e avisos.publicar informa o
  contacto externo).

O resumo não muda enquanto o desvio dura, para o ciclo não voltar a publicar a cada polling.
"""

from __future__ import annotations

from datetime import date, datetime

from backend import habitual
from backend.formatos import Contexto, Desvio, Leitura, Resolucao
from backend.regras import casa_vazia, ferias_agora

from ._comum import hora

_dia: date | None = None  # o dia que se está a vigiar
_abriu = False  # a porta já abriu nesse dia
_visto_antes_do_limite = False  # o ciclo viu esse dia antes da hora limite
_pendente: Desvio | None = None  # o desvio em curso, até a porta abrir


def reiniciar() -> None:
    global _dia, _abriu, _visto_antes_do_limite, _pendente
    _dia, _abriu, _visto_antes_do_limite, _pendente = None, False, False, None


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio | Resolucao]:
    global _dia, _abriu, _visto_antes_do_limite, _pendente
    h = habitual.padrao()
    limite = h.limite_porta_nao_abriu(agora)

    if agora.date() != _dia:
        _dia, _abriu = agora.date(), False
        _visto_antes_do_limite = limite is not None and agora.time() < limite

    estado = next(
        (l.valor for l in leituras if l.dispositivo == "porta" and l.tipo == "sensorState"), None
    )
    if estado == "alarm":
        _abriu = True
        if _pendente is not None:
            _pendente = None
            return [Resolucao("US09", f"a porta abriu às {hora(agora)}", agora)]

    if casa_vazia(contexto, agora):
        if _pendente is not None:  # já não se espera que a porta abra: não é "sozinha"
            _pendente = None
            periodo = ferias_agora(contexto, agora)
            motivo = f" ({periodo.motivo})" if periodo and periodo.motivo else ""
            return [Resolucao("US09", f"a casa ficou vazia{motivo}: já não se espera que a porta abra", agora)]
        return []
    if _pendente is not None:
        return [_pendente]
    if limite is None or _abriu or not _visto_antes_do_limite or agora.time() < limite:
        return []

    _pendente = Desvio(
        us="US09",
        classe="bem_estar",
        resumo=f"A porta ainda não tinha aberto hoje às {limite:%H:%M}.",
        habitual=h.texto_primeira_abertura(agora),
    )
    return [_pendente]
