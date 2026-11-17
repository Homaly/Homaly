"""US14: o aparelho na tomada está a gastar há muito mais tempo do que é costume.

"A gastar" é instantPower acima de habitual.LIMITE_W. O desvio dura enquanto o
aparelho gasta; quando deixa de gastar, o ciclo resolve a anomalia sozinho.

- Casa vazia (férias ditas à casa): de segurança e imediato, logo que gasta.
- Senão: eficiência energética, a partir de 3x o período mais longo do histórico.

O resumo não muda enquanto o desvio dura (diz desde quando), para o ciclo não
voltar a publicar a cada polling.
"""

from __future__ import annotations

from datetime import datetime

from backend import habitual
from backend.formatos import Contexto, Desvio, Leitura
from backend.regras import casa_vazia, com_a_casa_vazia

_desde: datetime | None = None  # desde quando o aparelho está a gastar


def reiniciar() -> None:
    global _desde
    _desde = None


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio]:
    global _desde
    potencia = next(
        (l.valor for l in leituras if l.dispositivo == "tomada" and l.tipo == "instantPower"), None
    )
    if potencia is not None:  # sem leitura da tomada neste polling: fica como estava
        if float(potencia) > habitual.LIMITE_W:
            _desde = _desde or agora
        else:
            _desde = None
    if _desde is None:
        return []

    h = habitual.padrao()
    nome = contexto.aparelho_tomada or "o aparelho na tomada"
    nome = nome[0].upper() + nome[1:]
    if casa_vazia(contexto, agora):
        return [Desvio(
            us="US14",
            classe="seguranca",
            resumo=f"{nome} está a gastar desde as {_desde:%H:%M}, {com_a_casa_vazia(contexto, agora)}.",
            habitual=h.texto_tomada(),
            imediato=True,
        )]
    if agora - _desde < h.limite_tomada:
        return []
    return [Desvio(
        us="US14",
        classe="eficiencia",
        resumo=f"{nome} está a gastar desde as {_desde:%H:%M}, há mais de {habitual.duracao(h.limite_tomada)} seguidas.",
        habitual=h.texto_tomada(),
    )]
