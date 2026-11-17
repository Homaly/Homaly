"""Do JSON do servidor MCP para as leituras da casa.

`get_home_devices` devolve `{"devices": [{"id", "type", "capabilities": [{"type", "value"}]}]}`.
Cada capability com um valor simples dá uma `Leitura`. O campo `name` das capabilities vem vazio,
por isso procura-se sempre pelo `type`.
"""

from datetime import datetime

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


def para_leituras(dados: dict, em: datetime) -> list[Leitura]:
    """Uma `Leitura` por capability com valor simples (listas e objetos ficam de fora)."""
    return [
        Leitura(nome(d.get("type", "")), c["type"], c["value"], em)
        for d in dados.get("devices", [])
        for c in d.get("capabilities", [])
        if "type" in c and isinstance(c.get("value"), _SIMPLES)
    ]


def ids(dados: dict) -> dict[str, str]:
    """O id do MCP de cada dispositivo, pelo nome (ex.: {"lampada": "59dfc0f6-..."})."""
    return {nome(d.get("type", "")): d["id"] for d in dados.get("devices", []) if "id" in d}


def valor(detalhes: dict, tipo: str) -> str | int | float | bool | None:
    """O valor de uma capability na resposta de `get_device_details`, ou None."""
    for c in detalhes.get("capabilities", []):
        if c.get("type") == tipo:
            return c.get("value")
    return None
