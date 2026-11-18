"""O que a casa sabe agora, para responder a perguntas na conversa (US01).

Junta a última leitura do ciclo (`dispositivos.ultimas()`, sem ir ao MCP), os avisos ativos, o que
aconteceu hoje e o que a pessoa disse à casa. Se alguma parte falhar, fica de fora: a conversa
nunca pára por causa disto.
"""

import logging
from datetime import datetime

from backend import anomalias, dispositivos, eventos
from backend.contexto import repositorio
from backend.conversa.interpretar import DIAS_DA_SEMANA
from backend.formatos import Leitura

registo = logging.getLogger(__name__)

MAX_EVENTOS = 15


def estado_da_casa(agora: datetime) -> dict:
    estado: dict = {}
    partes = {
        "sensores": lambda: _sensores(dispositivos.ultimas(), dispositivos.em_silencio(), agora),
        "avisos_ativos": lambda: _avisos(agora),
        "aconteceu_hoje": lambda: _hoje(agora),
        "o_que_me_disseram": lambda: _contexto(agora),
    }
    for nome, obter in partes.items():
        try:
            estado[nome] = obter()
        except Exception:  # noqa: BLE001 — sem esta parte, a casa responde com o resto
            registo.warning("Estado da casa sem %s", nome, exc_info=True)
    return estado


def _hora(quando: datetime, agora: datetime) -> str:
    local = quando.astimezone(agora.tzinfo) if quando.tzinfo else quando
    return f"{local:%H:%M}" if local.date() == agora.date() else f"{local:%d/%m %H:%M}"


def _sensores(leituras: list[Leitura], calados: dict[str, datetime], agora: datetime) -> dict | str:
    if not leituras and not calados:
        return "A casa ainda não leu os sensores."
    valores = {(l.dispositivo, l.tipo): l.valor for l in leituras}
    sensores: dict[str, str] = {}
    if (porta := valores.get(("porta", "sensorState"))) is not None:
        sensores["porta da rua"] = "aberta" if porta == "alarm" else "fechada"
    if (graus := valores.get(("temperatura", "temperatureValue"))) is not None:
        sensores["temperatura da sala"] = f"{graus:g} °C"
    if (luz := valores.get(("lampada", "power"))) is not None:
        sensores["luz da sala"] = "acesa" if luz == "on" else "apagada"
    if (tomada := valores.get(("tomada", "power"))) is not None:
        watts = valores.get(("tomada", "instantPower"))
        gasto = f", a gastar {watts:g} W" if tomada == "on" and isinstance(watts, (int, float)) else ""
        sensores["tomada"] = ("ligada" if tomada == "on" else "desligada") + gasto
    for nome, desde in calados.items():
        sensores.setdefault(nome, f"sem comunicar desde {_hora(desde, agora)}")
    return sensores


def _avisos(agora: datetime) -> list[str]:
    return [
        f"{a.titulo} (desde {_hora(a.detetada_em, agora)}): {a.explicacao}"
        for a in anomalias.listar("ativa")
    ]


def _hoje(agora: datetime) -> list[str]:
    def local(e):
        return e.em.astimezone(agora.tzinfo) if e.em.tzinfo else e.em

    de_hoje = [e for e in eventos.listar(200) if local(e).date() == agora.date()]
    return [f"{local(e):%H:%M} {e.dispositivo}: {e.descricao}" for e in reversed(de_hoje[:MAX_EVENTOS])]


def _contexto(agora: datetime) -> dict:
    contexto = repositorio.carregar_contexto(agora)
    return {
        "ferias": [f"de {p.inicio:%d/%m} a {p.fim:%d/%m} ({p.motivo or 'sem motivo'})" for p in contexto.ferias],
        "rotinas": [
            f"{r.descricao}: {', '.join(DIAS_DA_SEMANA[d] for d in r.dias)}"
            + (f", às {r.hora:%H:%M}" if r.hora else "")
            for r in contexto.rotinas
        ],
        "aparelho_na_tomada": contexto.aparelho_tomada,
        "casa_vazia": contexto.casa_vazia,
    }
