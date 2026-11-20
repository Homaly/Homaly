"""O inventário da casa: o nome e a divisão de cada dispositivo, e daí o papel que tem.

Para cada dispositivo, por esta ordem:

1. `dados/dispositivos.csv` (ou o ficheiro em DISPOSITIVOS_CSV), com as colunas `id,nome,divisao`.
   Tem os dispositivos do kit, com os nomes e as divisões que a equipa escolheu, e os dispositivos
   simulados da demo (ids inventados, que as leituras injetadas em `/dev/leituras` trazem);
2. o que o MCP diz dele: o `get_home_devices` traz o `name` e o `roomName` de cada dispositivo, e
   `dispositivos.ler()` regista-os aqui (`registar()`) a cada leitura, só em memória. Um MCP com
   outra casa funciona sem escrever nada à mão. Só se usa o que diz alguma coisa, campo a campo:
   um nome de fábrica ("Contact sensor", "Light 2") conta como não preenchido, e uma divisão
   também, se não for uma divisão conhecida ("Hack 4"). A divisão conhecida ganha o artigo
   ("Sala" -> "a sala"). É assim que o kit da Altice, com os nomes de fábrica e "Hack 4" em
   todos, fica com os valores por omissão, como no MVP;
   Antes disso, a IA (backend.ia.dispositivos) lê os dispositivos do MCP que não estão no CSV e
   diz o nome em português, a divisão e o papel de cada um (`classificar()`, chamado por
   `dispositivos.ler()` quando há dispositivos novos ou mudados). Fica guardado na base de dados,
   e o que a IA disse ganha às regras deste módulo, campo a campo. O que ela não identifica, ou
   sem modelo de IA (IA_FORNECEDOR=falso), fica com as regras;
3. os valores por omissão do tipo: na sala, a porta da rua, uma câmara interior. É a casa do kit,
   que tem um dispositivo de cada tipo, todos na mesma divisão (as leituras sem `id`, como as dos
   CSV de teste, ficam sempre aqui).

O papel, o que o dispositivo faz na casa, deduz-se do tipo, do nome e da divisão (`papel()`), sem
coluna própria:

- sensor de contacto (`porta`): a porta da rua (`porta_da_rua`, conta para entrar e sair de casa)
  ou outra abertura (`janela`: uma janela, a porta da varanda, que não é entrar nem sair). Pelo
  nome: "janela" é uma janela; "porta da rua", "porta de entrada", "porta principal" é a porta da
  rua; "porta" com outra coisa ("porta da varanda") é outra abertura. Na entrada ou no hall, é a
  porta da rua. Um nome genérico ("Contact sensor", "Porta") noutra divisão é outra abertura, a não
  ser que nenhum sensor da casa que o MCP devolve seja claramente a porta da rua: então os
  genéricos contam como a porta da rua (a casa do kit, com um "Contact sensor" em "Hack 4");
- câmara: exterior (`exterior`, vê a rua e não diz se há alguém em casa) se o nome ou a divisão
  falam de fora ("rua", "jardim", "garagem", "entrada de veículos", "varanda"...), senão interior
  (`interior`). "Entrada" sozinha é o hall, dentro de casa;
- os outros tipos não têm papel.
"""

from __future__ import annotations

import csv
import logging
import os
import re
import threading
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from backend.formatos import Leitura
from backend.ia import dispositivos as ia_dispositivos
from backend.ia.modelo import Modelo

registo = logging.getLogger(__name__)

INVENTARIO = Path(__file__).resolve().parents[2] / "dados" / "dispositivos.csv"

DIVISAO_POR_OMISSAO = "a sala"
PAPEL_POR_OMISSAO = {"porta": "porta_da_rua", "camara": "interior"}
NOME_POR_OMISSAO = {
    "porta": "Porta da rua",
    "lampada": "Luz da sala",
    "tomada": "Tomada",
    "camara": "Câmara da sala",
    "temperatura": "Sensor de temperatura da sala",
    "agua": "Válvula da água",
}

