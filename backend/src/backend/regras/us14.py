"""US14: o aparelho na tomada ficou a gastar sem ninguém a usá-lo.

"A gastar" é instantPower acima de habitual.LIMITE_W. Além da tomada, a regra junta a porta e
o movimento das câmaras de dentro (`regras/presenca.py`) para saber se a pessoa saiu, se está
na divisão da tomada (TOMADA_DIVISAO, `sala` por omissão) ou noutra. Por ordem:

1. Casa vazia (férias ditas à casa): segurança e imediato, logo que gasta.
2. Movimento na divisão da tomada nos últimos PRESENCA_MINUTOS (10): alguém o está a usar, não
   avisa. Se já tinha avisado, resolve ("voltou a haver alguém na sala às HH:MM").
3. Aparelho que precisa de alguém por perto, e a pessoa saiu: a porta abriu e fechou depois de o
   aparelho começar a gastar e não há movimento em nenhuma câmara de dentro desde que fechou, há
   SAIU_MINUTOS (20). Eficiência, muito mais cedo do que o habitual. A porta não distingue entrar
   de sair: quem acabou de chegar e se sentou também fica uns minutos sem se mexer (no histórico,
   até 14 min), daí os 20 min por omissão (na demo pode baixar-se).
4. Aparelho que precisa de alguém por perto, e ninguém na divisão há AUSENCIA_MINUTOS (60),
   contados do último movimento lá ou de quando começou a gastar: eficiência. Quem está sentado
   (a ver televisão) quase não se mexe: no histórico há até 47 min sem movimento com o aparelho
   em uso, daí os 60 min por omissão (na demo pode baixar-se).
5. Sem câmaras de dentro, ou aparelho que pode ficar sozinho (a máquina de lavar): eficiência a
   partir de 3x o período mais longo do histórico, como antes.

O aparelho é o nome da tomada, que a casa sabe pela conversa (contexto.aparelho_tomada). Os que
podem ficar sozinhos estão em SOZINHOS; um nome desconhecido, ou nenhum, precisa de alguém.

Quando o aparelho deixa de gastar, a regra devolve a Resolucao ("deixou de gastar às HH:MM").
O resumo não muda enquanto o desvio dura (fica o primeiro), para o ciclo não voltar a publicar
a cada polling.
"""

from __future__ import annotations

import os
import unicodedata
from datetime import datetime, timedelta

from backend import habitual
from backend.formatos import Contexto, Desvio, Leitura, Resolucao
from backend.regras import casa_vazia, com_a_casa_vazia, presenca

from ._comum import hora, numero, ultima

# Aparelhos que podem ficar a trabalhar sem ninguém por perto (sem acentos, em minúsculas).
SOZINHOS = (
    "maquina de lavar",
    "maquina da loica",
    "maquina de loica",
    "maquina da louca",
    "maquina de louca",
    "maquina de secar",
    "frigorifico",
    "arca",
    "congelador",
    "carregador",
    "router",
    "desumidificador",
    "aquario",
)

# Divisões que levam "no" em vez de "na".
_MASCULINAS = {"quarto", "escritorio", "corredor", "hall", "sotao", "atelier"}

_desde: datetime | None = None  # desde quando o aparelho está a gastar
_porta: str | None = None  # a última leitura da porta: 'alarm', 'normal' ou None
_abriu_em: datetime | None = None  # a porta abriu depois de o aparelho começar a gastar
_fechou_em: datetime | None = None  # e voltou a fechar
_avisado: Desvio | None = None  # o desvio em curso: fica igual até se resolver


def reiniciar() -> None:
    global _desde, _porta, _abriu_em, _fechou_em, _avisado
    _desde = _porta = _abriu_em = _fechou_em = _avisado = None
    presenca.reiniciar()


def presenca_minutos() -> timedelta:
    return timedelta(minutes=numero("PRESENCA_MINUTOS", 10))


def saiu_minutos() -> timedelta:
    return timedelta(minutes=numero("SAIU_MINUTOS", 20))


def ausencia_minutos() -> timedelta:
    return timedelta(minutes=numero("AUSENCIA_MINUTOS", 60))


def divisao_da_tomada() -> str:
    return os.environ.get("TOMADA_DIVISAO", "").strip().lower() or "sala"


