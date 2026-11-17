"""US08 (porta esquecida aberta) e US12 (porta aberta com a sala a arrefecer), num só aviso.

Por cada abertura da porta há no máximo um aviso, que muda em vez de se repetir:
- a sala desce PORTA_QUEDA_GRAUS (2 °C) desde que a porta abriu: aviso de eficiência (US12);
- a porta continua aberta PORTA_MINUTOS (5 min): o aviso passa a segurança (US08), ou já nasce
  de segurança se a sala ainda não desceu;
- a porta fecha depois do aviso: `Resolucao` com a hora ("a porta fechou às 14:12").

O ciclo identifica o aviso pela US, por isso a US com que o aviso nasce fica até ao fim da
abertura: se foi a US12, continua US12 mesmo depois de passar a segurança. Enquanto o problema
dura, a regra devolve o desvio em todas as voltas, sempre com o mesmo texto (só muda quando o aviso
muda), para o ciclo não o republicar a cada leitura.

O que a regra lembra entre voltas fica na tabela `estado_porta`. Uma volta sem leitura da porta,
ou com um valor que não é `alarm` nem `normal`, conta como a última leitura conhecida: uma falha
do MCP não resolve nem esquece nada.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from backend import db
from backend.formatos import Contexto, Desvio, Leitura, Resolucao

from ._comum import com_fuso, decimal, graus, hora, numero, ultima

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS estado_porta (
        id           INTEGER PRIMARY KEY CHECK (id = 1),  -- só há uma porta
        aberta_em    TEXT NOT NULL,  -- ISO 8601, com fuso
        temp_inicial REAL,           -- a temperatura da sala quando a porta abriu
        queda        REAL,           -- quanto a sala desceu quando passou o limite (fica fixa)
        temp_queda   REAL,           -- a temperatura nesse momento
        us           TEXT            -- a US do aviso desta abertura, depois de avisar
    )
    """
)


@dataclass(frozen=True)
class Estado:
    aberta_em: datetime
    temp_inicial: float | None = None
    queda: float | None = None
    temp_queda: float | None = None
    us: str | None = None


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio | Resolucao]:
    agora = com_fuso(agora)
    anterior = _carregar()
    if anterior is not None and anterior.aberta_em > agora:
        # Estado de um "futuro" (ex.: um CSV de outro dia corrido contra esta base de dados).
        _apagar()
        anterior = None
    lida = ultima(leituras, "porta", "sensorState")
    aberta = lida == "alarm" if lida in ("alarm", "normal") else anterior is not None

    if not aberta:
        if anterior is None:
            return []
        _apagar()
        return [Resolucao(anterior.us, f"a porta fechou às {hora(agora)}", agora)] if anterior.us else []

    estado = _com_temperatura(anterior or Estado(aberta_em=agora), ultima(leituras, "temperatura", "temperatureValue"))
    seguranca = agora - estado.aberta_em >= timedelta(minutes=numero("PORTA_MINUTOS", 5))
    if not seguranca and estado.queda is None:
        _guardar(estado)
        return []
    us = estado.us or ("US08" if seguranca else "US12")
    estado = replace(estado, us=us)
    _guardar(estado)
    return [_desvio(estado, us, seguranca)]


def _com_temperatura(estado: Estado, temperatura: object) -> Estado:
    """Guarda a temperatura inicial e, uma só vez, a descida que passou o limite."""
    if not isinstance(temperatura, (int, float)) or isinstance(temperatura, bool):
        return estado
    if estado.temp_inicial is None:
        return replace(estado, temp_inicial=float(temperatura))
    queda = round(estado.temp_inicial - temperatura, 1)
    if estado.queda is None and queda >= numero("PORTA_QUEDA_GRAUS", 2):
        return replace(estado, queda=queda, temp_queda=float(temperatura))
    return estado


def _desvio(estado: Estado, us: str, seguranca: bool) -> Desvio:
    desde = hora(estado.aberta_em)
    if not seguranca:
        # Só há aviso antes dos cinco minutos se a sala já desceu, e a descida guarda as três.
        assert estado.queda is not None and estado.temp_inicial is not None and estado.temp_queda is not None
        resumo = (
            f"A porta da rua está aberta desde as {desde} e a sala já desceu {graus(estado.queda)} "
            f"(de {graus(estado.temp_inicial)} para {graus(estado.temp_queda)})."
        )
        return Desvio(us=us, classe="eficiencia", resumo=resumo, habitual=None)
    minutos = numero("PORTA_MINUTOS", 5)
    unidade = "minuto" if minutos == 1 else "minutos"
    resumo = f"A porta da rua está aberta há mais de {decimal(minutos)} {unidade}, desde as {desde}"
    resumo += f", e a sala já desceu {graus(estado.queda)}." if estado.queda is not None else "."
    return Desvio(us=us, classe="seguranca", resumo=resumo, habitual=None)


def _carregar() -> Estado | None:
    with db.ligar() as con:
        linha = con.execute("SELECT * FROM estado_porta WHERE id = 1").fetchone()
    if linha is None:
        return None
    return Estado(
        aberta_em=com_fuso(datetime.fromisoformat(linha["aberta_em"])),
        temp_inicial=linha["temp_inicial"],
        queda=linha["queda"],
        temp_queda=linha["temp_queda"],
        us=linha["us"],
    )


def _guardar(estado: Estado) -> None:
    with db.ligar() as con:
        con.execute(
            """
            INSERT OR REPLACE INTO estado_porta (id, aberta_em, temp_inicial, queda, temp_queda, us)
            VALUES (1, ?, ?, ?, ?, ?)
            """,
            (estado.aberta_em.isoformat(), estado.temp_inicial, estado.queda, estado.temp_queda, estado.us),
        )


def _apagar() -> None:
    with db.ligar() as con:
        con.execute("DELETE FROM estado_porta")
