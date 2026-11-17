"""A base de dados: um só ficheiro SQLite para todo o backend.

Cada módulo regista as suas tabelas com `db.esquema("CREATE TABLE IF NOT EXISTS ...")` quando é
importado, e usa `with db.ligar() as con:` para ler e escrever. As tabelas registadas são criadas
na primeira ligação, por isso ninguém espera por um esquema central.

O ficheiro fica em `DB_PATH` (por omissão `homaly.db`, na pasta onde o backend arranca).
"""

import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager

CAMINHO = os.environ.get("DB_PATH") or "homaly.db"

_esquemas: list[str] = []
_aplicados = 0
_trinco = threading.Lock()


def esquema(sql: str) -> None:
    """Regista um `CREATE TABLE IF NOT EXISTS ...`; corre antes da próxima ligação."""
    _esquemas.append(sql)


@contextmanager
def ligar() -> Iterator[sqlite3.Connection]:
    """Uma ligação nova. No fim do bloco faz commit, ou rollback se houve exceção."""
    con = sqlite3.connect(CAMINHO, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        _aplicar_esquemas(con)
        with con:
            yield con
    finally:
        con.close()


def _aplicar_esquemas(con: sqlite3.Connection) -> None:
    global _aplicados
    if _aplicados == len(_esquemas):
        return
    with _trinco:
        if _aplicados == 0:
            # Leituras e escritas em simultâneo (pedidos da API e o ciclo das regras).
            con.execute("PRAGMA journal_mode=WAL")
        for sql in _esquemas[_aplicados:]:
            con.executescript(sql)
        _aplicados = len(_esquemas)
