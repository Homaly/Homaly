"""Os dispositivos da casa, pelo servidor MCP da Altice.

- `ler()`: o estado da casa num só pedido (`get_home_devices`), como lista de `Leitura`, já com as
  leituras injetadas da demo por cima. Grava um evento quando a porta, a lâmpada ou a tomada mudam.
  Um dispositivo que não comunica há mais de SENSOR_SILENCIO_MINUTOS (60) não dá leituras: o MCP
  repetiria o último valor (ex.: a porta "aberta" desde ontem com o kit desligado). As regras tratam
  "sem leitura" como "nada mudou". `em_silencio()` diz quais estão calados e desde quando.
- `executar(dispositivo, tipo, valor)`: liga/desliga a lâmpada ou a tomada, ou muda o brilho da
  lâmpada, e confirma lendo o dispositivo de novo. Lembra o comando durante COMANDO_SEGUNDOS:
  `comandado_ha_pouco(dispositivo, tipo)` deixa as regras ignorar o que a própria casa mudou.
- `alarme()`: o estado do alarme (`DISARMED`, `STAY` ou `AWAY`), para a casa vazia (US07, US14).

Uma falha a falar com o MCP levanta `ErroDispositivos`: o ciclo deve saltar essa volta.
"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Protocol

from backend import contrato, eventos
from backend.formatos import Leitura

from . import mapa, mudancas, simulacao
from .mcp import ClienteMCP, Config, ErroDispositivos

__all__ = ["ErroDispositivos", "alarme", "comandado_ha_pouco", "configurar", "em_silencio", "executar", "intervalo_s", "ler", "ultimas"]

registo = logging.getLogger(__name__)

# A confirmação de uma ação lê o dispositivo até TENTATIVAS vezes, com PAUSA_S entre leituras.
TENTATIVAS = 3
PAUSA_S = 1.0

COMANDADOS = {"lampada", "tomada"}

# Quanto tempo (real, não o do relógio acelerado) um comando da casa conta como "feito pela casa".
COMANDO_SEGUNDOS = 60.0


class Cliente(Protocol):
    def chamar(self, ferramenta: str, argumentos: dict | None = None) -> dict: ...


# O ciclo lê numa thread e os pedidos da API executam noutras: o trinco guarda o cliente, os ids e
# a leitura anterior (para haver uma só sessão MCP e nenhum evento em duplicado).
_trinco = threading.RLock()
_cliente: Cliente | None = None
_ids: dict[str, str] = {}
_observador = mudancas.Observador()
_calados: dict[str, datetime] = {}
_comandos: dict[tuple[str, str], float] = {}  # (dispositivo, tipo) -> time.monotonic() do comando
_ultimas: list[Leitura] = []  # a última leitura do ciclo, para a conversa (US01)


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


def silencio_minutos() -> float:
    """Ao fim de quantos minutos sem comunicar um dispositivo deixa de contar (0: nunca)."""
    texto = os.environ.get("SENSOR_SILENCIO_MINUTOS", "").strip()
    try:
        return float(texto) if texto else 60.0
    except ValueError:
        raise ValueError(f"SENSOR_SILENCIO_MINUTOS tem de ser um número, não '{texto}'") from None


def _agora_real() -> datetime:
    """A hora real; o `lastCommunicationTime` do MCP é real, mesmo com o relógio do ciclo acelerado."""
    return contrato.agora()


def ultimas() -> list[Leitura]:
    """A última leitura feita por `ler()`, sem ir ao MCP (vazia se o ciclo ainda não leu)."""
    with _trinco:
        return list(_ultimas)


def em_silencio() -> dict[str, datetime]:
    """Os dispositivos que estavam calados na última leitura, e desde quando."""
    with _trinco:
        return dict(_calados)


def configurar(cliente: Cliente | None) -> None:
    """Escolhe o cliente (o real, ou um falso nos testes); None volta ao real, criado do ambiente."""
    global _cliente, _ids, _observador, _calados, _ultimas
    with _trinco:
        _cliente = cliente
        _ultimas = []
        _ids = {}
        _observador = mudancas.Observador()
        _calados = {}
        _comandos.clear()


def _obter_cliente() -> Cliente:
    global _cliente
    with _trinco:
        if _cliente is None:
            _cliente = ClienteMCP(Config.do_ambiente())
        return _cliente


def ler(agora: datetime | None = None) -> list[Leitura]:
    """O estado da casa agora, uma `Leitura` por capability."""
    global _ids, _ultimas
    em = agora or contrato.agora()
    minutos = silencio_minutos()
    limite = _agora_real() - timedelta(minutes=minutos) if minutos > 0 else None
    with _trinco:
        dados = _obter_cliente().chamar("get_home_devices")
        _ids = mapa.ids(dados)
        _atualizar_calados(mapa.em_silencio(dados, limite) if limite else {})
        leituras = simulacao.aplicar(mapa.para_leituras(dados, em, limite), em)
        _registar_eventos(leituras)
        _ultimas = leituras
    return leituras


def _atualizar_calados(calados: dict[str, datetime]) -> None:
    """Escreve no log só quando um dispositivo fica calado ou volta, não a cada leitura."""
    global _calados
    for nome in calados.keys() - _calados.keys():
        registo.warning("%s não comunica desde %s; as leituras dele ficam de fora", nome, calados[nome])
    for nome in _calados.keys() - calados.keys():
        registo.info("%s voltou a comunicar", nome)
    _calados = calados


def _registar_eventos(leituras: list[Leitura]) -> None:
    for evento in _observador.ver(leituras):
        try:
            eventos.registar(evento)
        except Exception:  # noqa: BLE001 — fica no log; o histórico não deve parar a leitura da casa
            registo.exception("Não foi possível registar o evento %s", evento)


def executar(dispositivo: str, tipo: str, valor: str | int) -> bool:
    """Muda o dispositivo e devolve True se, ao lê-lo de novo, tem o valor pedido."""
    if simulacao.simulado(dispositivo, tipo):  # a válvula da água (US15): o kit não a tem
        return simulacao.executar(dispositivo, tipo, str(valor))
    _validar(dispositivo, tipo, valor)
    with _trinco:
        _comandos[(dispositivo, tipo)] = time.monotonic()
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


def comandado_ha_pouco(dispositivo: str, tipo: str) -> bool:
    """True se `executar` mandou este (dispositivo, tipo) há menos de COMANDO_SEGUNDOS segundos."""
    with _trinco:
        quando = _comandos.get((dispositivo, tipo))
    return quando is not None and time.monotonic() - quando < COMANDO_SEGUNDOS


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
