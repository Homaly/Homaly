"""US07: a porta abriu a uma hora anormal, ou com a casa vazia (Segurança).

Só conta a passagem da porta de fechada (normal) a aberta (alarm), por isso cada
abertura é uma ocorrência. A anomalia só se resolve com a resposta do responsável
(SO_COM_RESPOSTA, no ciclo).

- Casa vazia (férias ditas à casa): qualquer abertura é imediata, mesmo à hora de uma
  rotina; a IA não decide.
- Senão: avisa quando a abertura fica fora da janela habitual desse tipo de dia
  (backend.habitual), exceto se uma rotina a explicar. "Avisei que ia chegar tarde"
  é a IA que o vê, no contexto.
"""

from __future__ import annotations

from datetime import datetime

from backend import habitual
from backend.formatos import Contexto, Desvio, Leitura
from backend.regras import casa_vazia, com_a_casa_vazia, explicado_por_rotina

_anterior: str | None = None  # o último estado visto da porta


def reiniciar() -> None:
    global _anterior
    _anterior = None


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio]:
    global _anterior
    estado = next(
        (l.valor for l in leituras if l.dispositivo == "porta" and l.tipo == "sensorState"), None
    )
    if estado is None:
        return []
    abriu = estado == "alarm" and _anterior == "normal"
    _anterior = estado
    if not abriu:
        return []

    h = habitual.padrao()
    if casa_vazia(contexto, agora):
        return [Desvio(
            us="US07",
            classe="seguranca",
            resumo=f"A porta abriu às {agora:%H:%M} {com_a_casa_vazia(contexto, agora)}.",
            habitual=h.texto_porta(agora),
            imediato=True,
        )]
    if h.porta_normal(agora) or explicado_por_rotina(contexto, agora):
        return []
    dia = "num dia útil" if habitual.tipo_de_dia(agora) == "util" else "ao fim de semana"
    return [Desvio(
        us="US07",
        classe="seguranca",
        resumo=f"A porta abriu às {agora:%H:%M}, {dia}, a uma hora em que nunca abre.",
        habitual=h.texto_porta(agora),
    )]
