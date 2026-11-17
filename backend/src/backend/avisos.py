"""avisos.publicar: toda a mudança a uma anomalia (nova, mudada ou resolvida) passa por aqui.

Grava a anomalia (anomalias.guardar), envia-a pelo WebSocket (tempo_real) e avisa o
contacto externo:
- anomalia nova: contacto_externo.agendar (começa o tempo de espera);
- passou a segurança ou bem-estar (ex.: a US12 que vira US08): agendar,
  porque só agora pode chegar ao contacto externo;
- passou a resolvida: contacto_externo.resolvida.

Quem decide se a classe chega ao contacto externo é o contacto_externo (US05).
"""

from __future__ import annotations

from typing import Callable, Protocol

from backend.contrato import Anomalia, Classe

CLASSES_DO_CONTACTO: set[Classe] = {"seguranca", "bem_estar"}


class ContactoExterno(Protocol):
    def agendar(self, anomalia: Anomalia) -> None: ...
    def cancelar(self, anomalia_id: str) -> None: ...
    def resolvida(self, anomalia: Anomalia) -> None: ...


class Avisos:
    def __init__(
        self,
        gravar: Callable[[Anomalia], None],
        enviar_ws: Callable[[Anomalia], None],
        contacto: ContactoExterno,
    ) -> None:
        self._gravar = gravar
        self._enviar_ws = enviar_ws
        self._contacto = contacto
        # O último estado e classe publicados de cada anomalia, para saber o que mudou.
        self._publicadas: dict[str, tuple[str, Classe]] = {}

    def publicar(self, anomalia: Anomalia) -> None:
        anterior = self._publicadas.get(anomalia.id)
        self._publicadas[anomalia.id] = (anomalia.estado, anomalia.classe)

        self._gravar(anomalia)
        self._enviar_ws(anomalia)

        if anterior is None:
            self._contacto.agendar(anomalia)
            return
        estado_antes, classe_antes = anterior
        if anomalia.estado == "resolvida" and estado_antes != "resolvida":
            self._contacto.resolvida(anomalia)
        elif (
            anomalia.estado == "ativa"
            and anomalia.classe in CLASSES_DO_CONTACTO
            and classe_antes not in CLASSES_DO_CONTACTO
        ):
            self._contacto.agendar(anomalia)


_padrao: Avisos | None = None


def configurar(avisos: Avisos) -> None:
    """Escolhe as peças (reais ou falsas) que o publicar() do módulo usa."""
    global _padrao
    _padrao = avisos


def reais() -> Avisos:
    """A gravação e o WebSocket reais; o contacto externo é o falso até o real existir (Candeias)."""
    from backend import anomalias, falsos, tempo_real

    return Avisos(gravar=anomalias.guardar, enviar_ws=tempo_real.enviar_anomalia, contacto=falsos.ContactoExterno())


def publicar(anomalia: Anomalia) -> None:
    if _padrao is None:
        configurar(reais())
    assert _padrao is not None
    _padrao.publicar(anomalia)
