"""Onde fica o calendário: a ligação (uma só) e o que a casa tirou dele.

Os itens estão à parte das férias e rotinas ditas no chat, para remover o calendário apagar só o
que veio dele. `contexto.repositorio.carregar_contexto` junta os dois.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, time

from backend import db
from backend.formatos import Compromisso, Periodo, Rotina

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS calendario_ligacao (
        id            INTEGER PRIMARY KEY CHECK (id = 1),  -- um calendário por casa
        email         TEXT,
        refresh_token TEXT NOT NULL,
        ligado_em     TEXT NOT NULL,
        lido_em       TEXT,   -- a última leitura que correu bem
        erro          TEXT    -- o que correu mal na última leitura, ou NULL
    );
    CREATE TABLE IF NOT EXISTS calendario_itens (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo  TEXT NOT NULL CHECK (tipo IN ('ferias', 'rotina', 'compromisso')),
        dados TEXT NOT NULL   -- JSON
    );
    """
)


@dataclass(frozen=True)
class EstadoLigacao:
    email: str | None
    refresh_token: str
    ligado_em: datetime
    lido_em: datetime | None
    erro: str | None


@dataclass
class Itens:
    """O que a casa tirou do calendário."""

    ferias: list[Periodo] = field(default_factory=list)
    rotinas: list[Rotina] = field(default_factory=list)
    compromissos: list[Compromisso] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.ferias) + len(self.rotinas) + len(self.compromissos)


def guardar_ligacao(email: str | None, refresh_token: str, agora: datetime) -> None:
    """Liga (ou volta a ligar) o calendário. Os itens de antes saem: podiam ser de outra conta."""
    with db.ligar() as con:
        con.execute("DELETE FROM calendario_itens")
        con.execute(
            """
            INSERT OR REPLACE INTO calendario_ligacao (id, email, refresh_token, ligado_em, lido_em, erro)
            VALUES (1, ?, ?, ?, NULL, NULL)
            """,
            (email, refresh_token, agora.isoformat()),
        )


def ligacao() -> EstadoLigacao | None:
    with db.ligar() as con:
        linha = con.execute("SELECT * FROM calendario_ligacao WHERE id = 1").fetchone()
    if linha is None:
        return None
    return EstadoLigacao(
        email=linha["email"],
        refresh_token=linha["refresh_token"],
        ligado_em=datetime.fromisoformat(linha["ligado_em"]),
        lido_em=datetime.fromisoformat(linha["lido_em"]) if linha["lido_em"] else None,
        erro=linha["erro"],
    )


def guardar_leitura(itens: Itens, agora: datetime) -> bool:
    """Substitui os itens pelos desta leitura: o calendário é que manda.

    Se entretanto o calendário foi removido, não guarda nada (`False`): uma leitura que demorou
    não pode trazer de volta o que a pessoa apagou.
    """
    linhas = (
        [("ferias", _periodo_json(p)) for p in itens.ferias]
        + [("rotina", _rotina_json(r)) for r in itens.rotinas]
        + [("compromisso", _compromisso_json(c)) for c in itens.compromissos]
    )
    with db.ligar() as con:
        ligado = con.execute(
            "UPDATE calendario_ligacao SET lido_em = ?, erro = NULL WHERE id = 1", (agora.isoformat(),)
        ).rowcount
        if not ligado:
            return False
        con.execute("DELETE FROM calendario_itens")
        con.executemany("INSERT INTO calendario_itens (tipo, dados) VALUES (?, ?)", linhas)
    return True


def guardar_erro(erro: str) -> None:
    """A leitura falhou: os itens da anterior ficam, e a secção mostra o erro."""
    with db.ligar() as con:
        con.execute("UPDATE calendario_ligacao SET erro = ? WHERE id = 1", (erro,))


def itens() -> Itens:
    """O que veio do calendário; nada, se não estiver ligado."""
    with db.ligar() as con:
        linhas = con.execute(
            "SELECT tipo, dados FROM calendario_itens WHERE EXISTS (SELECT 1 FROM calendario_ligacao) ORDER BY id"
        ).fetchall()
    resultado = Itens()
    for linha in linhas:
        dados = json.loads(linha["dados"])
        if linha["tipo"] == "ferias":
            resultado.ferias.append(
                Periodo(datetime.fromisoformat(dados["inicio"]), datetime.fromisoformat(dados["fim"]), dados["motivo"])
            )
        elif linha["tipo"] == "rotina":
            hora = time.fromisoformat(dados["hora"]) if dados["hora"] else None
            resultado.rotinas.append(Rotina(dados["descricao"], dados["dias"], hora))
        else:
            resultado.compromissos.append(
                Compromisso(
                    dados["descricao"], datetime.fromisoformat(dados["inicio"]), datetime.fromisoformat(dados["fim"])
                )
            )
    return resultado


def apagar_tudo() -> None:
    """Remove o calendário: a ligação e tudo o que veio dele."""
    with db.ligar() as con:
        con.execute("DELETE FROM calendario_itens")
        con.execute("DELETE FROM calendario_ligacao")


def _periodo_json(p: Periodo) -> str:
    return json.dumps({"inicio": p.inicio.isoformat(), "fim": p.fim.isoformat(), "motivo": p.motivo})


def _rotina_json(r: Rotina) -> str:
    return json.dumps({"descricao": r.descricao, "dias": r.dias, "hora": r.hora.strftime("%H:%M") if r.hora else None})


def _compromisso_json(c: Compromisso) -> str:
    return json.dumps({"descricao": c.descricao, "inicio": c.inicio.isoformat(), "fim": c.fim.isoformat()})
