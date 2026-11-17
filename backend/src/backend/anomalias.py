"""As anomalias: a tabela, as funções para as guardar e ler, e os pedidos `/anomalias`.

Quem publica uma anomalia (o `avisos.publicar`) chama `anomalias.guardar(a)` e depois
`tempo_real.enviar_anomalia(a)`. Guardar outra vez uma anomalia com o mesmo id atualiza-a.
Guardar uma anomalia nova, ou passá-la a resolvida, deixa também um evento no histórico (US06).

Os pedidos `POST /anomalias/{id}/resposta` e `/silencio` são da US02 e ficam no router de quem a
faz; podem usar `obter` e `guardar` daqui.
"""

import logging
from datetime import UTC
from typing import Literal

from fastapi import APIRouter, HTTPException

from . import db, historico
from .contrato import Anomalia

registo = logging.getLogger(__name__)

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS anomalias (
        id          TEXT PRIMARY KEY,
        estado      TEXT NOT NULL,
        detetada_em TEXT NOT NULL,  -- ISO 8601 em UTC, para ordenar
        dados       TEXT NOT NULL   -- a Anomalia inteira, em JSON, como em contract.ts
    )
    """
)

Estado = Literal["ativa", "resolvida"]


def guardar(anomalia: Anomalia) -> None:
    """Grava uma anomalia nova ou substitui a que tem o mesmo id, e regista-a no histórico."""
    anterior = obter(anomalia.id)
    with db.ligar() as con:
        con.execute(
            """
            INSERT INTO anomalias (id, estado, detetada_em, dados) VALUES (?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                estado = excluded.estado,
                detetada_em = excluded.detetada_em,
                dados = excluded.dados
            """,
            (
                anomalia.id,
                anomalia.estado,
                anomalia.detetada_em.astimezone(UTC).isoformat(),
                anomalia.model_dump_json(by_alias=True, exclude_none=True),
            ),
        )
    try:
        historico.anomalia_mudou(anterior, anomalia)
    except Exception:
        # O histórico nunca impede a anomalia de chegar ao responsável.
        registo.exception("Não consegui registar a anomalia %s no histórico", anomalia.id)


def obter(id: str) -> Anomalia | None:
    with db.ligar() as con:
        linha = con.execute("SELECT dados FROM anomalias WHERE id = ?", (id,)).fetchone()
    return Anomalia.model_validate_json(linha["dados"]) if linha else None


def listar(estado: Estado | None = None) -> list[Anomalia]:
    """Da mais recente para a mais antiga."""
    sql = "SELECT dados FROM anomalias"
    parametros: tuple = ()
    if estado:
        sql += " WHERE estado = ?"
        parametros = (estado,)
    with db.ligar() as con:
        linhas = con.execute(sql + " ORDER BY detetada_em DESC", parametros).fetchall()
    return [Anomalia.model_validate_json(linha["dados"]) for linha in linhas]


router = APIRouter(prefix="/anomalias", tags=["anomalias"])


@router.get("", response_model=list[Anomalia], response_model_exclude_none=True)
def pedir_lista(estado: Estado | None = None) -> list[Anomalia]:
    return listar(estado)


@router.get("/{id}", response_model=Anomalia, response_model_exclude_none=True)
def pedir_anomalia(id: str) -> Anomalia:
    anomalia = obter(id)
    if anomalia is None:
        raise HTTPException(404, "Anomalia não encontrada")
    return anomalia
