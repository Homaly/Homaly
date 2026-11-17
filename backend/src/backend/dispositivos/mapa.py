"""Do JSON do servidor MCP para as leituras da casa.

`get_home_devices` devolve `{"devices": [{"id", "type", "capabilities": [{"type", "value"}]}]}`.
Cada capability com um valor simples dá uma `Leitura`. O campo `name` das capabilities vem vazio,
por isso procura-se sempre pelo `type`.

O MCP devolve o último valor de cada dispositivo mesmo que ele não comunique há horas (o kit
desligado, sem rede). Cada dispositivo traz `lastCommunicationTime`, em milissegundos desde 1970:
os que não comunicam desde um limite ficam de fora das leituras.
"""

from datetime import UTC, datetime

from backend.formatos import Leitura

# O type do MCP -> o nome do dispositivo nas leituras (DIVISAO.md, secção 1).
NOMES = {
    "contactSensor": "porta",
    "temperatureSensor": "temperatura",
    "bulb": "lampada",
    "plug": "tomada",
    "camera": "camara",
    "smokeSensor": "fumo",
    "gateway": "hub",
}

_SIMPLES = (str, int, float, bool)


def nome(tipo_mcp: str) -> str:
    """O nome do dispositivo; um tipo desconhecido fica com o tipo original."""
    return NOMES.get(tipo_mcp, tipo_mcp)


def para_leituras(dados: dict, em: datetime, calados_antes_de: datetime | None = None) -> list[Leitura]:
    """Uma `Leitura` por capability com valor simples (listas e objetos ficam de fora).

    Com `calados_antes_de`, os dispositivos que não comunicam desde antes dessa hora não dão leituras.
    """
    return [
        Leitura(nome(d.get("type", "")), c["type"], c["value"], em)
        for d in dados.get("devices", [])
        if not _calado(d, calados_antes_de)
        for c in d.get("capabilities", [])
        if "type" in c and isinstance(c.get("value"), _SIMPLES)
    ]


def ultima_comunicacao(dispositivo: dict) -> datetime | None:
    """Quando o dispositivo comunicou pela última vez, ou None se o MCP não o diz."""
    ms = dispositivo.get("lastCommunicationTime")
    if isinstance(ms, bool) or not isinstance(ms, (int, float)):
        return None
    return datetime.fromtimestamp(ms / 1000, UTC)


def em_silencio(dados: dict, calados_antes_de: datetime) -> dict[str, datetime]:
    """Os dispositivos que não comunicam desde antes do limite, e desde quando."""
    return {
        nome(d.get("type", "")): quando
        for d in dados.get("devices", [])
        if (quando := ultima_comunicacao(d)) is not None and quando < calados_antes_de
    }


def _calado(dispositivo: dict, calados_antes_de: datetime | None) -> bool:
    if calados_antes_de is None:
        return False
    quando = ultima_comunicacao(dispositivo)
    return quando is not None and quando < calados_antes_de


def ids(dados: dict) -> dict[str, str]:
    """O id do MCP de cada dispositivo, pelo nome (ex.: {"lampada": "59dfc0f6-..."})."""
    return {nome(d.get("type", "")): d["id"] for d in dados.get("devices", []) if "id" in d}


def valor(detalhes: dict, tipo: str) -> str | int | float | bool | None:
    """O valor de uma capability na resposta de `get_device_details`, ou None."""
    for c in detalhes.get("capabilities", []):
        if c.get("type") == tipo:
            return c.get("value")
    return None