def precisa_de_alguem(aparelho: str | None) -> bool:
    """Se o aparelho não deve ficar a gastar sem ninguém por perto (um aquecedor, um ferro)."""
    if not aparelho:
        return True
    nome = _sem_acentos(aparelho.lower())
    return not any(s in nome for s in SOZINHOS)


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio | Resolucao]:
    global _desde, _avisado
    presenca.ver(leituras, agora)
    potencia = ultima(leituras, "tomada", "instantPower")
    if potencia is not None:  # sem leitura da tomada neste polling: fica como estava
        if float(potencia) > habitual.LIMITE_W:
            if _desde is None:
                _comecou(agora)
        elif _desde is not None:
            _desde = _avisado = None
            nome = contexto.aparelho_tomada or "o aparelho na tomada"
            _ver_porta(leituras, agora)
            return [Resolucao("US14", f"{nome} deixou de gastar às {hora(agora)}", agora)]
    _ver_porta(leituras, agora)
    if _desde is None:
        return []

    h = habitual.padrao()
    nome = contexto.aparelho_tomada or "o aparelho na tomada"
    nome = nome[0].upper() + nome[1:]
    if casa_vazia(contexto, agora):
        return [Desvio(
            us="US14",
            classe="seguranca",
            resumo=f"{nome} está a gastar desde as {_desde:%H:%M}, {com_a_casa_vazia(contexto, agora)}.",
            habitual=h.texto_tomada(),
            imediato=True,
        )]

    divisao = divisao_da_tomada()
    com_cameras = presenca.ha_cameras_dentro()
    na_divisao = presenca.ultimo_movimento(divisao)
    if com_cameras and na_divisao is not None and agora - na_divisao <= presenca_minutos():
        if _avisado is None:
            return []
        _avisado = None  # alguém o está a usar
        return [Resolucao("US14", f"voltou a haver alguém {_na(divisao)} às {hora(na_divisao)}", agora)]
    if _avisado is not None:
        return [_avisado]

    if com_cameras and precisa_de_alguem(contexto.aparelho_tomada):
        _avisado = _saiu(nome, h, agora) or _ausente(nome, h, divisao, na_divisao, agora)
    elif agora - _desde >= h.limite_tomada:
        _avisado = Desvio(
            us="US14",
            classe="eficiencia",
            resumo=f"{nome} está a gastar desde as {_desde:%H:%M}, há mais de {habitual.duracao(h.limite_tomada)} de seguida.",
            habitual=h.texto_tomada(),
        )
    return [_avisado] if _avisado else []


def _comecou(agora: datetime) -> None:
    """O aparelho começou a gastar: a porta como está agora não conta como "abriu depois"."""
    global _desde, _abriu_em, _fechou_em, _avisado
    _desde, _abriu_em, _fechou_em, _avisado = agora, None, None, None


def _ver_porta(leituras: list[Leitura], agora: datetime) -> None:
    """Abriu e fechou depois de o aparelho começar a gastar (como a US11 com a luz)."""
    global _porta, _abriu_em, _fechou_em
    porta = ultima(leituras, "porta", "sensorState")
    if porta not in ("alarm", "normal"):
        return
    if _desde is not None:
        if porta == "alarm" and _porta != "alarm":
            _abriu_em, _fechou_em = agora, None  # uma saída (ou entrada) nova
        elif porta == "normal" and _abriu_em is not None and _fechou_em is None:
            _fechou_em = agora
    _porta = porta


def _saiu(nome: str, h: habitual.Habitual, agora: datetime) -> Desvio | None:
    """A porta fechou depois de o aparelho ligar e desde então ninguém se mexe em casa."""
    if _fechou_em is None or agora - _fechou_em < saiu_minutos():
        return None
    ultimo = presenca.ultimo_movimento()
    if ultimo is not None and ultimo > _fechou_em:
        return None
    return Desvio(
        us="US14",
        classe="eficiencia",
        resumo=(
            f"{nome} está a gastar desde as {_desde:%H:%M}, e a porta fechou às {hora(_fechou_em)} "
            "sem movimento em casa desde então: parece que saíram."
        ),
        habitual=h.texto_tomada(),
    )


def _ausente(
    nome: str, h: habitual.Habitual, divisao: str, na_divisao: datetime | None, agora: datetime
) -> Desvio | None:
    """Ninguém na divisão da tomada há AUSENCIA_MINUTOS."""
    assert _desde is not None
    desde = max(na_divisao, _desde) if na_divisao is not None else _desde
    if agora - desde < ausencia_minutos():
        return None
    outras = presenca.onde_desde(desde, exceto=divisao)
    noutras = f" (há movimento {_juntar([_na(d) for d in outras])})" if outras else ""
    return Desvio(
        us="US14",
        classe="eficiencia",
        resumo=f"{nome} está a gastar e não há ninguém {_na(divisao)} desde as {hora(desde)}{noutras}.",
        habitual=h.texto_tomada(),
    )


def _na(divisao: str) -> str:
    """'na sala', 'no quarto'."""
    return f"{'no' if _sem_acentos(divisao) in _MASCULINAS else 'na'} {divisao}"


def _juntar(partes: list[str]) -> str:
    return partes[0] if len(partes) == 1 else f"{', '.join(partes[:-1])} e {partes[-1]}"


def _sem_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
