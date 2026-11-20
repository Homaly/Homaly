"""US05: o contacto externo recebe uma SMS quando o responsável não responde a tempo.

O `avisos.publicar` chama `ContactoExterno().agendar`, `cancelar` e `resolvida`; nada aqui envia
logo. Cada anomalia de segurança ou de bem-estar fica com a hora a que deve sair a SMS (o fim do
tempo de espera das Definições; já, com a casa vazia ou espera zero), e `verificar()`, chamada de
poucos em poucos segundos pela thread de `arrancar()`, envia o que está na hora.

Na hora de enviar volta-se a ver tudo, por isso nenhum outro módulo tem de lembrar de cancelar:
- a anomalia já tem resposta (US02), ou está resolvida (pela resposta, pela ação da US03 ou
  sozinha): não sai nada;
- deixou de ser de segurança ou de bem-estar, ou já não há contacto (US04): não sai nada.

Se o contacto recebeu o alerta, recebe também uma SMS quando a anomalia se resolve. As SMS não
levam link nem há página do alerta (decisão da equipa, 2026-11-20): a mensagem basta.
O textbee que falha tenta-se mais duas vezes, 30 s e 60 s depois. O envio reserva a linha
(`a_enviar`) antes de falar com o textbee, para uma resposta ou resolução a meio não se perder.
"""

import logging
import secrets
import threading
from collections.abc import Callable
from datetime import datetime, timedelta

from backend import anomalias, definicoes
from backend.contrato import Anomalia
from backend.contrato import agora as _agora_real

from . import envios, mensagens, sms

registo = logging.getLogger(__name__)

CLASSES = {"seguranca", "bem_estar"}  # as únicas que chegam ao contacto externo
TENTATIVAS = 3
INTERVALO_S = 5.0
ESPERA_NO_LIMITE = timedelta(minutes=1)  # no limite de SMS por hora (SMS_MAXIMO_HORA), volta a ver

Relogio = Callable[[], datetime]


class ContactoExterno:
    """O contacto externo real, para o `avisos.publicar`.

    Os prazos (tempo de espera, novas tentativas) contam em tempo real, mesmo com o relógio da app
    acelerado (RELOGIO_FATOR): são o tempo que o responsável tem para responder e o do textbee.
    """

    def __init__(self, agora: Relogio = _agora_real) -> None:
        self._agora = agora

    def agendar(self, anomalia: Anomalia, imediato: bool = False) -> None:
        """Começa o tempo de espera de uma anomalia nova (ou que passou a segurança)."""
        if anomalia.classe not in CLASSES or anomalia.estado != "ativa":
            return
        espera = 0 if imediato else definicoes.obter().espera_minutos
        enviar_em = self._agora() + timedelta(minutes=espera)
        existente = envios.obter(anomalia.id)
        if existente is None:
            envios.criar(anomalia.id, enviar_em)
        elif existente.estado == "pendente" and enviar_em < existente.enviar_em:
            # A casa ficou vazia: já. Só se ainda ninguém a estiver a enviar.
            envios.mudar(anomalia.id, so_se_estado="pendente", enviar_em=enviar_em)

    def cancelar(self, anomalia_id: str) -> None:
        """O responsável respondeu: o contacto não recebe nada desta anomalia."""
        _cancelar(anomalia_id, "o responsável respondeu")

    def resolvida(self, anomalia: Anomalia) -> None:
        """Se o contacto já recebeu o alerta (ou está a recebê-lo), recebe a SMS de resolvido."""
        envio = envios.obter(anomalia.id)
        if envio is None:
            return
        if envio.estado == "pendente":
            if _cancelar(anomalia.id, "resolveu-se antes do fim do tempo de espera"):
                return
            # A thread reservou-o entre a leitura e o cancelamento: o alerta está a sair.
            envio = envios.obter(anomalia.id)
            if envio is None:
                return
        if envio.estado in ("a_enviar", "enviada") and envio.resolvido is None:
            # A meio do envio: se o alerta sair, a de resolvido sai a seguir; se falhar, o alerta
            # é cancelado na volta seguinte (já está resolvida) e a de resolvido nunca sai.
            agora = self._agora()
            envios.mudar(anomalia.id, resolvido="pendente", resolvido_em=agora, enviar_em=agora)


def _cancelar(anomalia_id: str, motivo: str) -> bool:
    """Cancela o alerta se ainda estiver `pendente`; devolve se cancelou."""
    if envios.mudar(anomalia_id, so_se_estado="pendente", estado="cancelada", motivo=motivo):
        registo.info("SMS ao contacto externo cancelada (%s): %s", anomalia_id[:8], motivo)
        return True
    return False


def _espera_depois_de_falhar(tentativas: int) -> timedelta:
    """30 s depois da primeira falha, 60 s depois da segunda."""
    return timedelta(seconds=30 * 2 ** (tentativas - 1))


def verificar(agora: datetime | None = None) -> None:
    """Envia as SMS que estão na hora: os alertas e as de resolvido.

    Um envio que rebenta com um erro inesperado fica `falhou` e não trava os outros.
    """
    agora = agora or _agora_real()
    for envio in envios.pendentes():
        if envio.enviar_em <= agora:
            _isolado(_enviar_alerta, envio, agora, resolvido=False)
    for envio in envios.resolvidos_por_enviar():
        if envio.enviar_em <= agora:
            _isolado(_enviar_resolvido, envio, agora, resolvido=True)


