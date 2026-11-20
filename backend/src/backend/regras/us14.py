"""US14: o aparelho na tomada ficou a gastar sem ninguém a usá-lo.

"A gastar" é instantPower acima de habitual.LIMITE_W. Além da tomada, a regra junta a saída de
casa (backend.saida) e o movimento das câmaras de dentro (`regras/presenca.py`) para saber se a
pessoa saiu, se está na divisão da tomada (a do inventário, backend.inventario) ou noutra. Por
ordem:

1. Casa vazia (férias ditas à casa): segurança e imediato, logo que gasta.
2. Movimento na divisão da tomada nos últimos PRESENCA_MINUTOS (10): alguém o está a usar, não
   avisa. Se já tinha avisado, resolve ("voltou a haver alguém na sala às HH:MM").
3. Aparelho que precisa de alguém por perto, e a pessoa saiu depois de o aparelho começar a
   gastar (a porta da rua abriu e nenhuma câmara de dentro viu movimento nos SAIDA_MINUTOS, 5,
   seguintes) há SAIU_MINUTOS (20). Eficiência, muito mais cedo do que o habitual. A espera é
   para as saídas curtas: no histórico há quem saia 20 min (o lixo, o café) com o aparelho
   ligado. Movimento numa câmara de dentro desfaz a saída (alguém está em casa), e a porta a
   abrir outra vez suspende-a até a nova janela da saída decidir (voltou, ou saiu outra vez).
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

Cada tomada tem o seu estado (desde quando gasta, se saíram depois disso), e a divisão de cada
uma vem do inventário. O ciclo identifica o aviso pela US, por isso há no máximo um aviso da US14
de cada vez: fica com a tomada que passou primeiro a merecê-lo (a que gasta há mais tempo, se
forem várias na mesma volta), e as outras esperam que esse acabe. Na volta em que acaba, nenhuma
outra avisa: o ciclo tem de fechar a anomalia antes de abrir outra. O desvio leva o id da tomada
(Desvio.dispositivo), para a ação "desligar a tomada" (US03) desligar essa e não outra.

Com uma só tomada, o aparelho é o que a pessoa disse à casa (contexto.aparelho_tomada). Com várias,
a conversa não diz de qual se trata: o aparelho é o nome da tomada no inventário ("Tomada da
máquina de lavar"), e é por esse nome que se vê se pode ficar sozinho.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta

from backend import habitual, inventario, saida
from backend.formatos import Contexto, Desvio, Leitura, Resolucao
from backend.regras import casa_vazia, com_a_casa_vazia, presenca

from ._comum import hora, numero

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

@dataclass
class _Tomada:
    id: str  # o id do MCP ("" sem id)
    desde: datetime  # desde quando está a gastar
    saiu_em: datetime | None = None  # saíram depois de começar a gastar (a hora da porta)
    avisado: Desvio | None = None  # o desvio em curso desta tomada: fica igual até se resolver


_tomadas: dict[str, _Tomada] = {}  # as tomadas a gastar, pela chave do inventário
_vistas: set[str] = set()  # todas as tomadas que já deram leituras
_dono: str | None = None  # a tomada do aviso em curso
_vigia = saida.Vigia()


def reiniciar() -> None:
    global _dono, _vigia
    _tomadas.clear()
    _vistas.clear()
    _dono = None
    _vigia = saida.Vigia()
    presenca.reiniciar()


def presenca_minutos() -> timedelta:
    return timedelta(minutes=numero("PRESENCA_MINUTOS", 10))


def saiu_minutos() -> timedelta:
    return timedelta(minutes=numero("SAIU_MINUTOS", 20))


def ausencia_minutos() -> timedelta:
    return timedelta(minutes=numero("AUSENCIA_MINUTOS", 60))


def precisa_de_alguem(aparelho: str | None) -> bool:
    """Se o aparelho não deve ficar a gastar sem ninguém por perto (um aquecedor, um ferro)."""
    if not aparelho:
        return True
    nome = _sem_acentos(aparelho.lower())
    return not any(s in nome for s in SOZINHOS)


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio | Resolucao]:
    global _dono
    presenca.ver(leituras, agora)
    visto = _vigia.ver(leituras, agora)  # todas as voltas, mesmo sem nenhum aparelho a gastar
    lidas = {inventario.chave(l): l for l in leituras if l.dispositivo == "tomada" and l.tipo == "instantPower"}
    _vistas.update(lidas)
    resolucao: Resolucao | None = None
    for chave, tomada in lidas.items():  # uma tomada sem leitura neste polling fica como estava
        if float(tomada.valor) > habitual.LIMITE_W:
            _tomadas.setdefault(chave, _Tomada(tomada.id, agora))
        elif chave in _tomadas:
            t = _tomadas.pop(chave)
            if _dono in (None, chave):  # sem aviso em curso, fecha o que o ciclo tiver de antes de um reinício
                _dono = None
                resolucao = Resolucao("US14", f"{_nome(t, contexto)} deixou de gastar às {hora(agora)}", agora)
    for t in _tomadas.values():
        if visto.saiu is not None and visto.saiu >= t.desde:
            t.saiu_em = visto.saiu
        elif visto.movimentos or visto.porta_abriu:
            t.saiu_em = None  # alguém em casa, ou a porta abriu outra vez (voltou?): a nova janela decide
    if resolucao is not None:
        return [resolucao]
    if not _tomadas:
        return []

    h = habitual.padrao()
    if casa_vazia(contexto, agora):
        _dono = _dono or min(_tomadas, key=lambda c: _tomadas[c].desde)
        t = _tomadas[_dono]
        return [Desvio(
            us="US14",
            classe="seguranca",
            resumo=f"{_maiuscula(_nome(t, contexto))} está a gastar desde as {t.desde:%H:%M}, {com_a_casa_vazia(contexto, agora)}.",
            habitual=h.texto_tomada(),
            imediato=True,
            dispositivo=t.id,
        )]

    com_cameras = presenca.ha_cameras_dentro()
    if _dono is not None:
        t = _tomadas[_dono]
        divisao, na_divisao = _divisao(t), presenca.ultimo_movimento(_divisao(t))
        if com_cameras and na_divisao is not None and agora - na_divisao <= presenca_minutos():
            avisado, t.avisado, _dono = t.avisado, None, None  # alguém o está a usar
            if avisado is None:
                return []
            return [Resolucao("US14", f"voltou a haver alguém {_em(divisao)} às {hora(na_divisao)}", agora)]
        t.avisado = t.avisado or _desvio(t, contexto, h, com_cameras, agora)
        if t.avisado is None:
            _dono = None  # o aviso de antes (com a casa vazia) acabou: o ciclo fecha-o nesta volta
            return []
        return [t.avisado]

    for chave, t in sorted(_tomadas.items(), key=lambda par: par[1].desde):
        na_divisao = presenca.ultimo_movimento(_divisao(t))
        if com_cameras and na_divisao is not None and agora - na_divisao <= presenca_minutos():
            continue  # alguém o está a usar
        if (desvio := _desvio(t, contexto, h, com_cameras, agora)) is not None:
            t.avisado, _dono = desvio, chave
            return [desvio]
    return []


def _desvio(t: _Tomada, contexto: Contexto, h: habitual.Habitual, com_cameras: bool, agora: datetime) -> Desvio | None:
    """O aviso desta tomada nesta volta, se já o merece."""
    nome = _maiuscula(_nome(t, contexto))
    if com_cameras and precisa_de_alguem(_aparelho(t, contexto)):
        return _saiu(t, nome, h, agora) or _ausente(t, nome, h, agora)
    if agora - t.desde >= h.limite_tomada:
        return Desvio(
            us="US14",
            classe="eficiencia",
            resumo=f"{nome} está a gastar desde as {t.desde:%H:%M}, há mais de {habitual.duracao(h.limite_tomada)} de seguida.",
            habitual=h.texto_tomada(),
            dispositivo=t.id,
        )
    return None


def _saiu(t: _Tomada, nome: str, h: habitual.Habitual, agora: datetime) -> Desvio | None:
    """Saíram de casa (backend.saida) depois de o aparelho começar a gastar."""
    if t.saiu_em is None or agora - t.saiu_em < saiu_minutos():
        return None
    return Desvio(
        us="US14",
        classe="eficiencia",
        resumo=(
            f"{nome} está a gastar desde as {t.desde:%H:%M}, e parece que saíram de casa às "
            f"{hora(t.saiu_em)}: a porta da rua abriu e as câmaras não viram ninguém a seguir."
        ),
        habitual=h.texto_tomada(),
        dispositivo=t.id,
    )


def _ausente(t: _Tomada, nome: str, h: habitual.Habitual, agora: datetime) -> Desvio | None:
    """Ninguém na divisão da tomada há AUSENCIA_MINUTOS."""
    divisao = _divisao(t)
    na_divisao = presenca.ultimo_movimento(divisao)
    desde = max(na_divisao, t.desde) if na_divisao is not None else t.desde
    if agora - desde < ausencia_minutos():
        return None
    outras = presenca.onde_desde(desde, exceto=divisao)
    noutras = f" (há movimento {_juntar([_em(d) for d in outras])})" if outras else ""
    return Desvio(
        us="US14",
        classe="eficiencia",
        resumo=f"{nome} está a gastar e não há ninguém {_em(divisao)} desde as {hora(desde)}{noutras}.",
        habitual=h.texto_tomada(),
        dispositivo=t.id,
    )


def _dispositivo(t: _Tomada) -> inventario.Dispositivo:
    return inventario.de(Leitura("tomada", "instantPower", 0.0, datetime.min, t.id))


def _divisao(t: _Tomada) -> str:
    return _dispositivo(t).divisao


def _aparelho(t: _Tomada, contexto: Contexto) -> str | None:
    """O aparelho na tomada: o da conversa com uma só tomada, o nome do inventário com várias."""
    if len(_vistas) <= 1:
        return contexto.aparelho_tomada
    return _dispositivo(t).nome


def _nome(t: _Tomada, contexto: Contexto) -> str:
    """Para os textos, em minúsculas: "o aquecedor", "o aparelho na tomada", "a tomada do quarto"."""
    if len(_vistas) <= 1:
        return contexto.aparelho_tomada or "o aparelho na tomada"
    nome = _dispositivo(t).nome
    return f"a {nome[:1].lower()}{nome[1:]}"


def _maiuscula(texto: str) -> str:
    return texto[:1].upper() + texto[1:]


def _em(divisao: str) -> str:
    """'a sala' -> 'na sala'; 'o quarto' -> 'no quarto' (a divisão vem com o artigo, do inventário)."""
    return inventario.com_preposicao("em", divisao)


def _juntar(partes: list[str]) -> str:
    return partes[0] if len(partes) == 1 else f"{', '.join(partes[:-1])} e {partes[-1]}"


def _sem_acentos(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
