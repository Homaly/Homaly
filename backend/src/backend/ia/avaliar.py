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
    )
    """
)

TITULO_POR_CLASSE = {
    "seguranca": "Alerta de segurança",
    "bem_estar": "A rotina mudou",
    "saude_conforto": "Conforto da casa",
    "eficiencia": "Energia a mais",
}

SISTEMA = """\
És a IA de uma casa ligada que avisa o responsável quando algo foge ao habitual.
Recebes, em JSON, um desvio detetado por uma regra simples e o contexto que o responsável deu à casa \
(férias, rotinas, se a casa está vazia, o aparelho ligado à tomada).
Decide se vale a pena enviar uma notificação e escreve-a. Responde só com JSON, neste formato:
{"avisar": true | false, "titulo": "...", "explicacao": "...", "acao": "..." | null}
- "avisar": false se, com este contexto, o desvio é normal e não merece incomodar a pessoa.
- "titulo": curto.
- "explicacao": em português simples, com o que aconteceu e o que é habitual.
- Não inventes factos que não estejam no resumo do desvio.
- "acao": só se houver algo que a casa possa fazer (por exemplo, apagar a lâmpada ou desligar a \
tomada); caso contrário, null.
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
        if not resposta["avisar"] and not desvio.imediato:
            return None
        titulo, explicacao, acao = resposta["titulo"], resposta["explicacao"], resposta["acao"]

    anomalia = Anomalia(
        classe=desvio.classe,
        titulo=titulo,
        explicacao=explicacao,
        detetada_em=agora,
        acao_proposta=AcaoProposta(descricao=acao) if acao else None,
    )
    with db.ligar() as con:
        con.execute(
            "INSERT OR REPLACE INTO anomalia_us (anomalia_id, us) VALUES (?, ?)",
            (anomalia.id, desvio.us),
        )
    return anomalia


def us_da_anomalia(anomalia_id: str) -> str | None:
    """A user story cuja regra gerou a anomalia (a US02 precisa dela para silenciar)."""
    with db.ligar() as con:
        linha = con.execute(
            "SELECT us FROM anomalia_us WHERE anomalia_id = ?", (anomalia_id,)
        ).fetchone()
    return linha["us"] if linha else None


def _silenciado(desvio: Desvio, contexto: Contexto, agora: datetime) -> bool:
    return any(
        s.us == desvio.us and (s.ate is None or agora <= _com_fuso(s.ate)) for s in contexto.silencios
    )


def _perguntar(
    modelo: Modelo, desvio: Desvio, contexto: Contexto, agora: datetime
) -> object:
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
            },
            "agora": agora.isoformat(),
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
    return {"avisar": avisar, "titulo": titulo, "explicacao": explicacao, "acao": acao}


def _recurso(desvio: Desvio) -> tuple[str, str, None]:
    explicacao = desvio.resumo
    if desvio.habitual:
        explicacao += " Habitual: " + desvio.habitual
    return TITULO_POR_CLASSE[desvio.classe], explicacao, None
