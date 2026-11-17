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

    def completar_json(self, sistema: str, mensagem: str) -> dict | None:
        self.chamadas.append((sistema, mensagem))
        return self.resposta


@pytest.fixture(autouse=True)
def bd(monkeypatch, tmp_path):
    """Um ficheiro SQLite novo por teste, com todas as tabelas registadas criadas."""
    monkeypatch.setattr(db, "CAMINHO", str(tmp_path / "teste.db"))
    monkeypatch.setattr(db, "_aplicados", 0)
