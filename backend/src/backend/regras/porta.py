"""US08 (porta esquecida aberta) e US12 (porta ou janela aberta com a divisão a arrefecer).

Cada abertura (a porta da rua e cada janela, pelo papel no inventário, backend.inventario) tem o
seu estado. Por cada vez que abre há no máximo um aviso, que muda em vez de se repetir:
- a divisão da abertura desce PORTA_QUEDA_GRAUS (2 °C) desde que abriu: aviso de eficiência (US12).
  Se há sensores de temperatura noutras divisões, a divisão tem de descer pelo menos
  PORTA_DIFERENCA_GRAUS (1 °C) mais do que elas: se a casa toda arrefece ao mesmo tempo, o frio
  não vem da abertura e a casa não avisa. Sem sensores noutras divisões, não há comparação;
- só a porta da rua: continua aberta PORTA_MINUTOS (5 min) e o aviso passa a segurança (US08), ou
  já nasce de segurança se a sala ainda não desceu. Uma janela aberta não é uma questão de
  segurança: fica na US12;
- a abertura fecha depois do aviso: `Resolucao` com a hora ("a porta fechou às 14:12",
  "a janela do quarto fechou às 14:12").

A temperatura de uma divisão é a média dos sensores dessa divisão nessa volta. Uma abertura numa
divisão sem sensor de temperatura não chega à US12.

O ciclo identifica o aviso pela US, por isso há no máximo um aviso de cada US de cada vez. A US
com que o aviso nasce fica até ao fim da abertura (se foi a US12, continua US12 mesmo depois de
passar a segurança). Uma segunda abertura que pede uma US já ocupada espera que a primeira feche.
Enquanto o problema dura, a regra devolve o desvio em todas as voltas, sempre com o mesmo texto
(só muda quando o aviso muda), para o ciclo não o republicar a cada leitura.

O que a regra lembra entre voltas fica na tabela `estado_aberturas`, uma linha por abertura. Uma
volta sem leitura de uma abertura, ou com um valor que não é `alarm` nem `normal`, conta como a
última leitura conhecida: uma falha do MCP não resolve nem esquece nada.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from statistics import fmean

from backend import db, inventario
from backend.formatos import Contexto, Desvio, Leitura, Resolucao

from ._comum import com_fuso, decimal, graus, hora, numero

db.esquema(
    """
    DROP TABLE IF EXISTS estado_porta;  -- a versão de uma só porta
    CREATE TABLE IF NOT EXISTS estado_aberturas (
        chave        TEXT PRIMARY KEY,  -- o id do sensor de contacto (ou 'porta', sem id)
        aberta_em    TEXT NOT NULL,     -- ISO 8601, com fuso
        temp_inicial REAL,              -- a temperatura da divisão quando abriu
        ref_inicial  REAL,              -- a das outras divisões
        queda        REAL,              -- quanto a divisão desceu quando passou o limite (fica fixa)
        temp_queda   REAL,              -- a temperatura nesse momento
        ref_queda    REAL,              -- quanto as outras divisões tinham descido nesse momento
        us           TEXT               -- a US do aviso desta abertura, depois de avisar
    )
    """
)

PAPEIS = (inventario.PORTA_DA_RUA, inventario.JANELA)


@dataclass(frozen=True)
class Estado:
    aberta_em: datetime
    temp_inicial: float | None = None
    ref_inicial: float | None = None
    queda: float | None = None
    temp_queda: float | None = None
    ref_queda: float | None = None
    us: str | None = None


@dataclass(frozen=True)
class Abertura:
    chave: str
    papel: str
    nome: str  # "Janela do quarto"
    divisao: str  # "o quarto"
    lida: str | None  # 'alarm', 'normal' ou None (sem leitura nesta volta)


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio | Resolucao]:
    agora = com_fuso(agora)
    estados = _carregar()
    if any(e.aberta_em > agora for e in estados.values()):
        # Estado de um "futuro" (ex.: um CSV de outro dia corrido contra esta base de dados).
        _apagar()
        estados = {}
    aberturas = _aberturas(leituras)
    temperaturas = _temperaturas(leituras)

    saidas: list[Desvio | Resolucao] = []
    resolvidas: set[str] = set()
    for chave in list(estados):
        abertura = aberturas.get(chave)
        if abertura is None or abertura.lida != "normal":
            continue  # aberta, ou sem leitura: fica como estava
        anterior = estados.pop(chave)
        _apagar(chave)
        if anterior.us:
            saidas.append(Resolucao(anterior.us, f"{_texto_curto(abertura)} fechou às {hora(agora)}", agora))
            resolvidas.add(anterior.us)

    for chave, abertura in aberturas.items():
        if abertura.lida == "alarm" and chave not in estados:
            estados[chave] = Estado(aberta_em=agora)

    ocupadas = {e.us for e in estados.values() if e.us} | resolvidas
    for chave in sorted(estados, key=lambda c: estados[c].aberta_em):
        abertura = aberturas.get(chave) or _sem_leitura(chave)
        estado = _com_temperatura(estados[chave], abertura, temperaturas)
        desvio = None
        seguranca = abertura.papel == inventario.PORTA_DA_RUA and (
            agora - estado.aberta_em >= timedelta(minutes=numero("PORTA_MINUTOS", 5))
        )
        if seguranca or estado.queda is not None:
            us = estado.us or ("US08" if seguranca else "US12")
            if estado.us or us not in ocupadas:
                estado = replace(estado, us=us)
                ocupadas.add(us)
                desvio = _desvio(estado, abertura, us, seguranca)
        estados[chave] = estado
        _guardar(chave, estado)
        if desvio:
            saidas.append(desvio)
    return saidas


def reiniciar() -> None:
    """Esquece o que a regra lembra (para os testes e para correr um CSV de raiz)."""
    _apagar()


def _aberturas(leituras: list[Leitura]) -> dict[str, Abertura]:
    aberturas: dict[str, Abertura] = {}
    for l in leituras:
        if l.dispositivo != "porta" or l.tipo != "sensorState":
            continue
        d = inventario.de(l)
        if d.papel in PAPEIS:
            lida = l.valor if l.valor in ("alarm", "normal") else None
            aberturas[d.chave] = Abertura(d.chave, d.papel, d.nome, d.divisao, lida)
    return aberturas


def _sem_leitura(chave: str) -> Abertura:
    """Uma abertura que não deu leitura nesta volta: o que o inventário diz dela."""
    d = inventario.de(Leitura("porta", "sensorState", "", datetime.min, "" if chave == "porta" else chave))
    return Abertura(d.chave, d.papel, d.nome, d.divisao, None)


def _temperaturas(leituras: list[Leitura]) -> dict[str, float]:
    """A temperatura média de cada divisão nesta volta."""
    por_divisao: dict[str, list[float]] = {}
    for l in leituras:
        if l.dispositivo == "temperatura" and l.tipo == "temperatureValue" and _e_numero(l.valor):
            por_divisao.setdefault(inventario.de(l).divisao, []).append(float(l.valor))
    return {divisao: fmean(valores) for divisao, valores in por_divisao.items()}


def _e_numero(valor: object) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _com_temperatura(estado: Estado, abertura: Abertura, temperaturas: dict[str, float]) -> Estado:
    """Guarda as temperaturas iniciais e, uma só vez, a descida que passou o limite."""
    temperatura = temperaturas.get(abertura.divisao)
    outras = [t for divisao, t in temperaturas.items() if divisao != abertura.divisao]
    referencia = fmean(outras) if outras else None
    if estado.ref_inicial is None and referencia is not None:
        estado = replace(estado, ref_inicial=referencia)
    if temperatura is None:
        return estado
    if estado.temp_inicial is None:
        return replace(estado, temp_inicial=temperatura)
    if estado.queda is not None:
        return estado
    queda = round(estado.temp_inicial - temperatura, 1)
    if queda < numero("PORTA_QUEDA_GRAUS", 2):
        return estado
    ref_queda = None
    if estado.ref_inicial is not None and referencia is not None:
        ref_queda = round(estado.ref_inicial - referencia, 1)
        if queda - ref_queda < numero("PORTA_DIFERENCA_GRAUS", 1):
            return estado  # a casa toda está a arrefecer: não é da abertura
    return replace(estado, queda=queda, temp_queda=temperatura, ref_queda=ref_queda)


def _texto_curto(abertura: Abertura) -> str:
    """'a porta' (a da rua) ou 'a janela do quarto'."""
    return "a porta" if abertura.papel == inventario.PORTA_DA_RUA else f"a {_minuscula(abertura.nome)}"


def _minuscula(texto: str) -> str:
    return texto[:1].lower() + texto[1:]


def _resto_da_casa(estado: Estado) -> str:
    if estado.ref_queda is None:
        return ""
    if estado.ref_queda <= 0:
        return " O resto da casa não desceu."
    return f" O resto da casa desceu só {graus(estado.ref_queda)}."


def _desvio(estado: Estado, abertura: Abertura, us: str, seguranca: bool) -> Desvio:
    # Os sensores de contacto são portas e janelas: "A porta da rua", "A janela do quarto".
    nome = f"A {_minuscula(abertura.nome)}"
    desde = hora(estado.aberta_em)
    if not seguranca:
        # Só há aviso antes dos cinco minutos se a divisão já desceu, e a descida guarda as três.
        assert estado.queda is not None and estado.temp_inicial is not None and estado.temp_queda is not None
        resumo = (
            f"{nome} está aberta desde as {desde} e {abertura.divisao} já desceu {graus(estado.queda)} "
            f"(de {graus(estado.temp_inicial)} para {graus(estado.temp_queda)})."
        )
        return Desvio(us=us, classe="eficiencia", resumo=resumo + _resto_da_casa(estado), habitual=None)
    minutos = numero("PORTA_MINUTOS", 5)
    unidade = "minuto" if minutos == 1 else "minutos"
    resumo = f"{nome} está aberta há mais de {decimal(minutos)} {unidade}, desde as {desde}"
    if estado.queda is not None:
        resumo += f", e {abertura.divisao} já desceu {graus(estado.queda)}." + _resto_da_casa(estado)
    else:
        resumo += "."
    return Desvio(us=us, classe="seguranca", resumo=resumo, habitual=None)


def _carregar() -> dict[str, Estado]:
    with db.ligar() as con:
        linhas = con.execute("SELECT * FROM estado_aberturas").fetchall()
    return {
        linha["chave"]: Estado(
            aberta_em=com_fuso(datetime.fromisoformat(linha["aberta_em"])),
            temp_inicial=linha["temp_inicial"],
            ref_inicial=linha["ref_inicial"],
            queda=linha["queda"],
            temp_queda=linha["temp_queda"],
            ref_queda=linha["ref_queda"],
            us=linha["us"],
        )
        for linha in linhas
    }


def _guardar(chave: str, estado: Estado) -> None:
    with db.ligar() as con:
        con.execute(
            """
            INSERT OR REPLACE INTO estado_aberturas
                (chave, aberta_em, temp_inicial, ref_inicial, queda, temp_queda, ref_queda, us)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                chave, estado.aberta_em.isoformat(), estado.temp_inicial, estado.ref_inicial,
                estado.queda, estado.temp_queda, estado.ref_queda, estado.us,
            ),
        )


def _apagar(chave: str | None = None) -> None:
    with db.ligar() as con:
        if chave is None:
            con.execute("DELETE FROM estado_aberturas")
        else:
            con.execute("DELETE FROM estado_aberturas WHERE chave = ?", (chave,))
