"""US10: casa fria durante horas.

A sala abaixo de FRIO_LIMITE_GRAUS (16 °C) durante FRIO_MINUTOS (120) dá um aviso de saúde e
conforto, com a temperatura nesse momento e, quando o histórico existir, a habitual a essa hora.
Quando volta ao limite ou acima, a regra devolve uma `Resolucao` ("a temperatura voltou a
16,4 °C às 15:10").

Enquanto o aviso está ativo, a regra devolve o mesmo desvio, com o mesmo texto, em todas as
voltas. O que lembra entre voltas fica na tabela `estado_temperatura`. Uma volta sem leitura da
temperatura não muda nada.
"""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from backend import db
from backend.formatos import Contexto, Desvio, Leitura, Resolucao

from ._comum import com_fuso, graus, hora, numero, ultima

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS estado_temperatura (
        id           INTEGER PRIMARY KEY CHECK (id = 1),  -- só há um sensor
        abaixo_desde TEXT NOT NULL,  -- ISO 8601, com fuso
        aviso_em     TEXT,           -- quando avisou (None: ainda não)
        temp_aviso   REAL,           -- a temperatura nesse momento
        habitual     REAL            -- a temperatura habitual a essa hora, se se souber
    )
    """
)


@dataclass(frozen=True)
class Estado:
    abaixo_desde: datetime
    aviso_em: datetime | None = None
    temp_aviso: float | None = None
    habitual: float | None = None


def temperatura_habitual(agora: datetime) -> float | None:
    """A temperatura habitual da sala a esta hora, do histórico simulado da Vila.

    Ainda não existe: devolve None e o aviso diz só a temperatura atual. Quando o histórico
    existir, esta função passa a perguntar-lhe.
    """
    return None


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio | Resolucao]:
    agora = com_fuso(agora)
    anterior = _carregar()
    if anterior is not None and anterior.abaixo_desde > agora:
        # Estado de um "futuro" (ex.: um CSV de outro dia corrido contra esta base de dados).
        _apagar()
        anterior = None
    lida = ultima(leituras, "temperatura", "temperatureValue")
    if not isinstance(lida, (int, float)) or isinstance(lida, bool):
        return [_desvio(anterior)] if anterior and anterior.aviso_em else []

    limite = numero("FRIO_LIMITE_GRAUS", 16)
    if lida >= limite:
        if anterior is None:
            return []
        _apagar()
        if anterior.aviso_em is None:
            return []
        return [Resolucao("US10", f"a temperatura voltou a {graus(lida)} às {hora(agora)}", agora)]

    estado = anterior or Estado(abaixo_desde=agora)
    if estado.aviso_em is None and agora - estado.abaixo_desde >= timedelta(minutes=numero("FRIO_MINUTOS", 120)):
        estado = replace(estado, aviso_em=agora, temp_aviso=float(lida), habitual=temperatura_habitual(agora))
    _guardar(estado)
    return [_desvio(estado)] if estado.aviso_em else []


def _desvio(estado: Estado) -> Desvio:
    # Só se chama depois do aviso, que guarda a hora e a temperatura.
    assert estado.aviso_em is not None and estado.temp_aviso is not None
    limite = graus(numero("FRIO_LIMITE_GRAUS", 16))
    resumo = (
        f"A sala está abaixo de {limite} desde as {hora(estado.abaixo_desde)}; "
        f"às {hora(estado.aviso_em)} estava a {graus(estado.temp_aviso)}."
    )
    habitual = f"a esta hora a sala costuma estar a {graus(estado.habitual)}" if estado.habitual is not None else None
    return Desvio(us="US10", classe="saude_conforto", resumo=resumo, habitual=habitual)


def _carregar() -> Estado | None:
    with db.ligar() as con:
        linha = con.execute("SELECT * FROM estado_temperatura WHERE id = 1").fetchone()
    if linha is None:
        return None
    return Estado(
        abaixo_desde=com_fuso(datetime.fromisoformat(linha["abaixo_desde"])),
        aviso_em=com_fuso(datetime.fromisoformat(linha["aviso_em"])) if linha["aviso_em"] else None,
        temp_aviso=linha["temp_aviso"],
        habitual=linha["habitual"],
    )


def _guardar(estado: Estado) -> None:
    with db.ligar() as con:
        con.execute(
            """
            INSERT OR REPLACE INTO estado_temperatura (id, abaixo_desde, aviso_em, temp_aviso, habitual)
            VALUES (1, ?, ?, ?, ?)
            """,
            (
                estado.abaixo_desde.isoformat(),
                estado.aviso_em.isoformat() if estado.aviso_em else None,
                estado.temp_aviso,
                estado.habitual,
            ),
        )


def _apagar() -> None:
    with db.ligar() as con:
        con.execute("DELETE FROM estado_temperatura")
