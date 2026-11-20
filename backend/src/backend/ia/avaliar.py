"""A IA pesa o desvio que uma regra detetou e decide se vale um aviso (US01, US02).

A regra diz o que se passou (`Desvio`); a IA, com o contexto da casa, decide se avisa e escreve o
texto. Sem modelo, ou com uma resposta que não presta, a casa fica com o resumo do desvio: nunca
deixa de avisar por causa da IA.
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime

from backend import contrato, db
from backend.contrato import AcaoProposta, Anomalia, _com_fuso
from backend.formatos import Contexto, Desvio
from backend.ia.modelo import Modelo, ModeloFalso, obter_modelo

registo = logging.getLogger(__name__)

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS anomalia_us (
        anomalia_id TEXT PRIMARY KEY,
        us          TEXT NOT NULL  -- a user story cuja regra gerou a anomalia
    );
    CREATE TABLE IF NOT EXISTS anomalia_dispositivo (
        anomalia_id TEXT PRIMARY KEY,
        dispositivo TEXT NOT NULL  -- o id do MCP do dispositivo de que a anomalia fala (Desvio.dispositivo)
    )
    """
)

# A IA escreve o texto mas não pode calar estas: a porta esquecida aberta é um risco mesmo que
# uma rotina explique quem a abriu (as rotinas explicam aberturas a horas estranhas, US07).
AVISA_SEMPRE = {"US08"}

TITULO_POR_CLASSE = {
    "seguranca": "Alerta de segurança",
    "bem_estar": "A rotina mudou",
    "saude_conforto": "Conforto da casa",
    "eficiencia": "Energia a mais",
}

SISTEMA = """\
És a IA de uma casa ligada que avisa o responsável quando algo foge ao habitual.
Recebes, em JSON, um desvio detetado por uma regra simples e o contexto que o responsável deu à casa \
(férias, rotinas, se a casa está vazia, o aparelho ligado à tomada, os compromissos de hoje no \
calendário).
Decide se vale a pena enviar uma notificação e escreve-a. Responde só com JSON, neste formato:
{"avisar": true | false, "titulo": "...", "explicacao": "...", "acao": "..." | null}
- "avisar": false se, com este contexto, o desvio é normal e não merece incomodar a pessoa.
- "titulo": curto.
- "explicacao": em português de Portugal, simples, com o que aconteceu e o que é habitual.
- Não inventes factos que não estejam no desvio ou no contexto. Se "habitual" for null, não digas \
o que é habitual nem o que "normalmente" acontece: escreve só o que aconteceu.
- Nas rotinas, "dias" vão de 0 (segunda-feira) a 6 (domingo). Uma rotina explica o desvio quando \
é o dia dela e a hora é próxima da dela; se a rotina não tiver hora, basta ser o dia dela e a \
parte do dia que a descrição disser ("de manhã": das 07:00 às 13:00; "à tarde": das 13:00 às \
20:00). Uma rotina nunca explica nada entre as 00:00 e as 06:00, a não ser que a hora dela seja \
essa. Noutro dia, ou a uma hora muito diferente, avisa.
- A falta de sinais de vida (US09) nunca se explica por a pessoa ter dito que ia ficar em casa: é com ela em casa que uma queda pode acontecer.
- "acao": uma frase curta para a pessoa, no infinitivo (por exemplo, "Apagar a lâmpada da sala" ou \
"Desligar o aquecedor"), só se a casa puder apagar a lâmpada, desligar a tomada ou fechar a água; caso \
contrário, null.
"""


def avaliar(
    desvio: Desvio,
    contexto: Contexto,
    *,
    agora: datetime | None = None,
    modelo: Modelo | None = None,
) -> Anomalia | None:
    """A anomalia a publicar para este desvio, ou `None` se não vale um aviso."""
    if agora is None:
        agora = contrato.agora()
    agora = _com_fuso(agora)
    if _silenciado(desvio, contexto, agora):
        return None

    if modelo is None:
        try:
            modelo = obter_modelo()
        except Exception:
            registo.warning("Sem modelo de IA; fica o resumo do desvio.", exc_info=True)
            modelo = ModeloFalso()
    resposta = _validar(_perguntar(modelo, desvio, contexto, agora))
    if resposta is None:
        titulo, explicacao, acao = _recurso(desvio)
    else:
        if (
            not resposta["avisar"]
            and not desvio.imediato
            and desvio.us not in AVISA_SEMPRE
            and (desvio.classe != "seguranca" or _ha_rotina_hoje(contexto, agora))
        ):
            registo.info("A IA não avisou (%s): %s", desvio.us, resposta["explicacao"])
            return None
        titulo, explicacao, acao = resposta["titulo"], resposta["explicacao"], resposta["acao"]
    acao = _acao_possivel(desvio.us, acao)

    anomalia = Anomalia(
        classe=desvio.classe,
        titulo=titulo,
        explicacao=explicacao,
        detetada_em=agora,
        acao_proposta=AcaoProposta(descricao=acao) if acao else None,
    )
    registar_us(anomalia.id, desvio.us, desvio.dispositivo)
    return anomalia


