"""US11: a luz está acesa há demasiado tempo e a pessoa saiu de casa depois de ela ser acesa.

Um sensor de porta não distingue entrar de sair, por isso a casa usa as câmaras (backend.saida):
a porta da rua abre e, nos SAIDA_MINUTOS seguintes, nenhuma câmara interior vê movimento. A casa
assume então que a pessoa saiu, mas pergunta ("ainda estão a usar?") em vez de afirmar. A ação de
apagar é a da US03.

- A luz conta como acesa desde a primeira volta em que a casa a vê acesa.
- O desvio aparece quando a luz está acesa há LUZ_HORAS (5 h; na demo pode ser menos, por exemplo
  LUZ_HORAS=0.05) e a pessoa saiu depois de a luz acender. Dura enquanto a luz estiver acesa,
  sempre com o mesmo texto, para o ciclo não o republicar a cada volta. Quando a luz apaga, deixa
  de aparecer e o ciclo resolve a anomalia.
- A câmara da divisão da lâmpada: movimento lá depois da saída quer dizer que alguém está a usar a
  luz. A saída deixa de contar e, se já tinha avisado, resolve-se ("houve movimento na sala às
  19:20"). O movimento noutras divisões não conta.
- Sem nenhuma câmara interior a comunicar nesta volta, a casa não sabe se a pessoa saiu e faz o
  que fazia antes: basta a porta da rua abrir e fechar depois de a luz acender. Uma porta que já
  estava aberta quando a luz acendeu não conta.

Cada lâmpada tem o seu estado: acende e apaga sozinha, e a saída conta para todas as que estavam
acesas. O ciclo identifica o aviso pela US, por isso há no máximo um aviso da US11 de cada vez:
fica com a lâmpada que passou primeiro a merecê-lo (a acesa há mais tempo, se forem várias na mesma
volta), e as outras esperam que esse acabe. O desvio leva o id dessa lâmpada (Desvio.dispositivo),
para a ação "apagar a luz" (US03) apagar essa e não outra. Na volta em que o aviso acaba, nenhuma
outra lâmpada avisa: o ciclo tem de fechar a anomalia antes de abrir outra.

O que a regra lembra entre voltas fica na tabela `estado_lampadas`, uma linha por lâmpada acesa (a
janela da saída a meio fica só em memória). Uma volta sem leitura de uma lâmpada, ou com um valor
que não é `on` nem `off`, conta como a última leitura conhecida: uma falha do MCP não resolve nem
esquece nada.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from backend import db, inventario, saida
from backend.formatos import Contexto, Desvio, Leitura, Resolucao

from ._comum import com_fuso, hora, numero

db.esquema(
    """
    DROP TABLE IF EXISTS estado_luz;   -- a versão sem as câmaras
    DROP TABLE IF EXISTS estado_us11;  -- a versão com uma só lâmpada
    CREATE TABLE IF NOT EXISTS estado_lampadas (
        chave       TEXT PRIMARY KEY,  -- o id da lâmpada no MCP (ou 'lampada', sem id)
        id          TEXT NOT NULL,     -- o id do MCP ('' sem id), para a ação da US03
        acesa_desde TEXT NOT NULL,     -- ISO 8601, com fuso
        porta       TEXT,              -- a última leitura da porta da rua: 'alarm', 'normal' ou NULL
        abriu_em    TEXT,              -- sem câmaras: a porta abriu depois de a luz acender
        fechou_em   TEXT,              -- e voltou a fechar
        saiu_em     TEXT,              -- a pessoa saiu (a hora a que a porta abriu)
        avisada     INTEGER NOT NULL   -- 1: é a lâmpada do aviso em curso
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
    saiu_em: datetime | None = None
    id: str = ""  # o id do MCP da lâmpada
    avisada: bool = False


_vigia = saida.Vigia()


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio | Resolucao]:
    agora = com_fuso(agora)
    visto = _vigia.ver(leituras, agora)  # todas as voltas, mesmo com as luzes apagadas
    estados = _carregar()
    for chave in [c for c, e in estados.items() if e.acesa_desde > agora]:
        # Estado de um "futuro" (ex.: um CSV de outro dia corrido contra esta base de dados).
        del estados[chave]
        _apagar(chave)

    portas = inventario.com_papel(leituras, "porta", "sensorState", inventario.PORTA_DA_RUA)
    porta = portas[-1].valor if portas else None
    porta = porta if porta in ("alarm", "normal") else None

    acabou = False  # o aviso em curso acabou nesta volta
    novas: set[str] = set()
    for chave, lampada in _lampadas(leituras).items():
        if lampada.valor == "off" and chave in estados:
            acabou = acabou or estados[chave].avisada
            del estados[chave]
            _apagar(chave)
        elif lampada.valor == "on" and chave not in estados:
            # Acabou de acender: a porta como está agora não conta como "abriu depois".
            estados[chave] = Estado(acesa_desde=agora, porta=porta, id=lampada.id)
            _guardar(chave, estados[chave])
            novas.add(chave)
    if not estados:
        return []
    _horas()  # um LUZ_HORAS inválido falha logo, não só cinco horas depois

    camaras = bool(inventario.com_papel(leituras, "camara", "motionDetected", inventario.INTERIOR))
    aviso: Desvio | None = None
    resolucao: Resolucao | None = None
    for chave, estado in estados.items():
        if chave in novas:
            continue
        antes = _em_aviso(estado, camaras, agora)
        estado = _com_porta(estado, porta, agora)
        if visto.saiu is not None and visto.saiu >= estado.acesa_desde:
            estado = replace(estado, saiu_em=visto.saiu)
        divisao = _lampada(estado).divisao
        na_divisao = [m for m in visto.movimentos if m.divisao == divisao]
        if estado.saiu_em is not None and na_divisao:
            estado = replace(estado, saiu_em=None)  # alguém está a usar a luz
        if estado.avisada:
            aviso = _desvio(estado, camaras, agora)
            if aviso is None:
                estado, acabou = replace(estado, avisada=False), True
                if antes and na_divisao:
                    texto = f"houve movimento {inventario.com_preposicao('em', divisao)} às {hora(na_divisao[-1].em)}"
                    resolucao = Resolucao("US11", texto, agora)
        estados[chave] = estado
        _guardar(chave, estado)

    if acabou:
        return [resolucao] if resolucao else []
    if aviso is not None:
        return [aviso]
    for chave, estado in sorted(estados.items(), key=lambda par: par[1].acesa_desde):
        if chave not in novas and (desvio := _desvio(estado, camaras, agora)):
            _guardar(chave, replace(estado, avisada=True))
            return [desvio]
    return []


