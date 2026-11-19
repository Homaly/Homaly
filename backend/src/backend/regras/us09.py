"""US09: a casa não vê sinais de vida (Bem-estar e rotina).

Um sinal de vida é uma mudança que só acontece com alguém em casa (backend.sinais): movimento
ou som na câmara, a luz ligada, desligada ou com o brilho mudado, a tomada a começar a gastar,
a porta a abrir. Uma mudança que a própria casa mandou fazer (US03, dispositivos.comandado_ha_pouco)
não é um sinal: a casa apagar a luz não resolve o aviso.

Dois casos, com o habitual calculado do histórico (backend.habitual):
- Manhã sem atividade: ainda não houve nenhum sinal hoje à hora limite (o primeiro sinal habitual
  desse tipo de dia mais MARGEM_US09). Só se a casa está a ver desde antes da hora habitual: se o
  ciclo arrancou depois, ou houve um buraco nas leituras, não sabe o que se passou de manhã.
- A atividade parou: hoje já houve sinais, o último não foi a porta (quem abre a porta pode ter
  saído) e passaram US09_HORAS (3) sem nenhum, contando só o tempo nas horas em que o histórico
  mostra atividade (dormir não conta), a uma dessas horas.

O que não conta: um buraco nas leituras de mais de US09_LACUNA_MINUTOS (30) recomeça a
vigilância (o que aconteceu nele não se sabe). Um dispositivo calado não dá sinais nem os tira;
uma volta sem nenhum dispositivo que dê sinais de vida não diz nada (a casa não sabe o que se
passa): não avisa nem resolve.

- Casa vazia (férias ditas à casa): não avisa. Se o aviso já estava ativo, resolve-se com esse
  motivo ("a casa ficou vazia…"), não "sozinha".
- "Vou ficar em casa" não cala a regra: é com a pessoa em casa que uma queda pode acontecer.
- O desvio dura até haver um sinal, mesmo depois da meia-noite, sempre com o mesmo resumo (para o
  ciclo não o republicar); o sinal resolve-o com "movimento na câmara às 11:05" (e avisos.publicar
  informa o contacto externo).

O estado (o último sinal, desde quando a casa vigia, a última leitura e o desvio em curso) fica na
tabela `estado_us09`: depois de um reinício a regra volta a ver o mesmo desvio e o ciclo, que o
reconstruiu, não avisa outra vez. Os valores anteriores de cada dispositivo ficam só em memória:
depois de um reinício, a primeira volta é o ponto de partida.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from backend import db, dispositivos, habitual, sinais
from backend.formatos import Contexto, Desvio, Leitura, Resolucao
from backend.regras import casa_vazia, ferias_agora
from backend.sinais import Sinal

from ._comum import com_fuso, hora, numero

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS estado_us09 (
        id    INTEGER PRIMARY KEY CHECK (id = 1),
        dados TEXT NOT NULL  -- JSON do Estado, com as datas em ISO 8601 com fuso
    )
    """
)


def horas_sem_sinais() -> timedelta:
    return timedelta(hours=numero("US09_HORAS", 3))


def lacuna() -> timedelta:
    return timedelta(minutes=numero("US09_LACUNA_MINUTOS", 30))


@dataclass(frozen=True)
class Estado:
    ultimo: Sinal | None = None  # o último sinal de vida visto
    vigia_desde: datetime | None = None  # desde quando a casa lê sem buracos
    lida_em: datetime | None = None  # a última volta com dispositivos que dão sinais
    pendente: Desvio | None = None  # o desvio em curso, até haver um sinal


def _comandado(dispositivo: str, tipo: str) -> bool:
    return dispositivos.comandado_ha_pouco(dispositivo, tipo)


_detetor = sinais.Detetor(comandado=_comandado)


def reiniciar() -> None:
    """Esquece o que a regra lembra (para os testes e para correr um CSV de raiz)."""
    global _detetor
    _detetor = sinais.Detetor(comandado=_comandado)
    _apagar()


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio | Resolucao]:
    momento = com_fuso(agora)
    estado = _carregar()
    if estado.lida_em is not None and estado.lida_em > momento:
        # Estado de um "futuro" (ex.: um CSV de outro dia corrido contra esta base de dados).
        _apagar()
        estado = Estado()

    if not sinais.comunica(leituras):  # a casa não sabe nada
        return [estado.pendente] if estado.pendente else []

    if estado.lida_em is None or momento - estado.lida_em > lacuna():
        estado = replace(estado, vigia_desde=momento)  # houve um buraco: o que aconteceu nele não se sabe
    estado = replace(estado, lida_em=momento)

    vistos = _detetor.ver(leituras)
    if vistos:
        # A hora é a do ciclo (o relógio da demo pode estar acelerado), não a da leitura.
        estado = replace(estado, ultimo=replace(vistos[-1], em=momento))
    saidas, pendente = _decidir(estado, bool(vistos), contexto, momento, agora)
    _guardar(replace(estado, pendente=pendente))
    return saidas


