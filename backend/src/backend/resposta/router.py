"""`POST /anomalias/{id}/resposta` e `/silencio`: a pessoa responde e aceita ou recusa (US02)."""

from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import field_validator

from backend import anomalias, db, tempo_real
from backend.contexto import repositorio
from backend.contrato import Anomalia
from backend.contrato import Modelo as ModeloContrato
from backend.dependencias import obter_agora
from backend.ia.avaliar import us_da_anomalia
from backend.resposta.responder import aplicar, recusar, responder

router = APIRouter(prefix="/anomalias", tags=["anomalias"])


def obter_publicar() -> Callable[[Anomalia], None]:
    """Toda a mudança a uma anomalia passa por `avisos.publicar`; sem ele, só guarda e envia."""
    try:
        from backend.avisos import publicar
    except ModuleNotFoundError as e:
        if e.name != "backend.avisos":
            raise
        return _publicar
    return publicar


def _publicar(anomalia: Anomalia) -> None:
    anomalias.guardar(anomalia)
    tempo_real.enviar_anomalia(anomalia)


class NovaResposta(ModeloContrato):
    texto: str

    @field_validator("texto")
    @classmethod
    def _nao_vazio(cls, texto: str) -> str:
        if not texto.strip():
            raise ValueError("o texto não pode estar vazio")
        return texto


class Aceitacao(ModeloContrato):
    aceitar: bool


@router.post("/{id}/resposta", response_model=Anomalia, response_model_exclude_none=True)
def responder_anomalia(
    id: str,
    corpo: NovaResposta,
    agora: datetime = Depends(obter_agora),
    publicar: Callable[[Anomalia], None] = Depends(obter_publicar),
) -> Anomalia:
    anomalia = anomalias.obter(id)
    if anomalia is None:
        raise HTTPException(404, "Anomalia não encontrada")
    if anomalia.estado != "ativa":
        raise HTTPException(409, "Esta anomalia já foi respondida")
    us = us_da_anomalia(id)
    decisao = responder(
        anomalia,
        us,
        corpo.texto,
        agora,
        anteriores=_detetadas(us, excluir=id),
        rotinas=repositorio.carregar_contexto(agora).rotinas,
        recusadas=repositorio.rotinas_recusadas(),
    )
    if decisao.proposta:
        repositorio.guardar_proposta(id, decisao.proposta)
    publicar(decisao.anomalia)
    return decisao.anomalia


@router.post("/{id}/silencio", response_model=Anomalia, response_model_exclude_none=True)
def decidir_silencio(
    id: str,
    corpo: Aceitacao,
    publicar: Callable[[Anomalia], None] = Depends(obter_publicar),
) -> Anomalia:
    anomalia = anomalias.obter(id)
    if anomalia is None:
        raise HTTPException(404, "Anomalia não encontrada")
    proposta = repositorio.ler_proposta(id)
    if (
        anomalia.proposta_silencio is None
        or anomalia.proposta_silencio.estado != "pendente"
        or proposta is None
    ):
        raise HTTPException(409, "Não há nenhuma proposta de silêncio por decidir")
    if corpo.aceitar:
        aplicar(proposta)
    else:
        recusar(proposta)
    estado = "aceite" if corpo.aceitar else "recusada"
    decidida = anomalia.model_copy(
        update={"proposta_silencio": anomalia.proposta_silencio.model_copy(update={"estado": estado})}
    )
    publicar(decidida)
    repositorio.apagar_proposta(id)
    return decidida


def _detetadas(us: str | None, excluir: str) -> list[datetime]:
    """Quando foram detetados os outros avisos da mesma US (para ver se já se repete)."""
    if us is None:
        return []
    with db.ligar() as con:
        linhas = con.execute(
            """
            SELECT a.detetada_em FROM anomalias a JOIN anomalia_us u ON u.anomalia_id = a.id
            WHERE u.us = ? AND a.id != ?
            """,
            (us, excluir),
        ).fetchall()
    return [datetime.fromisoformat(linha["detetada_em"]) for linha in linhas]