def _ha_rotina_hoje(contexto: Contexto, agora: datetime) -> bool:
    """Se a IA pode calar um aviso de segurança: só com uma rotina de hoje que lhe dê razão.

    Com hora, a hora da rotina tem de estar a menos de duas horas de agora; sem hora, nunca de
    madrugada (00:00 às 06:00). O resto (a parte do dia, se explica mesmo) fica com a IA.
    """
    minutos_agora = agora.hour * 60 + agora.minute
    for r in contexto.rotinas:
        if agora.weekday() not in r.dias:
            continue
        if r.hora is None:
            if agora.hour >= 6:
                return True
        elif abs(r.hora.hour * 60 + r.hora.minute - minutos_agora) <= 120:
            return True
    return False


def _acao_possivel(us: str, acao: str | None) -> str | None:
    """A ação a propor: só nas user stories em que a casa sabe agir (US03, `acoes.ACOES`).

    Nessas, propõe-se sempre, com o texto da IA ou, sem ele (ou sem modelo), o da casa. Nas
    outras, a ação que a IA escreveu cai: o botão Aceitar não teria nada para executar.
    """
    from backend.acoes import ACOES  # aqui dentro: acoes.py importa este módulo

    conhecida = ACOES.get(us)
    if conhecida is None:
        return None
    return acao or conhecida.descricao


def registar_us(anomalia_id: str, us: str, dispositivo: str = "") -> None:
    """Regista a user story cuja regra gerou a anomalia (a US02 precisa dela para silenciar) e,
    se a regra o disse, o id do dispositivo de que fala (a US03 age sobre esse)."""
    with db.ligar() as con:
        con.execute(
            "INSERT OR REPLACE INTO anomalia_us (anomalia_id, us) VALUES (?, ?)",
            (anomalia_id, us),
        )
        if dispositivo:
            con.execute(
                "INSERT OR REPLACE INTO anomalia_dispositivo (anomalia_id, dispositivo) VALUES (?, ?)",
                (anomalia_id, dispositivo),
            )


def dispositivo_da_anomalia(anomalia_id: str) -> str:
    """O id do MCP do dispositivo de que a anomalia fala, ou "" se a regra não o disse."""
    with db.ligar() as con:
        linha = con.execute(
            "SELECT dispositivo FROM anomalia_dispositivo WHERE anomalia_id = ?", (anomalia_id,)
        ).fetchone()
    return linha["dispositivo"] if linha else ""


def us_da_anomalia(anomalia_id: str) -> str | None:
    """A user story cuja regra gerou a anomalia (a US02 precisa dela para silenciar)."""
    with db.ligar() as con:
        linha = con.execute(
            "SELECT us FROM anomalia_us WHERE anomalia_id = ?", (anomalia_id,)
        ).fetchone()
    return linha["us"] if linha else None


def _silenciado(desvio: Desvio, contexto: Contexto, agora: datetime) -> bool:
    """Como `ciclo.silenciado`: um silêncio temporário nunca cala segurança."""
    return any(
        s.us == desvio.us
        and (s.ate is None or (desvio.classe != "seguranca" and agora <= _com_fuso(s.ate)))
        for s in contexto.silencios
    )


def _perguntar(
    modelo: Modelo, desvio: Desvio, contexto: Contexto, agora: datetime
) -> object:
    from backend.conversa.interpretar import DIAS_DA_SEMANA  # aqui dentro: interpretar importa ia/

    mensagem = json.dumps(
        {
            "desvio": {
                "us": desvio.us,
                "classe": desvio.classe,
                "resumo": desvio.resumo,
                "habitual": desvio.habitual,
                "imediato": desvio.imediato,
            },
            "contexto": {
                "ferias": [asdict(p) for p in contexto.ferias],
                "rotinas": [asdict(r) for r in contexto.rotinas],
                "casa_vazia": contexto.casa_vazia,
                "aparelho_tomada": contexto.aparelho_tomada,
                "compromissos_hoje": [asdict(c) for c in contexto.compromissos],
            },
            "agora": agora.isoformat(),
            "hoje": f"{DIAS_DA_SEMANA[agora.weekday()]}, {agora:%H:%M}",
        },
        ensure_ascii=False,
        default=str,
    )
    try:
        return modelo.completar_json(SISTEMA, mensagem)
    except Exception:
        registo.warning("O modelo de IA falhou; fica o resumo do desvio.", exc_info=True)
        return None


def _validar(resposta: object) -> dict | None:
    """A resposta se tem a forma pedida; senão `None` (e a casa usa o recurso)."""
    if not isinstance(resposta, dict):
        return None
    avisar = resposta.get("avisar")
    titulo = resposta.get("titulo")
    explicacao = resposta.get("explicacao")
    acao = resposta.get("acao")
    if not isinstance(avisar, bool):
        return None
    if not (isinstance(titulo, str) and titulo.strip()):
        return None
    if not (isinstance(explicacao, str) and explicacao.strip()):
        return None
    if acao is not None and not isinstance(acao, str):
        return None
    return {"avisar": avisar, "titulo": titulo, "explicacao": explicacao, "acao": acao if acao and acao.strip() else None}


def explicacao_do_desvio(desvio: Desvio) -> str:
    """A explicação sem IA: os factos e o habitual. O ciclo usa-a quando a anomalia muda."""
    if desvio.habitual:
        return f"{desvio.resumo} Habitual: {desvio.habitual}"
    return desvio.resumo


def _recurso(desvio: Desvio) -> tuple[str, str, None]:
    return TITULO_POR_CLASSE[desvio.classe], explicacao_do_desvio(desvio), None