# O nome de um dispositivo registado sem nome que diga alguma coisa: a base mais a divisão
# ("Câmara do quarto"). O sensor de contacto vai pelo papel ("Porta da rua", "Janela do quarto").
_BASE_DO_NOME = {
    "lampada": "Luz", "camara": "Câmara", "temperatura": "Sensor de temperatura", "tomada": "Tomada",
    "fumo": "Detetor de fumo",
}
_NOME_FIXO = {"hub": "Hub de segurança", "agua": "Válvula da água"}

PORTA_DA_RUA = "porta_da_rua"
JANELA = "janela"  # qualquer abertura que não é a porta da rua (uma janela, a porta da varanda)
INTERIOR = "interior"
EXTERIOR = "exterior"

# As palavras (sem acentos, em minúsculas) com que se deduz o papel.
_PORTA_DA_RUA = {"rua", "entrada", "principal", "frente", "exterior"}  # "porta da rua", "porta de entrada"
_ENTRADA = {"entrada", "hall", "vestibulo", "atrio"}  # a divisão da porta da rua
_FORA = {
    "exterior", "fora", "rua", "jardim", "quintal", "patio", "terraco", "varanda", "alpendre",
    "garagem", "veiculos", "fachada", "piscina", "logradouro", "portao",
}
# O que não acrescenta nada a "porta": "Porta da rua" tem "rua"; "Porta" sozinha não diz qual é.
_VAZIAS = {"a", "o", "as", "os", "da", "do", "das", "dos", "de", "sensor", "contacto", "contact", "porta"}

# As palavras dos nomes de fábrica (sem acentos, em minúsculas): um nome do MCP só com estas, e
# números, não diz nada ("Contact sensor", "Light 2"). "door" e "window" ficam de fora: dizem o papel.
_GENERICAS = {
    "contact", "sensor", "camera", "light", "bulb", "lamp", "plug", "socket", "temperature",
    "humidity", "smoke", "security", "hub", "gateway", "device", "motion", "smart", "wifi",
}

# O artigo das divisões conhecidas, pela primeira palavra (sem acentos, em minúsculas).
_ARTIGOS = {
    "sala": "a", "quarto": "o", "cozinha": "a", "casa": "a", "wc": "o", "escritorio": "o",
    "hall": "o", "corredor": "o", "entrada": "a", "garagem": "a", "varanda": "a", "jardim": "o",
    "sotao": "o", "cave": "a", "despensa": "a", "lavandaria": "a", "marquise": "a", "quintal": "o",
    "terraco": "o", "suite": "a", "patio": "o", "arrecadacao": "a", "arrumos": "os", "vestibulo": "o",
    "atrio": "o", "biblioteca": "a", "ginasio": "o", "copa": "a", "closet": "o", "alpendre": "o",
}


@dataclass(frozen=True)
class Dispositivo:
    chave: str  # o id do MCP, ou o tipo para uma leitura sem id
    nome: str  # "Janela do quarto"
    divisao: str  # "o quarto"
    papel: str  # "janela", "porta_da_rua", "interior", "exterior" ou ""


_trinco = threading.Lock()
_entradas: dict[str, dict[str, str]] | None = None
_do_mcp: dict[str, dict[str, str]] = {}  # id -> {"tipo", "nome", "divisao"}, da última leitura do MCP
_ha_porta_da_rua = True  # algum sensor da casa do MCP é claramente a porta da rua (ver papel())
_anunciados: set[str] = set()  # os ids do MCP que já foram para o log
_casa_mcp: list[dict[str, str]] = []  # o que o MCP disse na última leitura (`mapa.descricoes`)
_da_ia: dict[str, dict[str, str]] = {}  # id -> {"nome", "divisao", "papel"}, para a casa de agora
_guardadas: dict[str, tuple[str, dict[str, str]]] | None = None  # a tabela dispositivos_ia
_por_classificar: list[str] = []  # os ids que a IA ainda não viu (ou que o MCP mudou)
_tentadas: set[str] = set()  # as assinaturas que já se pediram à IA neste processo


def configurar(entradas: list[dict[str, str]] | None) -> None:
    """Escolhe o inventário (nos testes); None volta a ler o ficheiro na próxima consulta."""
    global _entradas
    with _trinco:
        _entradas = None if entradas is None else {e["id"]: e for e in entradas}


