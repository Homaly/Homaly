"""O contexto da casa guardado em SQLite: o que a pessoa disse à casa (US01, US02).

Datas guardadas em ISO 8601 com o fuso; as mensagens têm também `em_utc`, só para ordenar.
Filtrar silêncios expirados é de quem os lê; aqui devolve-se tudo.
"""

import json
import sqlite3
from datetime import UTC, datetime, time
from typing import Literal

from backend import db
from backend.contrato import MensagemConversa, _com_fuso
from backend.formatos import Contexto, Periodo, Rotina, Silencio

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS ferias (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        inicio TEXT NOT NULL,
        fim    TEXT NOT NULL,
        motivo TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS rotinas (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL,
        dias      TEXT NOT NULL,  -- lista JSON, 0 = segunda
        hora      TEXT            -- "HH:MM" ou NULL
    );
    CREATE TABLE IF NOT EXISTS silencios (
        id     INTEGER PRIMARY KEY AUTOINCREMENT,
        us     TEXT NOT NULL,
        ate    TEXT,              -- NULL: até ser removido
        motivo TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS mensagens (
        id    TEXT PRIMARY KEY,
        em_utc TEXT NOT NULL,     -- ISO 8601 em UTC, para ordenar
        dados TEXT NOT NULL       -- a MensagemConversa, em JSON
    );
    CREATE TABLE IF NOT EXISTS aparelho_tomada (
        id   INTEGER PRIMARY KEY CHECK (id = 1),  -- só há uma tomada
        nome TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS rotinas_recusadas (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        descricao TEXT NOT NULL,
        dias      TEXT NOT NULL,  -- lista JSON, 0 = segunda
        hora      TEXT            -- "HH:MM" ou NULL
    );
    CREATE TABLE IF NOT EXISTS propostas_silencio (
        anomalia_id TEXT PRIMARY KEY,
        dados       TEXT NOT NULL  -- JSON
    );
    """
)


def guardar_periodo(p: Periodo) -> None:
    with db.ligar() as con:
        con.execute(
            "INSERT INTO ferias (inicio, fim, motivo) VALUES (?, ?, ?)",
            (p.inicio.isoformat(), p.fim.isoformat(), p.motivo),
        )


def guardar_rotina(r: Rotina) -> None:
    _inserir_rotina("rotinas", r)


def guardar_recusa(r: Rotina) -> None:
    """Uma rotina que a casa propôs e a pessoa recusou: a casa não a volta a propor."""
    _inserir_rotina("rotinas_recusadas", r)


def rotinas_recusadas() -> list[Rotina]:
    with db.ligar() as con:
        return [_ler_rotina(linha) for linha in con.execute("SELECT * FROM rotinas_recusadas ORDER BY id")]


def _inserir_rotina(tabela: Literal["rotinas", "rotinas_recusadas"], r: Rotina) -> None:
    # O nome da tabela vem sempre de cá (Literal), nunca de quem pede.
    with db.ligar() as con:
        con.execute(
            f"INSERT INTO {tabela} (descricao, dias, hora) VALUES (?, ?, ?)",
            (r.descricao, json.dumps(r.dias), r.hora.strftime("%H:%M") if r.hora else None),
        )


def _ler_rotina(linha: sqlite3.Row) -> Rotina:
    return Rotina(linha["descricao"], json.loads(linha["dias"]), time.fromisoformat(linha["hora"]) if linha["hora"] else None)


def guardar_silencio(s: Silencio) -> None:
    with db.ligar() as con:
        con.execute(
            "INSERT INTO silencios (us, ate, motivo) VALUES (?, ?, ?)",
            (s.us, s.ate.isoformat() if s.ate else None, s.motivo),
        )


def guardar_aparelho(nome: str) -> None:
    """Substitui o aparelho anterior: só há uma tomada."""
    with db.ligar() as con:
        con.execute("INSERT OR REPLACE INTO aparelho_tomada (id, nome) VALUES (1, ?)", (nome,))


def carregar_contexto(agora: datetime) -> Contexto:
    agora = _com_fuso(agora)
    with db.ligar() as con:
        ferias = [
            Periodo(datetime.fromisoformat(linha["inicio"]), datetime.fromisoformat(linha["fim"]), linha["motivo"])
            for linha in con.execute("SELECT * FROM ferias ORDER BY id")
        ]
        rotinas = [_ler_rotina(linha) for linha in con.execute("SELECT * FROM rotinas ORDER BY id")]
        silencios = [
            Silencio(linha["us"], datetime.fromisoformat(linha["ate"]) if linha["ate"] else None, linha["motivo"])
            for linha in con.execute("SELECT * FROM silencios ORDER BY id")
        ]
        aparelho = con.execute("SELECT nome FROM aparelho_tomada WHERE id = 1").fetchone()
    return Contexto(
        ferias=ferias,
        rotinas=rotinas,
        silencios=silencios,
        casa_vazia=any(p.inicio <= agora <= p.fim for p in ferias),
        aparelho_tomada=aparelho["nome"] if aparelho else None,
    )


def guardar_mensagem(m: MensagemConversa) -> None:
    with db.ligar() as con:
        con.execute(
            "INSERT OR REPLACE INTO mensagens (id, em_utc, dados) VALUES (?, ?, ?)",
            (m.id, m.em.astimezone(UTC).isoformat(), m.model_dump_json()),
        )


def listar_mensagens() -> list[MensagemConversa]:
    """Da mais antiga para a mais recente."""
    with db.ligar() as con:
        linhas = con.execute("SELECT dados FROM mensagens ORDER BY em_utc, rowid").fetchall()
    return [MensagemConversa.model_validate_json(linha["dados"]) for linha in linhas]


def guardar_proposta(anomalia_id: str, dados: dict) -> None:
    with db.ligar() as con:
        con.execute(
            "INSERT OR REPLACE INTO propostas_silencio (anomalia_id, dados) VALUES (?, ?)",
            (anomalia_id, json.dumps(dados)),
        )


def ler_proposta(anomalia_id: str) -> dict | None:
    with db.ligar() as con:
        linha = con.execute(
            "SELECT dados FROM propostas_silencio WHERE anomalia_id = ?", (anomalia_id,)
        ).fetchone()
    return json.loads(linha["dados"]) if linha else None


def apagar_proposta(anomalia_id: str) -> None:
    with db.ligar() as con:
        con.execute("DELETE FROM propostas_silencio WHERE anomalia_id = ?", (anomalia_id,))
