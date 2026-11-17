"""O relógio do ciclo ao vivo: a hora real, ou uma hora simulada acelerada (para a demo).

Sem RELOGIO_INICIO, é a hora real. Com ele, a hora começa em RELOGIO_INICIO quando o
ciclo arranca e avança RELOGIO_FATOR vezes mais depressa do que a real (1 por omissão).
Os valores da demo escolhem-se quando a cena estiver decidida.

Há um só relógio por processo (`partilhado()`): o ciclo e a API (`dependencias.obter_agora`)
leem a mesma hora, para o silêncio "até ao fim do dia", as férias ditas na conversa e as
horas do histórico baterem certo com a hora simulada.
"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from typing import Callable

from backend.contrato import agora
from backend.regras._comum import com_fuso


class Relogio:
    def __init__(
        self,
        inicio: datetime | None = None,
        fator: float = 1.0,
        real: Callable[[], datetime] = agora,
    ) -> None:
        self.inicio = inicio
        self.fator = fator
        self._real = real
        self._arranque = real()

    def agora(self) -> datetime:
        if self.inicio is None:
            return self._real()
        return self.inicio + (self._real() - self._arranque) * self.fator

    @classmethod
    def do_ambiente(cls) -> "Relogio":
        inicio = os.environ.get("RELOGIO_INICIO") or None
        fator = os.environ.get("RELOGIO_FATOR") or "1"
        return cls(com_fuso(datetime.fromisoformat(inicio)) if inicio else None, float(fator))


_partilhado: Relogio | None = None
_trinco = threading.Lock()


def partilhado() -> Relogio:
    """O relógio do processo, criado do ambiente na primeira vez (o lifespan da app chama-o)."""
    global _partilhado
    with _trinco:
        if _partilhado is None:
            _partilhado = Relogio.do_ambiente()
        return _partilhado