def esquecer_mcp() -> None:
    """Esquece o que o MCP e a IA disseram (nos testes; a tabela fica)."""
    global _do_mcp, _ha_porta_da_rua, _casa_mcp, _da_ia, _guardadas, _por_classificar
    with _trinco:
        _do_mcp, _ha_porta_da_rua, _casa_mcp, _da_ia, _guardadas, _por_classificar = {}, True, [], {}, None, []
        _anunciados.clear()
        _tentadas.clear()


def registar(descricoes: list[dict[str, str]]) -> None:
    """Guarda o que o MCP diz dos dispositivos da casa (`mapa.descricoes`): tipo, nome e divisão.

    Substitui o registo anterior e junta-lhe o que a IA já disse de cada um. Os que a IA ainda não
    viu ficam em `por_classificar()`. Um dispositivo que não está no CSV vai uma vez para o log,
    com o que a casa deduziu dele (depois de a IA o ver, se ainda está à espera dela).
    """
    global _do_mcp, _ha_porta_da_rua, _casa_mcp, _da_ia, _guardadas, _por_classificar
    csv_ = _carregar()
    originais = {d["id"]: d for d in descricoes if d.get("id")}
    novos = {
        i: {"tipo": d.get("tipo", ""), "nome": _nome_do_mcp(d.get("nome") or ""), "divisao": _com_artigo(d.get("divisao") or "")}
        for i, d in originais.items()
    }
    guardadas = _guardadas if _guardadas is not None else ia_dispositivos.carregar()
    da_ia = {
        i: valores
        for i, (assinatura, valores) in guardadas.items()
        if i in originais and assinatura == ia_dispositivos.assinatura(originais[i])
    }
    pendentes = [
        i for i, d in originais.items()
        if i not in csv_ and i not in da_ia and ia_dispositivos.assinatura(d) not in _tentadas
    ]

    def claramente_porta_da_rua(id: str) -> bool:
        if id in csv_:
            entrada = csv_[id]
            return _papel_porta(entrada.get("nome") or "", entrada.get("divisao") or "") == PORTA_DA_RUA
        juntos = _juntar(novos[id], da_ia.get(id))
        return (da_ia.get(id) or {}).get("papel") == PORTA_DA_RUA or _papel_porta(juntos["nome"], juntos["divisao"]) == PORTA_DA_RUA

    ha = not novos or any(claramente_porta_da_rua(i) for i, d in novos.items() if d["tipo"] == "porta")
    with _trinco:
        _do_mcp, _ha_porta_da_rua, _casa_mcp, _da_ia, _guardadas, _por_classificar = (
            novos, ha, list(originais.values()), da_ia, guardadas, pendentes
        )
        anunciar = [i for i in novos if i not in csv_ and i not in pendentes and i not in _anunciados]
        _anunciados.update(anunciar)
    for i in anunciar:
        d = de(Leitura(novos[i]["tipo"], "", "", datetime.min, i))
        nome, divisao = (originais[i].get(c) or "" for c in ("nome", "divisao"))
        no_mcp = lambda usado, original: f" (no MCP '{original}')" if original and original != usado else ""  # noqa: E731
        registo.info(
            "dispositivo novo do MCP (%s): %s %s '%s'%s em '%s'%s -> %s",
            "visto pela IA" if i in da_ia else "pelas regras",
            novos[i]["tipo"], i, d.nome, no_mcp(d.nome, nome), d.divisao, no_mcp(d.divisao, divisao),
            d.papel or "sem papel",
        )


def por_classificar() -> list[str]:
    """Os ids do MCP que a IA ainda não viu, ou que o MCP mudou desde que ela os viu."""
    return list(_por_classificar)


