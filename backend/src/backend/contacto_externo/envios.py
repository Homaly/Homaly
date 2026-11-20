"""A tabela dos envios ao contacto externo: uma linha por anomalia que pode chegar ao contacto.

O alerta passa por `pendente` (à espera do fim do tempo de espera) e `a_enviar` (reservado pela
thread que fala com o textbee, para ninguém o mudar a meio), e acaba em `enviada`, `cancelada` (o
responsável respondeu, resolveu-se, já não há contacto) ou `falhou` (o textbee recusou três
vezes, ou um erro inesperado). Depois de enviada, a SMS de resolvido passa por `resolvido`:
`pendente`, `enviada` ou `falhou`; `enviar_em` passa a ser a hora da próxima tentativa dela.
"""

from dataclasses import dataclass
from datetime import datetime

from backend import db

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS envios_contacto (
        anomalia_id          TEXT PRIMARY KEY,
        enviar_em            TEXT NOT NULL,     -- ISO 8601: o fim do tempo de espera
        estado               TEXT NOT NULL,     -- pendente, a_enviar, enviada, cancelada, falhou
        motivo               TEXT,              -- porque foi cancelada ou falhou
        tentativas           INTEGER NOT NULL DEFAULT 0,
        telemovel            TEXT,              -- para onde foi o alerta (e vai o resolvido)
        codigo               TEXT UNIQUE,       -- marca o alerta como enviado (era o do link da página, que saiu)
        ultima_sms_em        TEXT,              -- a hora da última SMS
        resolvido            TEXT,              -- NULL, pendente, enviada, falhou
        resolvido_em         TEXT,
        tentativas_resolvido INTEGER NOT NULL DEFAULT 0
    )
    """
)


@dataclass(frozen=True)
class Envio:
    anomalia_id: str
    enviar_em: datetime
    estado: str
    tentativas: int
    telemovel: str | None
    codigo: str | None
    ultima_sms_em: datetime | None
    resolvido: str | None
    resolvido_em: datetime | None
    tentativas_resolvido: int


def _data(texto: str | None) -> datetime | None:
    return datetime.fromisoformat(texto) if texto else None


def _envio(linha) -> Envio:
    return Envio(
        anomalia_id=linha["anomalia_id"],
        enviar_em=datetime.fromisoformat(linha["enviar_em"]),
        estado=linha["estado"],
        tentativas=linha["tentativas"],
        telemovel=linha["telemovel"],
        codigo=linha["codigo"],
        ultima_sms_em=_data(linha["ultima_sms_em"]),
        resolvido=linha["resolvido"],
        resolvido_em=_data(linha["resolvido_em"]),
        tentativas_resolvido=linha["tentativas_resolvido"],
    )


def obter(anomalia_id: str) -> Envio | None:
    with db.ligar() as con:
        linha = con.execute("SELECT * FROM envios_contacto WHERE anomalia_id = ?", (anomalia_id,)).fetchone()
    return _envio(linha) if linha else None


def por_codigo(codigo: str) -> Envio | None:
    with db.ligar() as con:
        linha = con.execute("SELECT * FROM envios_contacto WHERE codigo = ?", (codigo,)).fetchone()
    return _envio(linha) if linha else None


def criar(anomalia_id: str, enviar_em: datetime) -> None:
    with db.ligar() as con:
        con.execute(
            "INSERT OR IGNORE INTO envios_contacto (anomalia_id, enviar_em, estado) VALUES (?, ?, 'pendente')",
            (anomalia_id, enviar_em.isoformat()),
        )


def pendentes() -> list[Envio]:
    with db.ligar() as con:
        linhas = con.execute("SELECT * FROM envios_contacto WHERE estado = 'pendente'").fetchall()
    return [_envio(l) for l in linhas]


def resolvidos_por_enviar() -> list[Envio]:
    with db.ligar() as con:
        linhas = con.execute(
            "SELECT * FROM envios_contacto WHERE estado = 'enviada' AND resolvido = 'pendente'"
        ).fetchall()
    return [_envio(l) for l in linhas]


_COLUNAS = {
    "enviar_em",
    "estado",
    "motivo",
    "tentativas",
    "telemovel",
    "codigo",
    "ultima_sms_em",
    "resolvido",
    "resolvido_em",
    "tentativas_resolvido",
}


def mudar(anomalia_id: str, *, so_se_estado: str | None = None, **campos: object) -> bool:
    """Muda colunas de um envio; com `so_se_estado`, só se ele ainda estiver nesse estado.

    Devolve se mudou. Os nomes das colunas vêm só deste pacote, nunca de fora (e são verificados).
    """
    desconhecidas = campos.keys() - _COLUNAS
    if desconhecidas:
        raise ValueError(f"Colunas desconhecidas: {sorted(desconhecidas)}")
    valores = [v.isoformat() if isinstance(v, datetime) else v for v in campos.values()]
    atribuicoes = ", ".join(f"{nome} = ?" for nome in campos)
    sql = f"UPDATE envios_contacto SET {atribuicoes} WHERE anomalia_id = ?"
    parametros: list[object] = [*valores, anomalia_id]
    if so_se_estado is not None:
        sql += " AND estado = ?"
        parametros.append(so_se_estado)
    with db.ligar() as con:
        return con.execute(sql, parametros).rowcount == 1


def recuperar_interrompidos() -> int:
    """Os que ficaram `a_enviar` (o backend caiu a meio) voltam a `pendente`; devolve quantos."""
    with db.ligar() as con:
        return con.execute("UPDATE envios_contacto SET estado = 'pendente' WHERE estado = 'a_enviar'").rowcount
