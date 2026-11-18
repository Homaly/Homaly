"""A pessoa responde a uma anomalia e a casa pode propor deixar de avisar (US02).

A anomalia fica sempre resolvida. A IA lê a resposta e diz se é só uma ocorrência (`nenhum`), se
vale só por hoje (`temporario`) ou se é uma rotina (`recorrente`). Só nos dois últimos a casa propõe
silenciar; a proposta só se aplica depois de a pessoa a aceitar (`aplicar`). Uma resposta do
modelo que não presta, ou um modelo que falha, não dá proposta: a anomalia fica resolvida na mesma.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.contexto import repositorio
from backend.contrato import Anomalia, PropostaSilencio, TextoEm
from backend.conversa.interpretar import DIAS_DA_SEMANA, ler_rotina
from backend.formatos import Rotina, Silencio
from backend.ia.avaliar import AVISA_SEMPRE
from backend.ia.modelo import Modelo

registo = logging.getLogger(__name__)

MOTIVOS = ("nenhum", "temporario", "recorrente")

SISTEMA = """\
És a IA de uma casa ligada. A casa avisou o responsável de uma anomalia e ele respondeu-lhe. \
Percebe se a resposta quer dizer que a casa não precisa de voltar a avisar disto. Responde só \
com JSON:
{"motivo": "nenhum" | "temporario" | "recorrente", "rotina": {"descricao": "...", "dias": [1], \
"hora": "HH:MM" | null} | null}
- "nenhum": a pessoa só explica ou diz que está tudo bem ("está tudo bem", "fui eu").
- "temporario": só para uma situação de hoje, que não vai repetir-se ("hoje tenho visitas", \
"hoje estou fora").
- "recorrente": a resposta explica o que a anomalia diz que aconteceu com algo que se repete em \
dias certos da semana (porta aberta: "a empregada vem às terças às 10h"; casa fria: "ao fim de \
semana desligo o aquecimento"). Se o que a pessoa diz não explica esta anomalia (porta aberta: \
"ao fim de semana fico em casa da minha mãe"), não é "recorrente": responde "nenhum". Preenche \
"rotina": "dias" são números de 0 a 6, com \
0 = segunda-feira, ..., 5 = sábado, 6 = domingo; "fim de semana" é [5, 6], "dias úteis" é \
[0, 1, 2, 3, 4] e "todos os dias" é [0, 1, 2, 3, 4, 5, 6]. "hora" só se a pessoa a disser, \
senão null.
- Se fala de um dia futuro concreto ("amanhã tenho visitas"), não é "temporario" nem \
"recorrente": responde "nenhum".
- "temporario" e "recorrente" só quando a resposta explica esta anomalia; uma resposta sem \
relação com o que aconteceu é "nenhum". Uma rotina só explica a anomalia se hoje for um dos dias \
dela.
- Fora de "recorrente", "rotina" é null.
- Na dúvida, responde "nenhum". Não inventes dias nem horas que a pessoa não tenha dito.
"""


@dataclass
class Decisao:
    anomalia: Anomalia
    proposta: dict | None  # o que `aplicar` faz se a pessoa aceitar


def responder(
    anomalia: Anomalia, us: str | None, texto: str, agora: datetime, modelo: Modelo
) -> Decisao:
    """A anomalia resolvida com a resposta da pessoa, e a proposta de silêncio que daí sair."""
    resolvida = anomalia.model_copy(
        update={
            "estado": "resolvida",
            "resposta": TextoEm(texto=texto, em=agora),
            "resolucao": TextoEm(texto=f"Resolvida com a resposta «{texto}»", em=agora),
        }
    )
    dados = _perguntar(modelo, anomalia, texto, agora)
    motivo = dados.get("motivo") if isinstance(dados, dict) else None

    if motivo == "temporario" and anomalia.classe != "seguranca" and us:
        ate = agora.replace(hour=23, minute=59, second=59, microsecond=0)
        proposta = {"tipo": "silencio", "us": us, "ate": ate.isoformat(), "motivo": texto}
        frase = f"Não volto a avisar sobre «{anomalia.titulo}» até ao fim do dia, ok?"
        return _com_proposta(resolvida, frase, ate, proposta)

    if motivo == "recorrente" and us not in AVISA_SEMPRE:
        rotina = ler_rotina(dados.get("rotina"))
        # Uma rotina só explica a anomalia se hoje for um dos dias dela (a IA às vezes esquece-se).
        if rotina and agora.weekday() in rotina.dias:
            proposta = {
                "tipo": "rotina",
                "descricao": rotina.descricao,
                "dias": rotina.dias,
                "hora": rotina.hora.strftime("%H:%M") if rotina.hora else None,
            }
            frase = (
                f"Passo a ter isto em conta: {rotina.descricao} ({_quando(rotina)}). "
                "Quando bater certo, não aviso. Ok?"
            )
            # O contrato ainda exige `ate`: "sem fim" é daqui a uns dez anos.
            return _com_proposta(resolvida, frase, agora + timedelta(days=3652), proposta)

    return Decisao(resolvida, None)


def aplicar(proposta: dict) -> None:
    """Guarda no contexto o silêncio ou a rotina que a pessoa aceitou."""
    if proposta["tipo"] == "silencio":
        repositorio.guardar_silencio(
            Silencio(proposta["us"], datetime.fromisoformat(proposta["ate"]), proposta["motivo"])
        )
    else:
        repositorio.guardar_rotina(ler_rotina(proposta))


GRUPOS_DE_DIAS = {
    (0, 1, 2, 3, 4): "dias úteis",
    (5, 6): "fim de semana",
    (0, 1, 2, 3, 4, 5, 6): "todos os dias",
}


def _quando(rotina: Rotina) -> str:
    """Os dias e a hora que ficam guardados, para a pessoa saber o que aceita: "sábado e domingo"."""
    numeros = sorted(set(rotina.dias))
    nomes = [DIAS_DA_SEMANA[d] for d in numeros]
    dias = GRUPOS_DE_DIAS.get(tuple(numeros)) or (
        nomes[0] if len(nomes) == 1 else f"{', '.join(nomes[:-1])} e {nomes[-1]}"
    )
    return f"{dias}, às {rotina.hora:%H:%M}" if rotina.hora else dias


def _com_proposta(anomalia: Anomalia, texto: str, ate: datetime, proposta: dict) -> Decisao:
    pendente = PropostaSilencio(texto=texto, ate=ate, estado="pendente")
    return Decisao(anomalia.model_copy(update={"proposta_silencio": pendente}), proposta)


def _perguntar(modelo: Modelo, anomalia: Anomalia, texto: str, agora: datetime) -> object:
    mensagem = json.dumps(
        {
            "anomalia": {
                "classe": anomalia.classe,
                "titulo": anomalia.titulo,
                "explicacao": anomalia.explicacao,
            },
            "resposta": texto,
            "hoje": f"{DIAS_DA_SEMANA[agora.weekday()]}, {agora.date().isoformat()}",
        },
        ensure_ascii=False,
    )
    try:
        return modelo.completar_json(SISTEMA, mensagem)
    except Exception:
        registo.warning("O modelo de IA falhou; a anomalia fica resolvida sem proposta.", exc_info=True)
        return None
