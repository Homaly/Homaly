"""US11: a luz está acesa há demasiado tempo e a porta abriu e fechou depois de ela ser acesa.

Um sensor de porta não distingue entrar de sair, por isso a casa pergunta ("ainda estão a usar?")
em vez de afirmar que não há ninguém. A ação de apagar é a da US03.

- A luz conta como acesa desde a primeira volta em que a casa a vê acesa.
- "A porta abriu e fechou depois": a porta passa a aberta (`alarm`) com a luz já acesa e depois
  volta a fechada (`normal`). Uma porta que já estava aberta quando a luz acendeu não conta.
- O desvio aparece quando a luz está acesa há LUZ_HORAS (5 h; na demo pode ser menos, por exemplo
  LUZ_HORAS=0.05) e a porta já abriu e fechou. Dura enquanto a luz estiver acesa, sempre com o
  mesmo texto, para o ciclo não o republicar a cada volta. Quando a luz apaga, deixa de aparecer
  e o ciclo resolve a anomalia.

O que a regra lembra entre voltas fica na tabela `estado_luz`. Uma volta sem leitura da lâmpada,
ou com um valor que não é `on` nem `off`, conta como a última leitura conhecida: uma falha do MCP
não resolve nem esquece nada.
"""

import os
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from backend import db
from backend.formatos import Contexto, Desvio, Leitura

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS estado_luz (
        id          INTEGER PRIMARY KEY CHECK (id = 1),  -- só há uma lâmpada
        acesa_desde TEXT NOT NULL,  -- ISO 8601, com fuso
        porta       TEXT,           -- a última leitura da porta: 'alarm', 'normal' ou NULL
        abriu_em    TEXT,           -- a porta abriu depois de a luz acender
        fechou_em   TEXT            -- e voltou a fechar
    )
    """
)

HORAS_POR_OMISSAO = 5.0


@dataclass(frozen=True)
class Estado:
    acesa_desde: datetime
    porta: str | None = None
    abriu_em: datetime | None = None
    fechou_em: datetime | None = None


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio]:
    agora = _com_fuso(agora)
    estado = _carregar()
    if estado is not None and estado.acesa_desde > agora:
        # Estado de um "futuro" (ex.: um CSV de outro dia corrido contra esta base de dados).
        _apagar()
        estado = None

    luz = _ultima(leituras, "lampada", "power")
    porta = _ultima(leituras, "porta", "sensorState")
    porta = porta if porta in ("alarm", "normal") else None

    if luz == "off" or (luz != "on" and estado is None):
        if estado is not None:
            _apagar()
        return []
    if estado is None:
        # A luz acabou de acender: a porta como está agora não conta como "abriu depois".
        estado = Estado(acesa_desde=agora, porta=porta)
    else:
        estado = _com_porta(estado, porta, agora)
    _guardar(estado)

    limite = timedelta(hours=_horas())
    if estado.fechou_em is None or agora - estado.acesa_desde < limite:
        return []
    return [
        Desvio(
            us="US11",
            classe="eficiencia",
            resumo=(
                f"A luz da sala está acesa desde as {estado.acesa_desde:%H:%M}, há mais de "
                f"{_duracao(limite)}, e a porta abriu e fechou depois disso "
                f"(fechou às {estado.fechou_em:%H:%M})."
            ),
            habitual=None,
        )
    ]


def reiniciar() -> None:
    """Esquece o que a regra lembra (para os testes e para correr um CSV de raiz)."""
    _apagar()


def _com_porta(estado: Estado, porta: str | None, agora: datetime) -> Estado:
    if porta is None:
        return estado
    if porta == "alarm" and estado.porta != "alarm" and estado.abriu_em is None:
        estado = replace(estado, abriu_em=agora)
    elif porta == "normal" and estado.abriu_em is not None and estado.fechou_em is None:
        estado = replace(estado, fechou_em=agora)
    return replace(estado, porta=porta)


def _ultima(leituras: list[Leitura], dispositivo: str, tipo: str) -> object:
    """O valor mais recente de um dispositivo nesta volta, ou None se não veio."""
    valores = [l.valor for l in leituras if l.dispositivo == dispositivo and l.tipo == tipo]
    return valores[-1] if valores else None


def _horas() -> float:
    texto = os.environ.get("LUZ_HORAS", "").strip()
    if not texto:
        return HORAS_POR_OMISSAO
    try:
        return float(texto)
    except ValueError:
        raise ValueError(f"LUZ_HORAS tem de ser um número, não '{texto}'") from None


def _duracao(td: timedelta) -> str:
    """'5 h', '1 h 30 min', '3 min'."""
    h, m = divmod(round(td.total_seconds() / 60), 60)
    if h and m:
        return f"{h} h {m} min"
    return f"{h} h" if h else f"{m} min"


def _com_fuso(momento: datetime) -> datetime:
    """Uma hora sem fuso é tomada como hora local, como em `contrato.py`."""
    return momento if momento.tzinfo else momento.astimezone()


def _carregar() -> Estado | None:
    with db.ligar() as con:
        linha = con.execute(
            "SELECT acesa_desde, porta, abriu_em, fechou_em FROM estado_luz WHERE id = 1"
        ).fetchone()
    if linha is None:
        return None
    data = lambda texto: datetime.fromisoformat(texto) if texto else None  # noqa: E731
    return Estado(data(linha["acesa_desde"]), linha["porta"], data(linha["abriu_em"]), data(linha["fechou_em"]))


def _guardar(estado: Estado) -> None:
    iso = lambda momento: momento.isoformat() if momento else None  # noqa: E731
    with db.ligar() as con:
        con.execute(
            "INSERT OR REPLACE INTO estado_luz (id, acesa_desde, porta, abriu_em, fechou_em)"
            " VALUES (1, ?, ?, ?, ?)",
            (iso(estado.acesa_desde), estado.porta, iso(estado.abriu_em), iso(estado.fechou_em)),
        )


def _apagar() -> None:
    with db.ligar() as con:
        con.execute("DELETE FROM estado_luz")
