"""O que os routers recebem por `Depends`; os testes substituem-no com `app.dependency_overrides`."""

from datetime import datetime

from backend import contrato
from backend.ia.modelo import Modelo, obter_modelo


def obter_modelo_dep() -> Modelo:
    return obter_modelo()


def obter_agora() -> datetime:
    return contrato.agora()
