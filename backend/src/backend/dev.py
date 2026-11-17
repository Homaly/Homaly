"""Pedidos só para desenvolvimento: pôr anomalias e eventos na base de dados à mão.

Fazem o papel do ciclo das regras enquanto ele não existe, e servem para ver o tempo real na PWA.
Só existem com `HOMALY_DEV=1`, porque não pedem login.
"""

from datetime import timedelta

from fastapi import APIRouter

from . import anomalias, eventos, tempo_real
from .contrato import AcaoProposta, Anomalia, Evento, TextoEm, agora
from .ia.avaliar import registar_us

router = APIRouter(prefix="/dev", tags=["desenvolvimento"])


@router.post("/anomalias", response_model=Anomalia, response_model_exclude_none=True)
def criar_anomalia(anomalia: Anomalia, us: str | None = None) -> Anomalia:
    """Grava a anomalia (ou atualiza a que tem o mesmo id) e envia-a pelo WebSocket.

    `?us=US11` diz que regra a gerou: a US02 precisa disso para silenciar e a US03 para agir.
    """
    if us:
        registar_us(anomalia.id, us)  # antes de guardar: o evento do histórico diz o dispositivo
    anomalias.guardar(anomalia)
    tempo_real.enviar_anomalia(anomalia)
    return anomalia


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
