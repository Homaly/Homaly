"""A pessoa responde a uma anomalia e a casa pode propor uma rotina (US02).

A anomalia fica sempre resolvida com a resposta (na PWA, um toque em "Está tudo bem"). A resposta
não ensina nada à casa: é a casa que repara quando o aviso começa a ser habitual
(`padrao.rotina_repetida`) e propõe passar a contar com isso. A rotina só se guarda depois de a
pessoa a aceitar (`aplicar`); se a recusar, a casa não a volta a propor.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from backend.contexto import repositorio
from backend.contrato import Anomalia, PropostaSilencio, TextoEm
from backend.conversa.interpretar import DIAS_DA_SEMANA, ler_rotina
from backend.formatos import Rotina, Silencio
from backend.resposta.padrao import rotina_repetida

# O contrato ainda exige `ate` na proposta: "sem fim" é daqui a uns dez anos.
SEM_FIM = timedelta(days=3652)


@dataclass
class Decisao:
    anomalia: Anomalia
    proposta: dict | None  # o que `aplicar` faz se a pessoa aceitar


def responder(
    anomalia: Anomalia,
    us: str | None,
    texto: str,
    agora: datetime,
    anteriores: list[datetime],
    rotinas: list[Rotina],
    recusadas: list[Rotina],
) -> Decisao:
    """A anomalia resolvida com a resposta, e a rotina a propor se o aviso já se repete.

    `anteriores` são as horas dos outros avisos da mesma US; conta a hora a que esta anomalia
    foi detetada, não a da resposta.
    """
    resolvida = anomalia.model_copy(
        update={
            "estado": "resolvida",
            "resposta": TextoEm(texto=texto, em=agora),
            "resolucao": TextoEm(texto=f"Resolvida com a resposta «{texto}»", em=agora),
        }
    )
    rotina = rotina_repetida(us, anomalia.detetada_em, anteriores, rotinas, recusadas)
    if rotina is None:
        return Decisao(resolvida, None)
    proposta = {
        "tipo": "rotina",
        "descricao": rotina.descricao,
        "dias": rotina.dias,
        "hora": rotina.hora.strftime("%H:%M") if rotina.hora else None,
    }
    frase = (
        f"Isto tem-se repetido: {rotina.descricao} ({_quando(rotina)}). "
        "Passo a contar com isso? Quando bater certo, não aviso."
    )
    pendente = PropostaSilencio(texto=frase, ate=agora + SEM_FIM, estado="pendente")
    return Decisao(resolvida.model_copy(update={"proposta_silencio": pendente}), proposta)


def aplicar(proposta: dict) -> None:
    """Guarda no contexto a rotina que a pessoa aceitou (ou um silêncio, das propostas antigas)."""
    if proposta["tipo"] == "silencio":
        repositorio.guardar_silencio(
            Silencio(proposta["us"], datetime.fromisoformat(proposta["ate"]), proposta["motivo"])
        )
    else:
        repositorio.guardar_rotina(ler_rotina(proposta))


def recusar(proposta: dict) -> None:
    """A pessoa disse que não: uma rotina recusada não volta a ser proposta."""
    rotina = ler_rotina(proposta) if proposta.get("tipo") == "rotina" else None
    if rotina is not None:
        repositorio.guardar_recusa(rotina)


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