def reiniciar() -> None:
    """Esquece o que a regra lembra (para os testes e para correr um CSV de raiz)."""
    global _vigia
    _vigia = saida.Vigia()
    _apagar()


def _lampadas(leituras: list[Leitura]) -> dict[str, Leitura]:
    """A leitura mais recente de cada lâmpada nesta volta (as que não vieram ficam de fora)."""
    return {
        inventario.chave(l): l for l in leituras if l.dispositivo == "lampada" and l.tipo == "power"
    }


def _lampada(estado: Estado) -> inventario.Dispositivo:
    """O que o inventário diz da lâmpada deste estado (o nome, a divisão)."""
    return inventario.de(Leitura("lampada", "power", "", datetime.min, estado.id))


def _em_aviso(estado: Estado, camaras: bool, agora: datetime) -> bool:
    if agora - estado.acesa_desde < timedelta(hours=_horas()):
        return False
    return estado.saiu_em is not None or (not camaras and estado.fechou_em is not None)


def _desvio(estado: Estado, camaras: bool, agora: datetime) -> Desvio | None:
    if not _em_aviso(estado, camaras, agora):
        return None
    nome = _lampada(estado).nome
    inicio = (
        f"A {nome[:1].lower()}{nome[1:]} está acesa desde as {estado.acesa_desde:%H:%M}, "
        f"há mais de {_duracao(timedelta(hours=_horas()))}"
    )
    if estado.saiu_em is not None:
        resumo = (
            f"{inicio}, e parece que saíram de casa às {hora(estado.saiu_em)}: a porta da rua abriu "
            "e as câmaras não viram ninguém a seguir."
        )
    else:
        assert estado.fechou_em is not None
        resumo = f"{inicio}, e a porta abriu e fechou depois disso (fechou às {estado.fechou_em:%H:%M})."
    return Desvio(us="US11", classe="eficiencia", resumo=resumo, habitual=None, dispositivo=estado.id)


def _com_porta(estado: Estado, porta: str | None, agora: datetime) -> Estado:
    if porta is None:
        return estado
    if porta == "alarm" and estado.porta != "alarm" and estado.abriu_em is None:
        estado = replace(estado, abriu_em=agora)
    elif porta == "normal" and estado.abriu_em is not None and estado.fechou_em is None:
        estado = replace(estado, fechou_em=agora)
    return replace(estado, porta=porta)


def _horas() -> float:
    return numero("LUZ_HORAS", HORAS_POR_OMISSAO)


def _duracao(td: timedelta) -> str:
    """'5 h', '1 h 30 min', '3 min'."""
    h, m = divmod(round(td.total_seconds() / 60), 60)
    if h and m:
        return f"{h} h {m} min"
    return f"{h} h" if h else f"{m} min"


def _carregar() -> dict[str, Estado]:
    with db.ligar() as con:
        linhas = con.execute("SELECT * FROM estado_lampadas").fetchall()
    data = lambda texto: com_fuso(datetime.fromisoformat(texto)) if texto else None  # noqa: E731
    return {
        linha["chave"]: Estado(
            acesa_desde=data(linha["acesa_desde"]),
            porta=linha["porta"],
            abriu_em=data(linha["abriu_em"]),
            fechou_em=data(linha["fechou_em"]),
            saiu_em=data(linha["saiu_em"]),
            id=linha["id"],
            avisada=bool(linha["avisada"]),
        )
        for linha in linhas
    }


def _guardar(chave: str, estado: Estado) -> None:
    iso = lambda momento: momento.isoformat() if momento else None  # noqa: E731
    with db.ligar() as con:
        con.execute(
            "INSERT OR REPLACE INTO estado_lampadas"
            " (chave, id, acesa_desde, porta, abriu_em, fechou_em, saiu_em, avisada)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                chave, estado.id, iso(estado.acesa_desde), estado.porta, iso(estado.abriu_em),
                iso(estado.fechou_em), iso(estado.saiu_em), int(estado.avisada),
            ),
        )


def _apagar(chave: str | None = None) -> None:
    with db.ligar() as con:
        if chave is None:
            con.execute("DELETE FROM estado_lampadas")
        else:
            con.execute("DELETE FROM estado_lampadas WHERE chave = ?", (chave,))
