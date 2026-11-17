"""US03: a casa propõe uma ação e só a executa se o responsável aceitar.

`POST /anomalias/{id}/acao {aceitar}` devolve a `Anomalia` atualizada, só depois de a casa confirmar.

**O que a casa executa não vem do texto da IA.** A IA escreve a `acaoProposta.descricao` (o que a
pessoa lê); o comando é fixo por user story, em `ACOES`. Assim a IA nunca escolhe o que se liga
ou desliga. Uma anomalia cuja user story não esteja em `ACOES` não tem ação que a casa saiba fazer.

- **Aceitar:** chama `dispositivos.executar` (que confirma lendo o estado de novo). Se correu bem,
  a anomalia fica resolvida. Se falhou, nada muda e o pedido dá erro.
- **Recusar:** a casa não age e a anomalia fica resolvida. Na US11 e na US14, recusar quer dizer
  "ainda está a ser usado": a casa não volta a perguntar até ao fim do dia.

Cada decisão fica registada na tabela `acoes`, com o resultado.
"""

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from backend import anomalias, db
from backend.contexto import repositorio
from backend.contrato import Anomalia, TextoEm
from backend.contrato import Modelo as ModeloContrato
from backend.dependencias import obter_agora
from backend.formatos import Silencio
from backend.ia.avaliar import us_da_anomalia
from backend.resposta.router import obter_publicar

registo = logging.getLogger(__name__)


@dataclass(frozen=True)
class Acao:
    dispositivo: str  # como em `Leitura.dispositivo`
    tipo: str  # o type da capability
    valor: str
    descricao: str  # o texto habitual, para quem propõe a ação


ACOES: dict[str, Acao] = {
    "US11": Acao("lampada", "power", "off", "Apagar a luz"),
    "US14": Acao("tomada", "power", "off", "Desligar a tomada"),
}
"""A ação que a casa sabe fazer em cada user story."""

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS acoes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        anomalia_id TEXT NOT NULL,
        dispositivo TEXT,
        tipo        TEXT,
        valor       TEXT,
        resultado   TEXT NOT NULL,  -- 'feita', 'falhou' ou 'recusada'
        em          TEXT NOT NULL   -- ISO 8601 em UTC
    )
    """
)

Executar = Callable[[str, str, str], bool]


def obter_executar() -> Executar:
    """O `dispositivos.executar` da Xuta; enquanto não existir, um falso só em desenvolvimento."""
    try:
        from backend.dispositivos import executar
    except ModuleNotFoundError as e:
        if e.name != "backend.dispositivos":
            raise
        if os.environ.get("HOMALY_DEV") == "1":
            return _executar_falso
        return _sem_dispositivos
    return executar


def _executar_falso(dispositivo: str, tipo: str, valor: str) -> bool:
    registo.warning("executar falso: %s %s=%s (nada foi enviado ao MCP)", dispositivo, tipo, valor)
    return True


def _sem_dispositivos(dispositivo: str, tipo: str, valor: str) -> bool:
    registo.error("Ainda não há ligação aos dispositivos; %s %s=%s não foi feito", dispositivo, tipo, valor)
    return False


def registar(anomalia_id: str, acao: Acao | None, resultado: str, em: datetime) -> None:
    with db.ligar() as con:
        con.execute(
            "INSERT INTO acoes (anomalia_id, dispositivo, tipo, valor, resultado, em)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                anomalia_id,
                acao.dispositivo if acao else None,
                acao.tipo if acao else None,
                acao.valor if acao else None,
                resultado,
                em.astimezone(UTC).isoformat(),
            ),
        )


class Decisao(ModeloContrato):
    aceitar: bool


router = APIRouter(prefix="/anomalias", tags=["anomalias"])


@router.post("/{id}/acao", response_model=Anomalia, response_model_exclude_none=True)
def decidir_acao(
    id: str,
    corpo: Decisao,
    executar: Executar = Depends(obter_executar),
    publicar: Callable[[Anomalia], None] = Depends(obter_publicar),
    agora: datetime = Depends(obter_agora),
) -> Anomalia:
    anomalia = anomalias.obter(id)
    if anomalia is None:
        raise HTTPException(404, "Anomalia não encontrada")
    if anomalia.estado != "ativa":
        raise HTTPException(409, "Esta anomalia já foi respondida")
    if anomalia.acao_proposta is None:
        raise HTTPException(409, "Esta anomalia não tem nenhuma ação proposta")
    descricao = anomalia.acao_proposta.descricao
    us = us_da_anomalia(id)
    acao = ACOES.get(us) if us else None

    if not corpo.aceitar:
        registar(id, acao, "recusada", agora)
        resolucao = "A casa não agiu."
        if acao:
            fim_do_dia = agora.replace(hour=23, minute=59, second=59, microsecond=0)
            repositorio.guardar_silencio(Silencio(us, fim_do_dia, f"Recusou: {descricao}"))
            resolucao += " Não volta a perguntar até ao fim do dia."
        return _resolver(anomalia, f"Recusou: {descricao}", resolucao, agora, publicar)

    if acao is None:
        raise HTTPException(409, "A casa não sabe fazer esta ação")
    try:
        feita = executar(acao.dispositivo, acao.tipo, acao.valor)
    except Exception:
        registo.exception("executar falhou: %s %s=%s", acao.dispositivo, acao.tipo, acao.valor)
        feita = False
    if not feita:
        registar(id, acao, "falhou", agora)
        raise HTTPException(502, "A casa não conseguiu confirmar a ação. Nada foi alterado.")
    registar(id, acao, "feita", agora)
    return _resolver(anomalia, f"Aceitou: {descricao}", f"Feito: {descricao}.", agora, publicar)


def _resolver(
    anomalia: Anomalia,
    resposta: str,
    resolucao: str,
    agora: datetime,
    publicar: Callable[[Anomalia], None],
) -> Anomalia:
    resolvida = anomalia.model_copy(
        update={
            "estado": "resolvida",
            "resposta": TextoEm(texto=resposta, em=agora),
            "resolucao": TextoEm(texto=resolucao, em=agora),
        }
    )
    publicar(resolvida)
    return resolvida
