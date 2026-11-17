"""O que os routers recebem por `Depends`; os testes substituem-no com `app.dependency_overrides`."""

import logging
from datetime import datetime

from backend import contrato
from backend.ia.modelo import Modelo, ModeloFalso, obter_modelo

registo = logging.getLogger(__name__)


def obter_modelo_dep() -> Modelo:
    try:
        return obter_modelo()
    except ValueError:
        registo.warning("IA_FORNECEDOR desconhecido; sem modelo de IA.", exc_info=True)
        return ModeloFalso()


def obter_agora() -> datetime:
    return contrato.agora()