def _decidir(
    estado: Estado, houve_sinal: bool, contexto: Contexto, momento: datetime, agora: datetime
) -> tuple[list[Desvio | Resolucao], Desvio | None]:
    """As saídas desta volta e o desvio que fica pendente."""
    pendente = estado.pendente
    if pendente is not None and houve_sinal:
        return [Resolucao("US09", f"{estado.ultimo.descricao} às {hora(momento)}", agora)], None

    if casa_vazia(contexto, agora):
        if pendente is None:
            return [], None
        periodo = ferias_agora(contexto, agora)
        motivo = f" ({periodo.motivo})" if periodo and periodo.motivo else ""
        return [Resolucao("US09", f"a casa ficou vazia{motivo}: já não se espera atividade", agora)], None

    if pendente is not None:
        return [pendente], pendente  # o resumo não muda enquanto dura, mesmo depois da meia-noite

    desvio = _manha_sem_atividade(estado, momento) or _atividade_parou(estado, momento)
    return ([desvio], desvio) if desvio else ([], None)


def _manha_sem_atividade(estado: Estado, agora: datetime) -> Desvio | None:
    h = habitual.padrao()
    limite = h.limite_sem_sinais(agora)
    if limite is None or agora.time() < limite:
        return None
    ultimo = _local(estado.ultimo, agora)
    if ultimo is not None and ultimo.em.date() == agora.date():
        return None  # já houve um sinal hoje
    hora_habitual = datetime.combine(agora.date(), h.primeiro_sinal[habitual.tipo_de_dia(agora)], tzinfo=agora.tzinfo)
    if estado.vigia_desde is None or estado.vigia_desde > hora_habitual:
        return None  # a casa não estava a ver antes da hora habitual

    resumo = f"Ainda não houve nenhum sinal de vida hoje até às {limite:%H:%M}."
    if ultimo is not None:
        ontem = ultimo.em.date() == agora.date() - timedelta(days=1)
        quando = f"{hora(ultimo.em)} de ontem" if ontem else f"{hora(ultimo.em)} de {ultimo.em:%d/%m}"
        resumo += f" O último foi {ultimo.descricao} às {quando}."
    return Desvio(us="US09", classe="bem_estar", resumo=resumo, habitual=h.texto_primeiro_sinal(agora))


def _atividade_parou(estado: Estado, agora: datetime) -> Desvio | None:
    h = habitual.padrao()
    ultimo = _local(estado.ultimo, agora)
    if ultimo is None or ultimo.em.date() != agora.date() or ultimo.dispositivo == "porta":
        return None  # sem sinais hoje, ou quem abriu a porta pode ter saído
    if not h.com_atividade(agora) or estado.vigia_desde is None:
        return None
    horas = horas_sem_sinais()
    if h.tempo_ativo(max(ultimo.em, estado.vigia_desde), agora) < horas:
        return None
    return Desvio(
        us="US09",
        classe="bem_estar",
        resumo=(
            f"O último sinal de vida foi {ultimo.descricao} às {hora(ultimo.em)} e, desde então, "
            f"passaram {habitual.duracao(horas)} sem nenhum, a horas em que costuma haver atividade."
        ),
        habitual=h.texto_atividade(agora),
    )


def _local(sinal: Sinal | None, agora: datetime) -> Sinal | None:
    """O sinal na hora local de agora (o guardado pode ter outro offset, de antes da mudança da hora)."""
    return replace(sinal, em=sinal.em.astimezone(agora.tzinfo)) if sinal else None


def _iso(momento: datetime | None) -> str | None:
    return momento.isoformat() if momento else None


def _data(texto: str | None) -> datetime | None:
    return datetime.fromisoformat(texto) if texto else None


def _para_json(estado: Estado) -> str:
    u, p = estado.ultimo, estado.pendente
    return json.dumps(
        {
            "ultimo": {"dispositivo": u.dispositivo, "descricao": u.descricao, "em": _iso(u.em)} if u else None,
            "vigia_desde": _iso(estado.vigia_desde),
            "lida_em": _iso(estado.lida_em),
            "pendente": {"classe": p.classe, "resumo": p.resumo, "habitual": p.habitual} if p else None,
        },
        ensure_ascii=False,
    )


def _de_json(texto: str) -> Estado:
    d = json.loads(texto)
    u, p = d["ultimo"], d["pendente"]
    return Estado(
        ultimo=Sinal(u["dispositivo"], u["descricao"], _data(u["em"])) if u else None,
        vigia_desde=_data(d["vigia_desde"]),
        lida_em=_data(d["lida_em"]),
        pendente=Desvio(us="US09", classe=p["classe"], resumo=p["resumo"], habitual=p["habitual"]) if p else None,
    )


def _carregar() -> Estado:
    with db.ligar() as con:
        linha = con.execute("SELECT dados FROM estado_us09 WHERE id = 1").fetchone()
    return _de_json(linha["dados"]) if linha else Estado()


def _guardar(estado: Estado) -> None:
    with db.ligar() as con:
        con.execute("INSERT OR REPLACE INTO estado_us09 (id, dados) VALUES (1, ?)", (_para_json(estado),))


def _apagar() -> None:
    with db.ligar() as con:
        con.execute("DELETE FROM estado_us09")
