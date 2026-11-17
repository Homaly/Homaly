"""`POST /anomalias/{id}/resposta` e `/silencio`: a pessoa responde e aceita ou recusa (US02)."""

from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import field_validator

from backend import anomalias, tempo_real
from backend.contexto import repositorio
from backend.contrato import Anomalia
from backend.contrato import Modelo as ModeloContrato
from backend.dependencias import obter_agora, obter_modelo_dep
from backend.ia.avaliar import us_da_anomalia
from backend.ia.modelo import Modelo
from backend.resposta.responder import aplicar, responder

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
    modelo: Modelo = Depends(obter_modelo_dep),
    agora: datetime = Depends(obter_agora),
    publicar: Callable[[Anomalia], None] = Depends(obter_publicar),
) -> Anomalia:
    anomalia = anomalias.obter(id)
    if anomalia is None:
        raise HTTPException(404, "Anomalia não encontrada")
    if anomalia.estado != "ativa":
        raise HTTPException(409, "Esta anomalia já foi respondida")
    decisao = responder(anomalia, us_da_anomalia(id), corpo.texto, agora, modelo)
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
    estado = "aceite" if corpo.aceitar else "recusada"
    decidida = anomalia.model_copy(
        update={"proposta_silencio": anomalia.proposta_silencio.model_copy(update={"estado": estado})}
    )
    publicar(decidida)
    repositorio.apagar_proposta(id)
    return decidida
