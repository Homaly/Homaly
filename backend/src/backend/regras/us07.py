"""US07: a porta abriu a uma hora anormal, ou com a casa vazia (Segurança).

Só conta a passagem da porta da rua de fechada (normal) a aberta (alarm), por isso cada
abertura é uma ocorrência. As janelas (backend.inventario) não contam. A anomalia só se resolve com a resposta do responsável
(SO_COM_RESPOSTA, no ciclo).

- Casa vazia (férias ditas à casa): qualquer abertura é imediata, mesmo à hora de uma
  rotina; a IA não decide.
- Senão: avisa quando a abertura fica fora da janela habitual desse tipo de dia
  (backend.habitual), exceto se uma rotina a explicar. "Avisei que ia chegar tarde"
  é a IA que o vê, no contexto.
"""

from __future__ import annotations

from datetime import datetime

from backend import habitual, inventario
from backend.formatos import Contexto, Desvio, Leitura
from backend.regras import casa_vazia, com_a_casa_vazia, explicado_por_rotina

_anteriores: dict[str, object] = {}  # o último estado visto de cada porta da rua


def reiniciar() -> None:
    _anteriores.clear()


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio]:
    abriu = False
    for l in inventario.com_papel(leituras, "porta", "sensorState", inventario.PORTA_DA_RUA):
        chave = inventario.chave(l)
        abriu = abriu or (l.valor == "alarm" and _anteriores.get(chave) == "normal")
        _anteriores[chave] = l.valor
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
