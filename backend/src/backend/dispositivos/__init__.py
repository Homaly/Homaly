"""Os dispositivos da casa, pelo servidor MCP da Altice.

- `ler()`: o estado da casa num só pedido (`get_home_devices`), como lista de `Leitura`, já com as
  leituras injetadas da demo por cima. Grava um evento quando a porta, a lâmpada ou a tomada mudam.
- `executar(dispositivo, tipo, valor)`: liga/desliga a lâmpada ou a tomada, ou muda o brilho da
  lâmpada, e confirma lendo o dispositivo de novo.
- `alarme()`: o estado do alarme (`DISARMED`, `STAY` ou `AWAY`), para a casa vazia (US07, US14).

Uma falha a falar com o MCP levanta `ErroDispositivos`: o ciclo deve saltar essa volta.
"""

import logging
import os
import threading
import time
from datetime import datetime
from typing import Protocol

from backend import contrato, eventos
from backend.formatos import Leitura

from . import mapa, mudancas, simulacao
from .mcp import ClienteMCP, Config, ErroDispositivos

__all__ = ["ErroDispositivos", "alarme", "configurar", "executar", "intervalo_s", "ler"]

registo = logging.getLogger(__name__)

# A confirmação de uma ação lê o dispositivo até TENTATIVAS vezes, com PAUSA_S entre leituras.
TENTATIVAS = 3
PAUSA_S = 1.0

COMANDADOS = {"lampada", "tomada"}


class Cliente(Protocol):
    def chamar(self, ferramenta: str, argumentos: dict | None = None) -> dict: ...


# O ciclo lê numa thread e os pedidos da API executam noutras: o trinco guarda o cliente, os ids e
# a leitura anterior (para haver uma só sessão MCP e nenhum evento em duplicado).
_trinco = threading.RLock()
_cliente: Cliente | None = None
_ids: dict[str, str] = {}
_observador = mudancas.Observador()


def intervalo_s() -> float:
    """De quanto em quanto tempo ler a casa (POLLING_SEGUNDOS, 10 por omissão)."""
    texto = os.environ.get("POLLING_SEGUNDOS", "").strip()
    try:
        valor = float(texto) if texto else 10.0
    except ValueError:
        raise ValueError(f"POLLING_SEGUNDOS tem de ser um número, não '{texto}'") from None
    if valor <= 0:
        raise ValueError("POLLING_SEGUNDOS tem de ser maior que zero")
    return valor


def configurar(cliente: Cliente | None) -> None:
    """Escolhe o cliente (o real, ou um falso nos testes); None volta ao real, criado do ambiente."""
    global _cliente, _ids, _observador
    with _trinco:
        _cliente = cliente
        _ids = {}
        _observador = mudancas.Observador()


def _obter_cliente() -> Cliente:
    global _cliente
    with _trinco:
        if _cliente is None:
            _cliente = ClienteMCP(Config.do_ambiente())
        return _cliente


def ler(agora: datetime | None = None) -> list[Leitura]:
    """O estado da casa agora, uma `Leitura` por capability."""
    global _ids
    em = agora or contrato.agora()
    with _trinco:
        dados = _obter_cliente().chamar("get_home_devices")
        _ids = mapa.ids(dados)
        leituras = simulacao.aplicar(mapa.para_leituras(dados, em), em)
        _registar_eventos(leituras)
    return leituras


def _registar_eventos(leituras: list[Leitura]) -> None:
    for evento in _observador.ver(leituras):
        try:
            eventos.registar(evento)
        except Exception:  # noqa: BLE001 — fica no log; o histórico não deve parar a leitura da casa
            registo.exception("Não foi possível registar o evento %s", evento)


def executar(dispositivo: str, tipo: str, valor: str | int) -> bool:
    """Muda o dispositivo e devolve True se, ao lê-lo de novo, tem o valor pedido."""
    _validar(dispositivo, tipo, valor)
    cliente = _obter_cliente()
    id_dispositivo = _id(dispositivo)
    cliente.chamar("update_device_capabilities", {"deviceId": id_dispositivo, "body": {"type": tipo, "value": valor}})
    for tentativa in range(TENTATIVAS):
        if tentativa:
            time.sleep(PAUSA_S)
        detalhes = cliente.chamar("get_device_details", {"deviceId": id_dispositivo})
        if mapa.valor(detalhes, tipo) == valor:
            return True
    registo.warning("%s não confirmou %s=%s", dispositivo, tipo, valor)
    return False


def _validar(dispositivo: str, tipo: str, valor: object) -> None:
    if dispositivo not in COMANDADOS:
        raise ValueError(f"A casa não comanda '{dispositivo}'; só {sorted(COMANDADOS)}")
    if tipo == "power":
        if valor not in ("on", "off"):
            raise ValueError("power só aceita 'on' ou 'off'")
    elif tipo == "brightness" and dispositivo == "lampada":
        if isinstance(valor, bool) or not isinstance(valor, int) or not 1 <= valor <= 100:
            raise ValueError("brightness é um inteiro de 1 a 100")
    else:
        raise ValueError(f"Não se pode mudar '{tipo}' em '{dispositivo}'")


def _id(dispositivo: str) -> str:
    global _ids
    with _trinco:
        if dispositivo not in _ids:
            _ids = mapa.ids(_obter_cliente().chamar("get_home_devices"))
        if dispositivo not in _ids:
            raise ErroDispositivos(f"O MCP não tem nenhum dispositivo '{dispositivo}'")
        return _ids[dispositivo]


def alarme() -> str:
    """`DISARMED`, `STAY` ou `AWAY`."""
    return str(_obter_cliente().chamar("get_home_security_status").get("status", ""))
