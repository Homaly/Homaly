"""Leituras injetadas, para a demo: sobrepõem uma leitura real até serem removidas.

Servem para mostrar ao vivo o que não se consegue provocar na sala, como a temperatura abaixo de
16 °C (US10) ou a descer com a porta aberta (US12). O resto da casa continua real.

Os pedidos `/dev/leituras` só existem com `HOMALY_DEV=1` (ver `main.py`), porque não pedem login.
"""

import threading
from dataclasses import replace
from datetime import datetime

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from backend.formatos import Leitura

Valor = str | float | bool

_trinco = threading.Lock()
_sobrepostas: dict[tuple[str, str], Valor] = {}


def sobrepor(dispositivo: str, tipo: str, valor: Valor) -> None:
    global _sobrepostas
    with _trinco:
        _sobrepostas = {**_sobrepostas, (dispositivo, tipo): valor}


def remover(dispositivo: str, tipo: str) -> bool:
    """Remove uma leitura injetada; False se não existia."""
    global _sobrepostas
    with _trinco:
        if (dispositivo, tipo) not in _sobrepostas:
            return False
        _sobrepostas = {k: v for k, v in _sobrepostas.items() if k != (dispositivo, tipo)}
        return True


def limpar() -> None:
    global _sobrepostas
    with _trinco:
        _sobrepostas = {}


def listar() -> dict[tuple[str, str], Valor]:
    with _trinco:
        return dict(_sobrepostas)


def aplicar(leituras: list[Leitura], em: datetime) -> list[Leitura]:
    """As leituras com as injetadas por cima; as que não existiam são acrescentadas."""
    sobrepostas = listar()
    if not sobrepostas:
        return leituras
    resultado = [
        replace(l, valor=sobrepostas[(l.dispositivo, l.tipo)]) if (l.dispositivo, l.tipo) in sobrepostas else l
        for l in leituras
    ]
    existentes = {(l.dispositivo, l.tipo) for l in leituras}
    novas = [Leitura(d, t, v, em) for (d, t), v in sobrepostas.items() if (d, t) not in existentes]
    return resultado + novas


class LeituraInjetada(BaseModel):
    dispositivo: str = Field(min_length=1, max_length=40)  # "temperatura", "porta", ...
    tipo: str = Field(min_length=1, max_length=60)  # "temperatureValue", "sensorState", ...
    valor: bool | float | str  # bool primeiro, para "true" não virar 1.0


router = APIRouter(prefix="/dev/leituras", tags=["dev"])


@router.get("")
def pedir_lista() -> list[LeituraInjetada]:
    return [LeituraInjetada(dispositivo=d, tipo=t, valor=v) for (d, t), v in listar().items()]


@router.post("")
def pedir_sobrepor(leitura: LeituraInjetada) -> LeituraInjetada:
    sobrepor(leitura.dispositivo, leitura.tipo, leitura.valor)
    return leitura


@router.delete("", status_code=204)
def pedir_limpar() -> Response:
    limpar()
    return Response(status_code=204)


@router.delete("/{dispositivo}/{tipo}", status_code=204)
def pedir_remover(dispositivo: str, tipo: str) -> Response:
    if not remover(dispositivo, tipo):
        raise HTTPException(404, "Essa leitura não está injetada")
    return Response(status_code=204)
