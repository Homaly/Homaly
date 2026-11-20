"""Leituras injetadas, para a demo: sobrepõem uma leitura real até serem removidas.

Servem para mostrar ao vivo o que não se consegue provocar na sala, como a temperatura abaixo de
16 °C (US10) ou a descer com a porta aberta (US12). O resto da casa continua real.

Os pedidos `/dev/leituras` só existem com `HOMALY_DEV=1` (ver `main.py`), porque não pedem login.

Uma leitura injetada com `id` muda só esse dispositivo, ou cria-o se o kit não o tem (ex.: uma
janela ou um segundo sensor de temperatura noutra divisão, com o `id` que está no inventário,
`dados/dispositivos.csv`). Sem `id`, muda todos os dispositivos desse tipo (o kit tem um de cada).

Também guarda os dispositivos que o kit não tem e a casa comanda na demo: a válvula da água
(US15). Fechá-la põe o caudal a zero até alguém injetar outro (ou limpar as leituras).
"""

import threading
from dataclasses import replace
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from backend.formatos import Leitura

Valor = str | float | bool

_trinco = threading.Lock()
_sobrepostas: dict[tuple[str, str, str], Valor] = {}  # (dispositivo, tipo, id) -> valor; id "" = todos


def sobrepor(dispositivo: str, tipo: str, valor: Valor, id: str = "") -> None:
    global _sobrepostas
    novas = {(dispositivo, tipo, id): valor}
    a_correr = (dispositivo, tipo) == ("agua", "caudal") and isinstance(valor, (int, float)) and valor > 0
    with _trinco:
        if a_correr and _sobrepostas.get(("agua", "valvula", "")) == "fechada":
            novas[("agua", "valvula", "")] = "aberta"  # a água voltou a correr: a válvula foi aberta
        _sobrepostas = {**_sobrepostas, **novas}


def remover(dispositivo: str, tipo: str, id: str = "") -> bool:
    """Remove uma leitura injetada; False se não existia."""
    global _sobrepostas
    chave = (dispositivo, tipo, id)
    with _trinco:
        if chave not in _sobrepostas:
            return False
        _sobrepostas = {k: v for k, v in _sobrepostas.items() if k != chave}
        return True


# (dispositivo, tipo) que a casa comanda sem o MCP -> os valores aceites
SIMULADOS: dict[tuple[str, str], set[str]] = {("agua", "valvula"): {"aberta", "fechada"}}


def simulado(dispositivo: str, tipo: str) -> bool:
    return (dispositivo, tipo) in SIMULADOS


def executar(dispositivo: str, tipo: str, valor: str) -> bool:
    """Comanda um dispositivo simulado. Fechar a água corta o caudal."""
    if valor not in SIMULADOS.get((dispositivo, tipo), set()):
        raise ValueError(f"Não se pode pôr '{dispositivo}' {tipo}={valor}")
    sobrepor(dispositivo, tipo, valor)
    if (dispositivo, tipo, valor) == ("agua", "valvula", "fechada"):
        sobrepor("agua", "caudal", 0.0)
    return True


def limpar() -> None:
    global _sobrepostas
    with _trinco:
        _sobrepostas = {}


def listar() -> dict[tuple[str, str, str], Valor]:
    with _trinco:
        return dict(_sobrepostas)


def aplicar(leituras: list[Leitura], em: datetime) -> list[Leitura]:
    """As leituras com as injetadas por cima; as que não existiam são acrescentadas.

    A injetada com o id do dispositivo ganha à injetada sem id (que vale para todos desse tipo).
    """
    sobrepostas = listar()
    if not sobrepostas:
        return leituras

    def por_cima(l: Leitura) -> Leitura:
        for chave in ((l.dispositivo, l.tipo, l.id), (l.dispositivo, l.tipo, "")):
            if chave in sobrepostas:
                return replace(l, valor=sobrepostas[chave])
        return l

    resultado = [por_cima(l) for l in leituras]
    com_id = {(l.dispositivo, l.tipo, l.id) for l in leituras}
    sem_id = {(l.dispositivo, l.tipo) for l in leituras}
    novas = [
        Leitura(d, t, v, em, i)
        for (d, t, i), v in sobrepostas.items()
        if (i and (d, t, i) not in com_id) or (not i and (d, t) not in sem_id)
    ]
    return resultado + novas


class LeituraInjetada(BaseModel):
    dispositivo: str = Field(min_length=1, max_length=40)  # "temperatura", "porta", ...
    tipo: str = Field(min_length=1, max_length=60)  # "temperatureValue", "sensorState", ...
    valor: bool | float | str  # bool primeiro, para "true" não virar 1.0
    id: str = Field(default="", max_length=60)  # um só dispositivo (ver dados/dispositivos.csv); "" = todos


router = APIRouter(prefix="/dev/leituras", tags=["dev"])


@router.get("")
def pedir_lista() -> list[LeituraInjetada]:
    return [LeituraInjetada(dispositivo=d, tipo=t, valor=v, id=i) for (d, t, i), v in listar().items()]


@router.post("")
def pedir_sobrepor(leitura: LeituraInjetada) -> LeituraInjetada:
    sobrepor(leitura.dispositivo, leitura.tipo, leitura.valor, leitura.id)
    return leitura


@router.delete("", status_code=204)
def pedir_limpar() -> Response:
    limpar()
    return Response(status_code=204)


@router.delete("/{dispositivo}/{tipo}", status_code=204)
def pedir_remover(dispositivo: str, tipo: str, id: str = Query(default="", max_length=60)) -> Response:
    if not remover(dispositivo, tipo, id):
        raise HTTPException(404, "Essa leitura não está injetada")
    return Response(status_code=204)
