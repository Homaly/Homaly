"""`/calendario`: o estado da ligação, ligar à Google, ler outra vez e remover.

Ligar é uma navegação, não um pedido da PWA: `GET /calendario/google/ligar` manda o browser para
a Google e `GET /calendario/google/retorno` volta para `APP_URL/definicoes?calendario=ligado`
(ou `=erro`), onde a PWA mostra a mensagem.

O retorno só aceita o browser que começou: o `state` vai também num cookie, e o código só se
troca com o verificador PKCE que ficou no servidor. Assim ninguém liga à casa o calendário dele
mandando à pessoa um link de retorno já feito.
"""

import logging
import os
import secrets
import time as relogio_real
from datetime import datetime

import httpx
from fastapi import APIRouter, Cookie, Depends, HTTPException
from fastapi.responses import RedirectResponse

from backend.calendario import armazem, google
from backend.calendario.sincronizar import sincronizar
from backend.conversa.interpretar import DIAS_DA_SEMANA
from backend.dependencias import obter_agora, obter_modelo_dep
from backend.formatos import Compromisso, Periodo, Rotina
from backend.ia.modelo import Modelo

registo = logging.getLogger(__name__)

APP_URL_POR_OMISSAO = "http://localhost:5173"
VALIDADE_STATE_S = 10 * 60
COOKIE_STATE = "homaly_calendario_state"
INTERVALO_LER_AGORA_S = 30  # "Ler agora" gasta a Google e a IA: no máximo uma vez por meio minuto
MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]  # fmt: skip

# state → (quando expira, verificador PKCE), em hora real. Um processo só; perde-se ao reiniciar,
# e aí liga-se outra vez.
_pedidos: dict[str, tuple[float, str]] = {}
_ultima_leitura_pedida: float | None = None  # hora real (monotónica) do último "Ler agora"

router = APIRouter(prefix="/calendario", tags=["calendário"])


def obter_cliente_google() -> httpx.Client | None:
    """`None` usa o `httpx` direto; os testes trocam-no por um cliente falso."""
    return None


@router.get("")
def pedir_estado(agora: datetime = Depends(obter_agora)) -> dict:
    return estado(agora)


@router.get("/google/ligar")
def ligar() -> RedirectResponse:
    credenciais = google.credenciais()
    if credenciais is None:
        registo.warning("Calendário: faltam GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET no .env")
        return _voltar("erro")
    state = secrets.token_urlsafe(24)
    verificador = google.novo_verificador()
    _limpar_pedidos()
    _pedidos[state] = (relogio_real.monotonic() + VALIDADE_STATE_S, verificador)
    resposta = RedirectResponse(google.url_autorizar(credenciais, state, verificador), status_code=303)
    resposta.set_cookie(
        COOKIE_STATE,
        state,
        max_age=VALIDADE_STATE_S,
        httponly=True,
        samesite="lax",  # a Google devolve a pessoa com uma navegação normal: o cookie vai
        secure=credenciais.redirect_uri.startswith("https://"),
    )
    return resposta


@router.get("/google/retorno")
def retorno(
    state: str = "",
    code: str = "",
    error: str = "",
    homaly_calendario_state: str = Cookie(default=""),
    agora: datetime = Depends(obter_agora),
    modelo: Modelo = Depends(obter_modelo_dep),
    cliente: httpx.Client | None = Depends(obter_cliente_google),
) -> RedirectResponse:
    credenciais = google.credenciais()
    mesmo_browser = bool(state) and secrets.compare_digest(state, homaly_calendario_state)
    pedido = _pedidos.pop(state, None) if mesmo_browser else None
    valido = pedido is not None and pedido[0] > relogio_real.monotonic()
    if error or not code or not valido or credenciais is None:
        registo.warning(
            "Calendário: ligação recusada (erro=%r, mesmo browser=%s, state válido=%s)", error, mesmo_browser, valido
        )
        return _voltar("erro")
    try:
        ligacao = google.trocar_codigo(credenciais, code, pedido[1], cliente=cliente)
    except google.ErroGoogle as erro:
        registo.warning("Calendário: %s", erro)
        return _voltar("erro")
    armazem.guardar_ligacao(ligacao.email, ligacao.refresh_token, agora)
    try:
        sincronizar(agora, modelo, cliente=cliente)  # se falhar, fica ligado e o erro aparece
    except Exception:  # noqa: BLE001 — já está ligado; a próxima leitura tenta outra vez
        registo.exception("Calendário: a primeira leitura falhou")
        armazem.guardar_erro("Não foi possível ler o calendário. A casa tenta outra vez dentro de uma hora.")
    return _voltar("ligado")


