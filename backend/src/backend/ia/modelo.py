"""O modelo de IA, trocável: quem o usa só conhece `Modelo`.

`IA_FORNECEDOR` escolhe o modelo. `falso` (ou por definir) não usa nenhum: a casa fica com o resumo
do desvio. O fornecedor real acrescenta-se aqui, num `if` novo em `obter_modelo`.
"""

import os
from typing import Protocol


class Modelo(Protocol):
    def completar_json(self, sistema: str, mensagem: str) -> dict | None:
        """A resposta do modelo como dicionário, ou `None` se falhou ou não há modelo."""
        ...


class ModeloFalso:
    def completar_json(self, sistema: str, mensagem: str) -> dict | None:
        return None


def obter_modelo() -> Modelo:
    fornecedor = os.environ.get("IA_FORNECEDOR") or "falso"
    if fornecedor == "falso":
        return ModeloFalso()
    raise ValueError(f"IA_FORNECEDOR desconhecido: {fornecedor!r}")
