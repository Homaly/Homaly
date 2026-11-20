"""A IA lê o que a pessoa disse à casa e diz o que fazer com isso, ou responde-lhe (US01, US14).

O modelo devolve um JSON de um de cinco tipos (férias, rotina, aparelho, resposta, não percebi). Qualquer
outra coisa, ou um modelo que falha, dá `NAO_PERCEBI`: a casa nunca grava o que não percebeu.
`ler_rotina` e `ler_data` são públicas porque a US02 usa as mesmas regras.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, time

from backend.contrato import MensagemConversa
from backend.formatos import Periodo, Rotina
from backend.ia.modelo import Modelo

registo = logging.getLogger(__name__)

NAO_PERCEBI = "Não percebi bem. Podes dizer de outra forma?"

MAX_HISTORICO = 10  # mensagens anteriores que a IA lê: a memória curta da conversa
MAX_CARACTERES = 500  # de cada uma, para o pedido não crescer sem limite

DIAS_DA_SEMANA = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]

SISTEMA = """\
És a IA de uma casa ligada e falas com o responsável da casa, em português de Portugal, tratando-o \
por tu. Ele pode dizer-te coisas que a casa deve saber ou fazer-te perguntas. Responde só com JSON, \
num destes formatos:
{"tipo": "ferias", "inicio": "AAAA-MM-DD", "fim": "AAAA-MM-DD", "motivo": "...", "resposta": "..."}
{"tipo": "rotina", "descricao": "...", "dias": [1], "hora": "HH:MM" | null, "resposta": "..."}
{"tipo": "aparelho", "nome": "...", "resposta": "..."}
{"tipo": "resposta", "resposta": "..."}
{"tipo": "nao_percebi"}
- "ferias": a pessoa vai estar fora de casa. "inicio" e "fim" em ISO 8601; se disser só a data \
de fim, o início é hoje. Só a data (AAAA-MM-DD) quando a pessoa não diz a hora: o fim conta o dia \
todo. Com a hora ou a parte do dia, AAAA-MM-DDTHH:MM ("a partir das 15h", "hoje à tarde" = 14:00, \
"à noite" = 20:00).
- "rotina": algo que acontece em dias certos (a empregada vem às terças). "dias" são números de \
0 a 6, com 0 = segunda-feira. "hora" só se a pessoa a disser, senão null.
- "aparelho": só quando a pessoa diz o que está ligado à tomada (por exemplo, "na tomada está o \
aquecedor"). "nome" é o aparelho.
- "resposta": perguntas sobre a casa ("a porta está fechada?", "está tudo bem?", "o que \
aconteceu hoje?", "que rotinas sabes?"), cumprimentos e pedidos para a casa fazer alguma coisa. \
Responde só com o que está em "O que a casa sabe agora" ou com o que já se disse nesta conversa; \
se não estiver em nenhum, diz que não sabes. \
A casa não cumpre ordens pela conversa: a um pedido como "apaga a luz", explica que as ações são \
propostas nos avisos, quando a casa repara em alguma coisa. A um cumprimento, diz o que te podem \
dizer (férias, rotinas, o aparelho na tomada) e perguntar.
- Antes da última mensagem vêm as mensagens anteriores desta conversa. Usa-as para perceber a \
última ("e amanhã?", "e às quintas também") e para te lembrares do que a pessoa te pediu na \
conversa (por exemplo, o nome por que te deve chamar). O JSON é só sobre a última mensagem: não \
voltes a mandar férias, rotinas ou aparelhos que vieram em mensagens anteriores. O estado da casa \
vem só de "O que a casa sabe agora": o que se disse antes pode já não ser verdade.
- Nunca digas que fizeste, mudaste, ligaste ou apagaste alguma coisa.
- "resposta" (em todos os tipos): curta e simpática, em português de Portugal; as datas por \
extenso ("19 de novembro"), nunca AAAA-MM-DD.
- Se não for nenhuma destas coisas, responde {"tipo": "nao_percebi"}.
- Não inventes datas, dias, aparelhos nem estados da casa.
"""


@dataclass
class Interpretacao:
    resposta: str
    periodo: Periodo | None = None
    rotina: Rotina | None = None
    aparelho: str | None = None


def interpretar(
    texto: str,
    agora: datetime,
    modelo: Modelo,
    estado: dict | None = None,
    historico: list[MensagemConversa] | None = None,
) -> Interpretacao:
    """O que a casa percebeu de `texto`; sem certeza, `NAO_PERCEBI` e nada para guardar.

    `estado` é o que a casa sabe agora (`conversa.estado`), para responder a perguntas.
    `historico` são as mensagens anteriores da conversa, sem `texto`: só as últimas
    `MAX_HISTORICO` seguem para o modelo, a memória curta da casa.
    """
    sistema = (
        SISTEMA
        + f"\nHoje é {DIAS_DA_SEMANA[agora.weekday()]}, {agora.date().isoformat()}."
        " Usa esta data para perceber 'amanhã', 'sexta' ou 'às terças'."
        + f"\nO que a casa sabe agora: {json.dumps(estado or {}, ensure_ascii=False)}"
    )
    try:
        dados = modelo.completar_json(sistema, texto, historico=_para_o_modelo(historico or []))
    except Exception:
        registo.warning("O modelo de IA falhou; a casa não percebeu a mensagem.", exc_info=True)
        return Interpretacao(NAO_PERCEBI)
    return _ler(dados, agora) or Interpretacao(NAO_PERCEBI)


def _para_o_modelo(historico: list[MensagemConversa]) -> list[dict[str, str]]:
    """As últimas mensagens como papéis do modelo, abrindo sempre com a pessoa."""
    mensagens = [
        {"role": "user" if m.autor == "pessoa" else "assistant", "content": m.texto[:MAX_CARACTERES]}
        for m in historico[-MAX_HISTORICO:]
    ]
    while mensagens and mensagens[0]["role"] != "user":
        mensagens.pop(0)
    return mensagens


def ler_data(valor: object, agora: datetime) -> datetime | None:
    """Uma data ISO 8601; sem fuso, fica com o de `agora`. `None` se não se lê."""
    if not isinstance(valor, str):
        return None
    try:
        data = datetime.fromisoformat(valor)
    except ValueError:
        return None
    return data if data.tzinfo else data.replace(tzinfo=agora.tzinfo)


def _ate_ao_fim_do_dia(valor: object, fim: datetime | None) -> datetime | None:
    """Um fim só com a data ("até domingo") conta o dia todo, não só a meia-noite."""
    if fim is None or not isinstance(valor, str):
        return fim
    try:
        date.fromisoformat(valor)
    except ValueError:
        return fim  # trazia a hora: fica essa
    return datetime.combine(fim.date(), time.max, tzinfo=fim.tzinfo)


def ler_rotina(dados: object) -> Rotina | None:
    """A rotina de `{"descricao", "dias", "hora"}` se estiver bem formada; senão `None`."""
    if not isinstance(dados, dict):
        return None
    descricao = dados.get("descricao")
    dias = dados.get("dias")
    hora = dados.get("hora")
    if not (isinstance(descricao, str) and descricao.strip()):
        return None
    if not (isinstance(dias, list) and dias):
        return None
    if not all(type(d) is int and 0 <= d <= 6 for d in dias):
        return None
    if hora is None:
        return Rotina(descricao, dias, None)
    if not (isinstance(hora, str) and re.fullmatch(r"\d{2}:\d{2}", hora)):
        return None
    try:
        return Rotina(descricao, dias, time.fromisoformat(hora))
    except ValueError:
        return None


def _ler(dados: object, agora: datetime) -> Interpretacao | None:
    if not isinstance(dados, dict):
        return None
    resposta = dados.get("resposta")
    if not (isinstance(resposta, str) and resposta.strip()):
        return None
    tipo = dados.get("tipo")
    if tipo == "resposta":
        return Interpretacao(resposta)
    if tipo == "ferias":
        inicio = ler_data(dados.get("inicio"), agora)
        fim = _ate_ao_fim_do_dia(dados.get("fim"), ler_data(dados.get("fim"), agora))
        motivo = dados.get("motivo")
        if inicio is None or fim is None or fim <= inicio or not isinstance(motivo, str):
            return None
        return Interpretacao(resposta, periodo=Periodo(inicio, fim, motivo))
    if tipo == "rotina":
        rotina = ler_rotina(dados)
        return Interpretacao(resposta, rotina=rotina) if rotina else None
    if tipo == "aparelho":
        nome = dados.get("nome")
        if not (isinstance(nome, str) and nome.strip()):
            return None
        return Interpretacao(resposta, aparelho=nome.strip())
    return None
