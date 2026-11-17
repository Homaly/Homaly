"""Os eventos do histórico (US06): o que os sensores registaram, e o pedido `GET /eventos`.

`eventos.registar(evento)` grava o evento e envia-o à PWA pelo WebSocket.
"""

from datetime import UTC

from fastapi import APIRouter

from . import db, tempo_real
from .contrato import Evento

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS eventos (
        id    TEXT PRIMARY KEY,
        em    TEXT NOT NULL,  -- ISO 8601 em UTC, para ordenar
        dados TEXT NOT NULL   -- o Evento inteiro, em JSON, como em contract.ts
    )
    """
)
db.esquema("CREATE INDEX IF NOT EXISTS eventos_em ON eventos (em)")


def registar(evento: Evento) -> None:
    with db.ligar() as con:
        con.execute(
            "INSERT OR REPLACE INTO eventos (id, em, dados) VALUES (?, ?, ?)",
            (
                evento.id,
                evento.em.astimezone(UTC).isoformat(),
                evento.model_dump_json(by_alias=True, exclude_none=True),
            ),
        )
    tempo_real.enviar_evento(evento)


def listar(limite: int = 200) -> list[Evento]:
    """Do mais recente para o mais antigo."""
    with db.ligar() as con:
        linhas = con.execute(
            "SELECT dados FROM eventos ORDER BY em DESC LIMIT ?", (limite,)
        ).fetchall()
    return [Evento.model_validate_json(linha["dados"]) for linha in linhas]


router = APIRouter(tags=["eventos"])


@router.get("/eventos", response_model=list[Evento], response_model_exclude_none=True)
def pedir_eventos() -> list[Evento]:
    return listar()
