"""Versões falsas das peças dos colegas, até as reais existirem.

Cada uma só escreve no terminal o que a real faria. Quando a real chegar,
troca-se em backend/ciclo.py (main) ou em avisos.configurar().
"""

from __future__ import annotations

import csv
from datetime import datetime
from itertools import groupby
from typing import Iterator

from backend.contrato import Anomalia
from backend.formatos import Contexto, Desvio, Leitura


def _log(texto: str) -> None:
    print(f"[falso] {texto}")


# dispositivos.ler(): as leituras de um CSV (colunas dispositivo,tipo,valor,em).
def _valor(texto: str) -> str | float | bool:
    if texto.lower() in ("true", "false"):
        return texto.lower() == "true"
    try:
        return float(texto)
    except ValueError:
        return texto


def ler_csv(caminho: str) -> Iterator[tuple[datetime, list[Leitura]]]:
    """Um lote por hora 'em', pela ordem do ficheiro: cada lote faz de um polling."""
    with open(caminho, newline="", encoding="utf-8") as f:
        leituras = [
            Leitura(l["dispositivo"], l["tipo"], _valor(l["valor"]), datetime.fromisoformat(l["em"]))
            for l in csv.DictReader(f)
        ]
    for em, lote in groupby(leituras, key=lambda l: l.em):
        yield em, list(lote)


# dispositivos.ler() (Xuta), para o ciclo ao vivo sem o MCP: a porta fechada e a tomada sem gastar.
def ler() -> list[Leitura]:
    agora = datetime.now()
    return [
        Leitura("porta", "sensorState", "normal", agora),
        Leitura("tomada", "instantPower", 0.0, agora),
    ]


# Contexto (Simão): vazio.
def obter_contexto() -> Contexto:
    return Contexto(ferias=[], rotinas=[], silencios=[], casa_vazia=False)


# ia.avaliar (Simão): avisa sempre, com o resumo da regra.
def avaliar(desvio: Desvio, contexto: Contexto) -> Anomalia:
    return Anomalia(
        classe=desvio.classe,
        titulo=desvio.resumo,
        explicacao=desvio.resumo,
        detetada_em=datetime.now(),
    )


# Histórico (Benny): o desvio que a casa viu e não avisou.
def registar_historico(desvio: Desvio, motivo: str, agora: datetime) -> None:
    _log(f"histórico {agora:%H:%M}: {desvio.us} '{desvio.resumo}', sem aviso: {motivo}")


# Gravação e WebSocket (Benny).
def gravar(anomalia: Anomalia) -> None:
    _log(f"gravar {anomalia.id[:8]} {anomalia.estado} {anomalia.classe}: {anomalia.explicacao}")


def enviar_ws(anomalia: Anomalia) -> None:
    a = anomalia.para_json()
    _log(f"ws anomalia {a['id'][:8]} {a['estado']}" + (f" ({a['resolucao']['texto']})" if "resolucao" in a else ""))


# contacto_externo (Candeias).
class ContactoExterno:
    def agendar(self, anomalia: Anomalia) -> None:
        _log(f"contacto_externo.agendar {anomalia.id[:8]} ({anomalia.classe})")

    def cancelar(self, anomalia_id: str) -> None:
        _log(f"contacto_externo.cancelar {anomalia_id[:8]}")

    def resolvida(self, anomalia: Anomalia) -> None:
        _log(f"contacto_externo.resolvida {anomalia.id[:8]}")


def avisos():
    from backend.avisos import Avisos

    return Avisos(gravar=gravar, enviar_ws=enviar_ws, contacto=ContactoExterno())
