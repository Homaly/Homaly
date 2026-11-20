"""US04: o contacto externo, o tempo de espera e o nome da casa; `GET` e `PUT /definicoes`.

Uma só linha na tabela `definicoes`. Sem nada guardado, não há contacto e o tempo de espera é de
cinco minutos. O `contacto_externo` lê-as na hora de enviar cada SMS, por isso remover o contacto
pára os envios que ainda estavam à espera.
"""

from fastapi import APIRouter

from . import db
from .contrato import Contacto, Definicoes

ESPERA_POR_OMISSAO = 5

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS definicoes (
        id                 INTEGER PRIMARY KEY CHECK (id = 1),  -- uma casa por conta
        contacto_nome      TEXT,
        contacto_telemovel TEXT,  -- formato internacional, ex.: +351912345678
        espera_minutos     INTEGER NOT NULL,  -- o SQLite guarda 0.5 (30 s) como REAL, sem migração
        nome_casa          TEXT
    )
    """
)


def obter() -> Definicoes:
    with db.ligar() as con:
        linha = con.execute("SELECT * FROM definicoes WHERE id = 1").fetchone()
    if linha is None:
        return Definicoes(contacto=None, espera_minutos=ESPERA_POR_OMISSAO)
    contacto = (
        Contacto(nome=linha["contacto_nome"], telemovel=linha["contacto_telemovel"])
        if linha["contacto_telemovel"]
        else None
    )
    return Definicoes(contacto=contacto, espera_minutos=linha["espera_minutos"], nome_casa=linha["nome_casa"])


def guardar(definicoes: Definicoes) -> Definicoes:
    """Grava as definições (já validadas pelo modelo) e devolve-as como ficaram."""
    contacto = definicoes.contacto
    with db.ligar() as con:
        con.execute(
            """
            INSERT OR REPLACE INTO definicoes (id, contacto_nome, contacto_telemovel, espera_minutos, nome_casa)
            VALUES (1, ?, ?, ?, ?)
            """,
            (
                contacto.nome if contacto else None,
                contacto.telemovel if contacto else None,
                definicoes.espera_minutos,
                definicoes.nome_casa,
            ),
        )
    return obter()


router = APIRouter(prefix="/definicoes", tags=["definições"])


@router.get("")
def pedir_definicoes() -> dict:
    return obter().para_json()


@router.put("")
def pedir_guardar(definicoes: Definicoes) -> dict:
    return guardar(definicoes).para_json()
