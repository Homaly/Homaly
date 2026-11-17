"""avisos.publicar: toda a mudança a uma anomalia (nova, mudada ou resolvida) passa por aqui.

Grava a anomalia (anomalias.guardar), envia-a pelo WebSocket (tempo_real) e avisa o
contacto externo:
- anomalia nova e ativa: contacto_externo.agendar (começa o tempo de espera); uma que
  chega já resolvida sem ter sido vista (ex.: depois de um reinício) não avisa ninguém;
  com imediato=True (casa vazia), o contacto avisa já, sem o tempo de espera;
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
    def agendar(self, anomalia: Anomalia, imediato: bool = False) -> None: ...
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

    def publicar(self, anomalia: Anomalia, imediato: bool = False) -> None:
        """imediato: casa vazia (US07, US14); o contacto é avisado sem esperar o tempo de espera."""
        anterior = self._publicadas.get(anomalia.id)
        self._publicadas[anomalia.id] = (anomalia.estado, anomalia.classe)

        self._gravar(anomalia)
        self._enviar_ws(anomalia)

        if anterior is None:
            # Uma já resolvida que este processo nunca viu (resposta depois de um reinício,
            # anomalia de /dev) não agenda: seria um alerta ao contacto por algo já resolvido.
            if anomalia.estado == "ativa":
                self._contacto.agendar(anomalia, imediato=imediato)
            return
        estado_antes, classe_antes = anterior
        if anomalia.estado == "resolvida" and estado_antes != "resolvida":
            self._contacto.resolvida(anomalia)
        elif (
            anomalia.estado == "ativa"
            and anomalia.classe in CLASSES_DO_CONTACTO
            and classe_antes not in CLASSES_DO_CONTACTO
        ):
            self._contacto.agendar(anomalia, imediato=imediato)


_padrao: Avisos | None = None


def configurar(avisos: Avisos) -> None:
    """Escolhe as peças (reais ou falsas) que o publicar() do módulo usa."""
    global _padrao
    _padrao = avisos


def reais() -> Avisos:
    """A gravação e o WebSocket reais; o contacto externo é o falso até o real existir (Candeias)."""
    from backend import anomalias, falsos, tempo_real

    return Avisos(gravar=anomalias.guardar, enviar_ws=tempo_real.enviar_anomalia, contacto=falsos.ContactoExterno())


def publicar(anomalia: Anomalia, imediato: bool = False) -> None:
    if _padrao is None:
        configurar(reais())
    assert _padrao is not None
    _padrao.publicar(anomalia, imediato=imediato)
