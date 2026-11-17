"""`GET /conversa` e `POST /conversa`: a pessoa fala com a casa (US01)."""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import field_validator

from backend.contexto import repositorio
from backend.contrato import MensagemConversa
from backend.contrato import Modelo as ModeloContrato
from backend.conversa.interpretar import interpretar
from backend.dependencias import obter_agora, obter_modelo_dep
from backend.ia.modelo import Modelo

router = APIRouter(tags=["conversa"])


class NovaMensagem(ModeloContrato):
    texto: str

    @field_validator("texto")
    @classmethod
    def _nao_vazio(cls, texto: str) -> str:
        if not texto.strip():
            raise ValueError("o texto não pode estar vazio")
        return texto


@router.get("/conversa", response_model=list[MensagemConversa], response_model_exclude_none=True)
def listar() -> list[MensagemConversa]:
    return repositorio.listar_mensagens()


@router.post("/conversa", response_model=MensagemConversa, response_model_exclude_none=True)
def enviar(
    corpo: NovaMensagem,
    modelo: Modelo = Depends(obter_modelo_dep),
    agora: datetime = Depends(obter_agora),
) -> MensagemConversa:
    repositorio.guardar_mensagem(MensagemConversa(autor="pessoa", texto=corpo.texto, em=agora))
    interpretacao = interpretar(corpo.texto, agora, modelo)
    if interpretacao.periodo:
        repositorio.guardar_periodo(interpretacao.periodo)
    if interpretacao.rotina:
        repositorio.guardar_rotina(interpretacao.rotina)
    if interpretacao.aparelho:
        repositorio.guardar_aparelho(interpretacao.aparelho)
    resposta = MensagemConversa(autor="casa", texto=interpretacao.resposta, em=agora)
    repositorio.guardar_mensagem(resposta)
    return resposta
