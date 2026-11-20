from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from backend import db

LX = ZoneInfo("Europe/Lisbon")
AGORA = datetime(2026, 11, 17, 15, 0, tzinfo=LX)  # uma terça-feira


class ModeloFixo:
    """Um modelo que devolve sempre `resposta` e guarda as chamadas que recebeu."""

    def __init__(self, resposta: dict | None):
        self.resposta = resposta
        self.chamadas: list[tuple[str, str]] = []
        self.historicos: list[list[dict]] = []  # o histórico de cada chamada, em paralelo a `chamadas`

    def completar_json(self, sistema: str, mensagem: str, historico=()) -> dict | None:
        self.chamadas.append((sistema, mensagem))
        self.historicos.append(list(historico))
        return self.resposta


@pytest.fixture(autouse=True)
def bd(monkeypatch, tmp_path):
    """Um ficheiro SQLite novo por teste, com todas as tabelas registadas criadas."""
    monkeypatch.setattr(db, "CAMINHO", str(tmp_path / "teste.db"))
    monkeypatch.setattr(db, "_aplicados", 0)


@pytest.fixture(autouse=True)
def sem_registo_do_mcp():
    """O que um `dispositivos.ler()` regista do MCP não passa de um teste para o outro."""
    from backend import inventario

    inventario.esquecer_mcp()
    yield
    inventario.esquecer_mcp()


# Uma casa com várias divisões, para os testes com mais de um dispositivo do mesmo tipo.
CASA = [
    {"id": "porta-rua", "nome": "Porta da rua", "divisao": "a sala"},
    {"id": "janela-quarto", "nome": "Janela do quarto", "divisao": "o quarto"},
    {"id": "janela-sala", "nome": "Janela da sala", "divisao": "a sala"},
    {"id": "temp-sala", "nome": "Sensor da sala", "divisao": "a sala"},
    {"id": "temp-quarto", "nome": "Sensor do quarto", "divisao": "o quarto"},
    {"id": "temp-cozinha", "nome": "Sensor da cozinha", "divisao": "a cozinha"},
    {"id": "cam-sala", "nome": "Câmara da sala", "divisao": "a sala"},
    {"id": "cam-quarto", "nome": "Câmara do quarto", "divisao": "o quarto"},
    {"id": "cam-cozinha", "nome": "Câmara da cozinha", "divisao": "a cozinha"},
    {"id": "cam-rua", "nome": "Câmara da entrada de veículos", "divisao": "a entrada"},
    {"id": "tomada-quarto", "nome": "Tomada do quarto", "divisao": "o quarto"},
    {"id": "tomada-cozinha", "nome": "Tomada da máquina de lavar", "divisao": "a cozinha"},
    {"id": "luz-sala", "nome": "Luz da sala", "divisao": "a sala"},
    {"id": "luz-quarto", "nome": "Luz do quarto", "divisao": "o quarto"},
]


@pytest.fixture
def casa():
    """O inventário CASA em vez do ficheiro dados/dispositivos.csv."""
    from backend import inventario

    inventario.configurar(CASA)
    yield
    inventario.configurar(None)