def classificar(modelo: Modelo, agora: datetime | None = None) -> None:
    """Pede à IA o que são os dispositivos em `por_classificar()` e guarda a resposta.

    Cada pedido faz-se uma vez por processo: se a IA falha (ou não há modelo), a casa fica com as
    regras deste módulo até ao próximo arranque, sem perguntar a cada leitura.
    """
    global _guardadas
    ids, casa = por_classificar(), list(_casa_mcp)
    if not ids:
        return
    por_id = {d["id"]: d for d in casa}
    with _trinco:
        _tentadas.update(ia_dispositivos.assinatura(por_id[i]) for i in ids if i in por_id)
    resultado = ia_dispositivos.classificar(casa, ids, modelo)
    if resultado is None:
        registo.info("a IA não classificou %d dispositivo(s) do MCP: ficam as regras do inventário", len(ids))
    else:
        ia_dispositivos.guardar(casa, resultado, agora)
        with _trinco:
            _guardadas = None  # ler de novo a tabela
    registar(casa)  # junta o que a IA disse e escreve no log os que estavam à espera dela


def _juntar(do_mcp: dict[str, str], da_ia: dict[str, str] | None) -> dict[str, str]:
    """O nome e a divisão de um dispositivo do MCP, com o que a IA disse por cima.

    O nome da IA só conta se o MCP deu um nome que diz alguma coisa: a IA não inventa um nome
    para um nome de fábrica ("Light"), e com o kit ficam os nomes por omissão.
    """
    da_ia = da_ia or {}
    nome = (da_ia.get("nome") if do_mcp.get("nome") else "") or do_mcp.get("nome") or ""
    divisao = da_ia.get("divisao") or do_mcp.get("divisao") or ""
    return {"nome": nome, "divisao": divisao}


def registados() -> dict[str, str]:
    """Os dispositivos que o MCP devolveu na última leitura, com o tipo: {id: "porta", ...}."""
    return {i: d["tipo"] for i, d in _do_mcp.items()}


def origem(id: str) -> str:
    """De onde vem o que se sabe deste id: "csv", "ia" (o MCP, visto pela IA), "mcp" (o MCP, pelas
    regras) ou "omissao"."""
    if id and id in _carregar():
        return "csv"
    if id in _da_ia and any(_da_ia[id].values()):
        return "ia"
    return "mcp" if id in _do_mcp else "omissao"


def _nome_do_mcp(nome: str) -> str:
    """O nome que o MCP dá, ou "" se é um nome de fábrica que não diz nada ("Contact sensor")."""
    nome = nome.strip()
    palavras = _palavras(nome)
    if all(p in _GENERICAS or p.isdigit() for p in palavras):
        return ""
    return nome


def _com_artigo(divisao: str) -> str:
    """"Sala" -> "a sala"; "Quarto principal" -> "o quarto principal"; desconhecida ("Hack 4") ou
    vazia -> a divisão por omissão."""
    divisao = divisao.strip()
    if not divisao:
        return DIVISAO_POR_OMISSAO
    palavras = divisao.split()
    if palavras[0].lower() in ("a", "o", "as", "os"):
        return divisao  # já traz o artigo
    primeira = _palavras(palavras[0])
    artigo = _ARTIGOS.get(next(iter(primeira), "")) if len(primeira) == 1 else None
    return f"{artigo} {divisao.lower()}" if artigo else DIVISAO_POR_OMISSAO


def _carregar() -> dict[str, dict[str, str]]:
    global _entradas
    with _trinco:
        if _entradas is None:
            caminho = Path(os.environ.get("DISPOSITIVOS_CSV", "").strip() or INVENTARIO)
            if caminho.exists():
                with open(caminho, newline="", encoding="utf-8") as f:
                    _entradas = {l["id"]: l for l in csv.DictReader(f) if l.get("id")}
            else:
                _entradas = {}
        return _entradas


def de(leitura: Leitura) -> Dispositivo:
    """O dispositivo desta leitura, com o que o inventário diz dele."""
    tipo = leitura.dispositivo
    entrada = _carregar().get(leitura.id) if leitura.id else None
    papel_da_ia = ""
    if entrada is None and leitura.id in _do_mcp:
        da_ia = _da_ia.get(leitura.id)
        entrada = _juntar(_do_mcp[leitura.id], da_ia)
        papel_da_ia = (da_ia or {}).get("papel") or ""
    if not entrada:
        return Dispositivo(
            leitura.id or tipo, NOME_POR_OMISSAO.get(tipo, tipo), DIVISAO_POR_OMISSAO, PAPEL_POR_OMISSAO.get(tipo, "")
        )
    nome = (entrada.get("nome") or "").strip()
    divisao = (entrada.get("divisao") or "").strip() or DIVISAO_POR_OMISSAO
    papel_ = papel_da_ia or papel(tipo, nome, entrada.get("divisao") or "", _ha_porta_da_rua)
    return Dispositivo(leitura.id, nome or _nome_por_omissao(tipo, divisao, papel_), divisao, papel_)