@router.post("/sincronizar")
def pedir_sincronizar(
    agora: datetime = Depends(obter_agora),
    modelo: Modelo = Depends(obter_modelo_dep),
    cliente: httpx.Client | None = Depends(obter_cliente_google),
) -> dict:
    global _ultima_leitura_pedida
    if armazem.ligacao() is None:
        raise HTTPException(409, "O calendário não está ligado.")
    agora_real = relogio_real.monotonic()
    # Sem leitura pedida antes, lê sempre: o relógio monotónico conta desde o arranque da máquina,
    # que pode ter sido há menos de 30 s (um servidor ou a CI acabados de ligar).
    if _ultima_leitura_pedida is None or agora_real - _ultima_leitura_pedida >= INTERVALO_LER_AGORA_S:
        _ultima_leitura_pedida = agora_real
        sincronizar(agora, modelo, cliente=cliente)
    return estado(agora)


@router.delete("")
def remover(
    agora: datetime = Depends(obter_agora),
    cliente: httpx.Client | None = Depends(obter_cliente_google),
) -> dict:
    ligacao = armazem.ligacao()
    if ligacao is not None and not google.revogar(ligacao.refresh_token, cliente=cliente):
        registo.warning("Calendário: a Google não confirmou a revogação; apaga-se na mesma.")
    armazem.apagar_tudo()
    return estado(agora)


def estado(agora: datetime) -> dict:
    ligacao = armazem.ligacao()
    itens = armazem.itens() if ligacao else armazem.Itens()
    return {
        "configurado": google.credenciais() is not None,
        "ligado": ligacao is not None,
        "email": ligacao.email if ligacao else None,
        "lidoEm": ligacao.lido_em.isoformat() if ligacao and ligacao.lido_em else None,
        "erro": ligacao.erro if ligacao else None,
        "itens": [{"tipo": "ferias", "texto": texto_ferias(p, agora)} for p in sorted(itens.ferias, key=lambda p: p.inicio)]
        + [{"tipo": "rotina", "texto": texto_rotina(r)} for r in itens.rotinas]
        + [
            {"tipo": "compromisso", "texto": texto_compromisso(c, agora)}
            for c in sorted(itens.compromissos, key=lambda c: c.inicio)
        ],
    }


def texto_ferias(p: Periodo, agora: datetime) -> str:
    inicio, fim = _local(p.inicio, agora), _local(p.fim, agora)
    if inicio.date() == fim.date():
        return f"{p.motivo}: {_dia(inicio)}"
    return f"{p.motivo}: de {_dia(inicio)} a {_dia(fim)}"


def texto_rotina(r: Rotina) -> str:
    if sorted(r.dias) == list(range(7)):
        dias = "todos os dias"
    elif sorted(r.dias) == [0, 1, 2, 3, 4]:
        dias = "dias úteis"
    else:
        nomes = [DIAS_DA_SEMANA[d] for d in sorted(r.dias)]
        dias = nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]
    return f"{r.descricao}: {dias}" + (f", às {r.hora:%H:%M}" if r.hora else "")


def texto_compromisso(c: Compromisso, agora: datetime) -> str:
    inicio, fim = _local(c.inicio, agora), _local(c.fim, agora)
    dias = (inicio.date() - agora.date()).days
    quando = "hoje" if dias == 0 else "amanhã" if dias == 1 else _dia(inicio)
    return f"{c.descricao}: {quando}, das {inicio:%H:%M} às {fim:%H:%M}"


def _local(d: datetime, agora: datetime) -> datetime:
    return d.astimezone(agora.tzinfo) if d.tzinfo and agora.tzinfo else d


def _dia(d: datetime) -> str:
    return f"{d.day} de {MESES[d.month - 1]}"


def _voltar(resultado: str) -> RedirectResponse:
    app_url = (os.environ.get("APP_URL") or APP_URL_POR_OMISSAO).rstrip("/")
    resposta = RedirectResponse(f"{app_url}/definicoes?calendario={resultado}", status_code=303)
    resposta.delete_cookie(COOKIE_STATE)
    return resposta


def _limpar_pedidos() -> None:
    agora = relogio_real.monotonic()
    for state in [s for s, (expira, _) in _pedidos.items() if expira <= agora]:
        del _pedidos[state]