def _isolado(
    enviar: Callable[[envios.Envio, datetime], None], envio: envios.Envio, agora: datetime, resolvido: bool
) -> None:
    try:
        enviar(envio, agora)
    except Exception:  # noqa: BLE001 — fica no registo e na tabela; os outros envios continuam
        registo.exception("Envio ao contacto externo rebentou (%s)", envio.anomalia_id[:8])
        if resolvido:
            envios.mudar(envio.anomalia_id, resolvido="falhou")
        else:
            envios.mudar(envio.anomalia_id, estado="falhou", motivo="erro inesperado (ver o registo)")


def _enviar_alerta(envio: envios.Envio, agora: datetime) -> None:
    anomalia = anomalias.obter(envio.anomalia_id)
    defs = definicoes.obter()
    motivo = _motivo_para_nao_enviar(anomalia, defs.contacto is not None)
    if motivo:
        _cancelar(envio.anomalia_id, motivo)
        return
    assert anomalia is not None and defs.contacto is not None
    codigo = envio.codigo or secrets.token_urlsafe(16)
    texto = mensagens.alerta(anomalia, defs.nome_casa)
    # Reserva o envio: a partir daqui ninguém o cancela nem o adia a meio.
    if not envios.mudar(envio.anomalia_id, so_se_estado="pendente", estado="a_enviar", codigo=codigo):
        return
    tentativas = envio.tentativas + 1
    try:
        sms.enviar(defs.contacto.telemovel, texto)
    except sms.LimiteSMS as e:
        # Não é uma falha: espera que a hora liberte um lugar, sem gastar tentativas.
        envios.mudar(
            envio.anomalia_id, so_se_estado="a_enviar", estado="pendente", enviar_em=agora + ESPERA_NO_LIMITE, motivo=str(e)
        )
        registo.warning("SMS ao contacto externo à espera do limite por hora: %s", e)
        return
    except sms.ErroSMS as e:
        desiste = tentativas >= TENTATIVAS
        envios.mudar(
            envio.anomalia_id,
            so_se_estado="a_enviar",
            estado="falhou" if desiste else "pendente",
            tentativas=tentativas,
            enviar_em=agora + _espera_depois_de_falhar(tentativas),
            motivo=str(e),
        )
        registo.warning("SMS ao contacto externo falhou (%d/%d): %s", tentativas, TENTATIVAS, e)
        return
    envios.mudar(
        envio.anomalia_id,
        so_se_estado="a_enviar",
        estado="enviada",
        tentativas=tentativas,
        telemovel=defs.contacto.telemovel,
        ultima_sms_em=agora,
        motivo=None,
    )
    registo.info("SMS ao contacto externo enviada (%s)", envio.anomalia_id[:8])


def _motivo_para_nao_enviar(anomalia: Anomalia | None, ha_contacto: bool) -> str | None:
    if anomalia is None:
        return "a anomalia já não existe"
    if anomalia.estado == "resolvida":
        return "resolveu-se antes do fim do tempo de espera"
    if anomalia.resposta is not None:
        return "o responsável respondeu"
    if anomalia.classe not in CLASSES:
        return "deixou de ser de segurança ou de bem-estar"
    if not ha_contacto:
        return "não há contacto externo"
    return None


def _enviar_resolvido(envio: envios.Envio, agora: datetime) -> None:
    anomalia = anomalias.obter(envio.anomalia_id)
    if anomalia is None or envio.telemovel is None or envio.codigo is None:
        registo.warning("SMS de resolvido sem anomalia, número ou link (%s)", envio.anomalia_id[:8])
        envios.mudar(envio.anomalia_id, resolvido="falhou")
        return
    texto = mensagens.resolvido(anomalia, definicoes.obter().nome_casa, envio.resolvido_em or agora)
    tentativas = envio.tentativas_resolvido + 1
    try:
        sms.enviar(envio.telemovel, texto)
    except sms.LimiteSMS as e:
        envios.mudar(envio.anomalia_id, enviar_em=agora + ESPERA_NO_LIMITE)
        registo.warning("SMS de resolvido à espera do limite por hora: %s", e)
        return
    except sms.ErroSMS as e:
        envios.mudar(
            envio.anomalia_id,
            tentativas_resolvido=tentativas,
            resolvido="falhou" if tentativas >= TENTATIVAS else "pendente",
            enviar_em=agora + _espera_depois_de_falhar(tentativas),
        )
        registo.warning("SMS de resolvido falhou (%d/%d): %s", tentativas, TENTATIVAS, e)
        return
    envios.mudar(envio.anomalia_id, resolvido="enviada", tentativas_resolvido=tentativas, ultima_sms_em=agora)
    registo.info("SMS de resolvido enviada (%s)", envio.anomalia_id[:8])


def recuperar() -> None:
    """No arranque: um envio que ficou a meio (o backend caiu) volta a `pendente`.

    Pode repetir uma SMS que já tinha saído; é melhor do que perder um alerta.
    """
    quantos = envios.recuperar_interrompidos()
    if quantos:
        registo.warning("%d envio(s) ao contacto externo ficaram a meio; voltam a tentar", quantos)


def arrancar(intervalo: float = INTERVALO_S, agora: Relogio | None = None) -> Callable[[], None]:
    """Uma thread que chama `verificar()` de `intervalo` em `intervalo` segundos; devolve `parar`."""
    recuperar()
    parar = threading.Event()

    def correr() -> None:
        while not parar.is_set():
            try:
                verificar(agora() if agora else None)
            except Exception:  # noqa: BLE001 — fica no registo; a thread não pode morrer
                registo.exception("A verificação do contacto externo falhou")
            parar.wait(intervalo)

    fio = threading.Thread(target=correr, name="contacto-externo", daemon=True)
    fio.start()

    def terminar() -> None:
        parar.set()
        fio.join(timeout=5)

    return terminar
