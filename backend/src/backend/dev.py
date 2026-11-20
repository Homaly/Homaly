"""Pedidos só para desenvolvimento: pôr anomalias e eventos na base de dados à mão.

Fazem o papel do ciclo das regras enquanto ele não existe, e servem para ver o tempo real na PWA.
Só existem com `HOMALY_DEV=1`, porque não pedem login.
"""

import base64
import binascii
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from . import anomalias, avisos, camara, eventos, tempo_real
from .contrato import AcaoProposta, Anomalia, Evento, TextoEm
from .dependencias import obter_agora as agora
from .ia.avaliar import registar_us

router = APIRouter(prefix="/dev", tags=["desenvolvimento"])


@router.post("/anomalias", response_model=Anomalia, response_model_exclude_none=True)
def criar_anomalia(anomalia: Anomalia, us: str | None = None, contacto: bool = False) -> Anomalia:
    """Grava a anomalia (ou atualiza a que tem o mesmo id) e envia-a pelo WebSocket.

    `?us=US11` diz que regra a gerou: a US02 precisa disso para silenciar e a US03 para agir.
    `?contacto=true` passa-a pelo `avisos.publicar`, como o ciclo: se for de segurança ou de
    bem-estar, o contacto externo recebe a SMS no fim do tempo de espera (US05).
    """
    if us:
        registar_us(anomalia.id, us)  # antes de guardar: o evento do histórico diz o dispositivo
    if contacto:
        avisos.publicar(anomalia)  # grava, envia pelo WebSocket e agenda a SMS
        return anomalia
    anomalias.guardar(anomalia)
    tempo_real.enviar_anomalia(anomalia)
    return anomalia


class FotoDaCamara(BaseModel):
    imagem: Annotated[str, Field(min_length=1, max_length=15_000_000)]  # JPEG em base64 (ou data:)


@router.post("/us13", status_code=204)
def simular_veiculo(pedido: FotoDaCamara) -> Response:
    """US13 sem câmara: a câmara passa a "ver" esta fotografia e conta-se um movimento.

    Com o ciclo a correr (CICLO=1) e um modelo de visão, um veículo desconhecido na fotografia dá
    o aviso ao fim de VEICULO_MINUTOS. A fotografia fica até `DELETE /dev/us13`.
    """
    texto = pedido.imagem.split(",", 1)[1] if pedido.imagem.startswith("data:") else pedido.imagem
    try:
        jpeg = base64.b64decode(texto, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=422, detail="A imagem tem de vir em base64") from None
    camara.definir_foto_fixa(camara.reduzir(jpeg))
    camara.simular_movimento()
    return Response(status_code=204)


@router.delete("/us13", status_code=204)
def parar_veiculo() -> Response:
    """A câmara volta a ser a verdadeira."""
    camara.definir_foto_fixa(None)
    return Response(status_code=204)


@router.post("/eventos", response_model=Evento, response_model_exclude_none=True)
def criar_evento(evento: Evento) -> Evento:
    eventos.registar(evento)
    return evento


@router.post("/exemplo")
def carregar_exemplo() -> dict:
    """Os mesmos dados que os mocks da PWA. Pode correr-se várias vezes: os ids são fixos."""
    t = agora()

    def ha(minutos: int):
        return t - timedelta(minutes=minutos)

    exemplo_anomalias = [
        Anomalia(
            id="exemplo-porta",
            classe="seguranca",
            titulo="Porta da rua aberta há 7 minutos",
            explicacao=f"A porta da rua abriu às {ha(7):%H:%M} e ainda não fechou. "
            "Normalmente fecha em menos de um minuto.",
            detetada_em=ha(2),
        ),
        Anomalia(
            id="exemplo-luz",
            classe="eficiencia",
            titulo="Luz da sala acesa há 5 horas",
            explicacao="A luz da sala está acesa há cinco horas e a porta abriu e fechou depois "
            "disso. Ainda estão a usar?",
            detetada_em=ha(15),
            acao_proposta=AcaoProposta(descricao="Apagar a luz da sala"),
        ),
        Anomalia(
            id="exemplo-frio",
            classe="saude_conforto",
            titulo="Casa fria durante a noite",
            explicacao="A sala esteve abaixo de 16 °C durante três horas. Já voltou aos 19 °C.",
            detetada_em=ha(60 * 10),
            estado="resolvida",
            resolucao=TextoEm(texto="A sala voltou aos 19 °C.", em=ha(60 * 7)),
        ),
    ]
    exemplo_eventos = [
        Evento(id="exemplo-e1", em=ha(7), dispositivo="Porta da rua", descricao="Abriu"),
        Evento(id="exemplo-e2", em=ha(90), dispositivo="Sala", descricao="19,5 °C"),
        Evento(id="exemplo-e3", em=ha(180), dispositivo="Porta da rua", descricao="Fechou"),
        Evento(id="exemplo-e4", em=ha(181), dispositivo="Porta da rua", descricao="Abriu"),
        Evento(id="exemplo-e5", em=ha(300), dispositivo="Luz da sala", descricao="Acendeu"),
        Evento(id="exemplo-e6", em=ha(60 * 10), dispositivo="Sala", descricao="15,4 °C"),
    ]
    us = {"exemplo-porta": "US08", "exemplo-luz": "US11", "exemplo-frio": "US10"}
    for anomalia in exemplo_anomalias:
        criar_anomalia(anomalia, us[anomalia.id])
    for evento in exemplo_eventos:
        eventos.registar(evento)
    return {"anomalias": len(exemplo_anomalias), "eventos": len(exemplo_eventos)}