def _nome_por_omissao(tipo: str, divisao: str, papel_: str) -> str:
    """O nome de um dispositivo sem nome que diga alguma coisa: "Luz da sala", "Janela do quarto"."""
    if tipo in _NOME_FIXO:
        return _NOME_FIXO[tipo]
    if tipo == "porta":
        if papel_ == PORTA_DA_RUA:
            return "Porta da rua"
        base = "Janela"
    else:
        base = _BASE_DO_NOME.get(tipo, NOME_POR_OMISSAO.get(tipo, tipo))
    return f"{base} {com_preposicao('de', divisao)}"


def papel(tipo: str, nome: str, divisao: str, ha_porta_da_rua: bool = True) -> str:
    """O papel de um dispositivo, pelo tipo, o nome e a divisão (ver o início do módulo).

    `ha_porta_da_rua` falso (nenhum sensor da casa é claramente a porta da rua): um sensor de
    contacto com um nome genérico conta como a porta da rua.
    """
    if tipo == "porta":
        claro = _papel_porta(nome, divisao)
        if claro is not None:
            return claro
        return PORTA_DA_RUA if not ha_porta_da_rua or not _palavras(divisao) else JANELA
    if tipo == "camara":
        return EXTERIOR if (_palavras(nome) | _palavras(divisao)) & _FORA else INTERIOR
    return ""


def _papel_porta(nome: str, divisao: str) -> str | None:
    """O papel de um sensor de contacto quando o nome ou a divisão o dizem; None se não dizem."""
    nome_ = _palavras(nome)
    if nome_ & {"janela", "janelas", "window"}:
        return JANELA
    if "porta" in nome_:
        if nome_ & _PORTA_DA_RUA:
            return PORTA_DA_RUA
        if nome_ - _VAZIAS:
            return JANELA  # "Porta da varanda": uma abertura que não é entrar nem sair
    if _palavras(divisao) & _ENTRADA:
        return PORTA_DA_RUA
    return None


def _palavras(texto: str) -> set[str]:
    sem_acentos = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return set(re.findall(r"[a-z0-9]+", sem_acentos))


def chave(leitura: Leitura) -> str:
    return leitura.id or leitura.dispositivo


def com_papel(leituras: list[Leitura], dispositivo: str, tipo: str, papel: str) -> list[Leitura]:
    """As leituras de (dispositivo, tipo) dos dispositivos com este papel."""
    return [l for l in leituras if l.dispositivo == dispositivo and l.tipo == tipo and de(l).papel == papel]


def conta_como_casa(leitura: Leitura) -> bool:
    """A leitura vem de um dispositivo que vê o que se passa dentro de casa.

    Fora ficam as câmaras exteriores (vêem quem passa na rua) e as janelas (abrir uma janela não
    é entrar nem sair). Os outros dispositivos contam todos.
    """
    papel = de(leitura).papel
    if leitura.dispositivo == "camara":
        return papel == INTERIOR
    if leitura.dispositivo == "porta":
        return papel == PORTA_DA_RUA
    return True


# Os textos: a divisão vem com o artigo ("a sala"), e as contrações são as do português.
_CONTRACOES = {("em", "a"): "na", ("em", "o"): "no", ("de", "a"): "da", ("de", "o"): "do",
               ("em", "as"): "nas", ("em", "os"): "nos", ("de", "as"): "das", ("de", "os"): "dos"}


def com_preposicao(preposicao: str, divisao: str) -> str:
    """("em", "a sala") -> "na sala"; ("de", "o quarto") -> "do quarto"."""
    artigo, _, resto = divisao.partition(" ")
    contraida = _CONTRACOES.get((preposicao, artigo.lower()))
    return f"{contraida} {resto}" if contraida and resto else f"{preposicao} {divisao}"
