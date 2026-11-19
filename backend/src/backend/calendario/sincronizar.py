"""Ler o calendário: quando liga, de hora a hora (numa thread) e quando a pessoa pede.

Uma leitura que falha não apaga nada: ficam os itens da anterior e o erro aparece nas
Definições (por exemplo, quando a Google corta o acesso ao fim de 7 dias em modo de teste).
"""

import logging
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx

from backend.calendario import armazem, extrair, google
from backend.ia.modelo import Modelo

registo = logging.getLogger(__name__)

INTERVALO = timedelta(hours=1)
JANELA_ANTES = timedelta(days=1)
JANELA_DEPOIS = timedelta(days=90)
COMPROMISSOS_ATE = timedelta(days=14)
# A casa é em Portugal. Um desvio fixo (+00:00) não sabe da hora de verão: as férias de agosto
# lidas em novembro ficavam uma hora ao lado.
FUSO_DA_CASA = ZoneInfo("Europe/Lisbon")


def sincronizar(agora: datetime, modelo: Modelo, *, cliente: httpx.Client | None = None) -> bool:
    """Lê o calendário e guarda o que a casa tirou dele. `False` se não há ligação ou falhou."""
    ligacao = armazem.ligacao()
    credenciais = google.credenciais()
    if ligacao is None or credenciais is None:
        return False
    try:
        token = google.token_de_acesso(credenciais, ligacao.refresh_token, cliente=cliente)
        brutos = google.listar_eventos(token, agora - JANELA_ANTES, agora + JANELA_DEPOIS, cliente=cliente)
    except google.ErroGoogle as erro:
        registo.warning("Não foi possível ler o calendário: %s", erro)
        armazem.guardar_erro(_frase_do_erro(str(erro)))
        return False
    fuso = agora.tzinfo if isinstance(agora.tzinfo, ZoneInfo) else FUSO_DA_CASA
    eventos = extrair.ler_eventos(brutos, fuso)
    itens = extrair.extrair(eventos, agora.astimezone(fuso), modelo)
    itens.compromissos = [
        c for c in itens.compromissos if agora - JANELA_ANTES <= c.fim and c.inicio <= agora + COMPROMISSOS_ATE
    ]
    if not armazem.guardar_leitura(itens, agora):
        registo.info("Calendário removido durante a leitura; não se guardou nada.")
        return False
    registo.info("Calendário lido: %d eventos, %d itens", len(eventos), len(itens))
    return True


def arrancar(obter_agora, obter_modelo) -> threading.Event:
    """Lê o calendário de hora a hora (hora real), numa thread. `set()` no evento devolvido pára."""
    parar = threading.Event()

    def correr() -> None:
        while not parar.wait(INTERVALO.total_seconds()):
            try:
                sincronizar(obter_agora(), obter_modelo())
            except Exception:  # noqa: BLE001 — a thread não pode morrer; tenta na próxima hora
                registo.exception("A leitura do calendário falhou")

    threading.Thread(target=correr, name="calendario", daemon=True).start()
    return parar


def _frase_do_erro(erro: str) -> str:
    if any(sinal in erro for sinal in ("invalid_grant", "(401)", "(403)")):
        return "A Google deixou de dar acesso ao calendário. Ligue outra vez."
    return "Não foi possível ler o calendário. A casa tenta outra vez dentro de uma hora."
