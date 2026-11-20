"""A IA lê os dispositivos que o MCP devolve e diz o que cada um é: o nome, a divisão e o papel.

Corre quando o MCP traz um dispositivo que não está no CSV do inventário, ou quando muda o nome ou
a divisão de um (backend.inventario.classificar, chamado por `dispositivos.ler()`). A IA vê a casa
toda de uma vez, porque o papel de um sensor depende dos outros (qual é a porta da rua?).

O que a IA diz fica na tabela `dispositivos_ia`, com a assinatura do que o MCP dizia nessa altura
(tipo, nome, divisão): se o MCP mudar, a casa volta a perguntar. Só se aceita o que é válido:
um papel que existe para esse tipo, uma divisão com o artigo, um nome curto. O resto conta como
"não identificado", e o inventário usa as suas regras e os valores por omissão.
"""

import json
import logging
from datetime import UTC, datetime

from backend import db
from backend.ia.modelo import Modelo

registo = logging.getLogger(__name__)

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS dispositivos_ia (
        id         TEXT PRIMARY KEY,  -- o id do dispositivo no MCP
        assinatura TEXT NOT NULL,     -- o que o MCP dizia (tipo, nome, divisão), em JSON
        nome       TEXT NOT NULL,     -- '' se a IA não identificou
        divisao    TEXT NOT NULL,     -- com o artigo ('a cozinha'); '' se não identificou
        papel      TEXT NOT NULL,     -- 'porta_da_rua', 'janela', 'interior', 'exterior' ou ''
        em         TEXT NOT NULL      -- ISO 8601 em UTC
    )
    """
)

PAPEIS = {"porta": {"porta_da_rua", "janela"}, "camara": {"interior", "exterior"}}
ARTIGOS = ("a ", "o ", "as ", "os ")
MAX_NOME = 60
MAX_DIVISAO = 40

SISTEMA = """\
És a IA de uma casa ligada. Recebes a lista dos dispositivos da casa, como o servidor da casa os \
descreve (o tipo, o nome e a divisão que alguém lhes deu na app), e dizes o que é cada um, para a \
casa falar deles nos avisos, em português de Portugal. Responde só com JSON, neste formato:
{"dispositivos": [{"id": "...", "nome": "..." | null, "divisao": "..." | null, "papel": "..." | null}]}
Um elemento por cada id em "Classifica estes ids", com o mesmo id.
- "nome": como a casa lhe chama num aviso, curto e em português ("Luz da cozinha", "Janela do \
quarto", "Porta da rua"). null se o nome dado é o nome de fábrica, que não diz o que é nem onde \
está ("Light", "Contact sensor", "Camera", "Plug 2"). Não inventes onde está.
- "divisao": a divisão onde está, em minúsculas (exceto os nomes próprios) e com o artigo definido \
("a cozinha", "o quarto", "a casa de banho", "o quarto da Ana"). null se a divisão dada não é uma divisão de uma casa (um código, o nome da \
casa ou de um evento, como "Hack 4") ou se não vem nenhuma.
- "papel": só para os tipos "porta" e "camara"; null nos outros.
  - "porta" (um sensor de contacto): "porta_da_rua" se é a porta por onde se entra e sai de casa; \
"janela" se é uma janela ou outra abertura (a porta da varanda, da garagem, uma porta interior).
  - "camara": "exterior" se vê a rua, o jardim, a garagem ou a entrada de veículos; "interior" se \
vê o interior da casa (um hall de entrada é interior).
  - null se o nome e a divisão não chegam para saber. Não adivinhes.
"""


def assinatura(descricao: dict[str, str]) -> str:
    """O que o MCP diz de um dispositivo: se mudar, a casa volta a perguntar à IA."""
    return json.dumps([descricao.get(c) or "" for c in ("tipo", "nome", "divisao")], ensure_ascii=False)


def carregar() -> dict[str, tuple[str, dict[str, str]]]:
    """O que a IA disse antes: {id: (assinatura, {"nome", "divisao", "papel"})}."""
    with db.ligar() as con:
        linhas = con.execute("SELECT * FROM dispositivos_ia").fetchall()
    return {
        l["id"]: (l["assinatura"], {"nome": l["nome"], "divisao": l["divisao"], "papel": l["papel"]})
        for l in linhas
    }


def classificar(
    casa: list[dict[str, str]], ids: list[str], modelo: Modelo
) -> dict[str, dict[str, str]] | None:
    """O que a IA diz de cada um de `ids`, já validado ("" no que não identificou).

    `casa` são todos os dispositivos do MCP (`mapa.descricoes`), para o contexto. None se o modelo
    falhou ou não há modelo: a casa tenta de novo no próximo arranque.
    """
    lista = [{c: d.get(c) or "" for c in ("id", "tipo", "nome", "divisao")} for d in casa]
    mensagem = (
        "Os dispositivos da casa:\n"
        + json.dumps(lista, ensure_ascii=False, indent=1)
        + "\n\nClassifica estes ids: "
        + json.dumps(ids)
    )
    resposta = modelo.completar_json(SISTEMA, mensagem)
    if not isinstance(resposta, dict) or not isinstance(resposta.get("dispositivos"), list):
        return None
    tipos = {d["id"]: d.get("tipo") or "" for d in casa if d.get("id")}
    resultado = {i: {"nome": "", "divisao": "", "papel": ""} for i in ids}
    for item in resposta["dispositivos"]:
        if not isinstance(item, dict) or item.get("id") not in resultado:
            continue
        resultado[item["id"]] = _validar(item, tipos.get(item["id"], ""))
    return resultado


def guardar(casa: list[dict[str, str]], resultado: dict[str, dict[str, str]], agora: datetime | None = None) -> None:
    em = (agora or datetime.now(UTC)).astimezone(UTC).isoformat()
    por_id = {d["id"]: d for d in casa if d.get("id")}
    with db.ligar() as con:
        for i, valores in resultado.items():
            con.execute(
                "INSERT OR REPLACE INTO dispositivos_ia (id, assinatura, nome, divisao, papel, em)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (i, assinatura(por_id.get(i, {})), valores["nome"], valores["divisao"], valores["papel"], em),
            )


def _validar(item: dict, tipo: str) -> dict[str, str]:
    nome = item.get("nome")
    nome = nome.strip() if isinstance(nome, str) else ""
    if len(nome) > MAX_NOME:
        nome = ""
    divisao = item.get("divisao")
    divisao = divisao.strip() if isinstance(divisao, str) else ""
    if not divisao.lower().startswith(ARTIGOS) or len(divisao) > MAX_DIVISAO:
        divisao = ""
    papel = item.get("papel")
    if papel not in PAPEIS.get(tipo, set()):
        papel = ""
    return {"nome": nome, "divisao": divisao, "papel": papel}
