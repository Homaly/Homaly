"""Saída de casa: a porta da rua abre e, nos SAIDA_MINUTOS (5) seguintes, nenhuma câmara interior
vê movimento. A casa assume então que a pessoa saiu.

As regras que precisam de saber se a pessoa saiu (US09, US11, US15) têm cada uma o seu `Vigia` e
dão-lhe todas as voltas. Cada volta devolve um `Visto`:

- `movimentos`: o movimento nas câmaras interiores nesta volta, com a divisão de cada câmara;
- `saiu`: a hora a que a porta abriu, na volta em que a janela acaba sem movimento;
- `sem_conclusao`: a hora a que a porta abriu, na volta em que a janela acaba sem que nenhuma
  câmara interior tenha dado leituras. A casa não sabe se a pessoa saiu: cada regra faz o que
  fazia antes de haver câmaras.

Se uma câmara interior vê movimento durante a janela, a pessoa não saiu (ou entrou alguém): a
janela acaba sem `saiu`. O movimento na própria volta em que a porta abre não conta: é, quase
sempre, quem vai a caminho da porta. A porta a abrir outra vez durante a janela recomeça-a.

Só contam a porta da rua (não as janelas) e as câmaras interiores (não as exteriores), pelo
inventário (backend.inventario). O movimento é o de backend.sinais (`sinais.movimento`; o formato
de `motionDetected` ainda está por confirmar), mesmo na primeira leitura de uma câmara: `true` é
movimento agora. A janela fica só em memória:
depois de um reinício, uma saída a meio perde-se.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from backend import inventario, sinais
from backend.formatos import Leitura
from backend.regras._comum import numero


def janela() -> timedelta:
    return timedelta(minutes=numero("SAIDA_MINUTOS", 5))


@dataclass(frozen=True)
class Movimento:
    divisao: str  # "a sala"
    em: datetime


@dataclass(frozen=True)
class Visto:
    movimentos: list[Movimento] = field(default_factory=list)
    porta_abriu: datetime | None = None  # a porta da rua abriu nesta volta
    saiu: datetime | None = None  # a hora da porta de uma saída que se concluiu nesta volta
    sem_conclusao: datetime | None = None  # a janela acabou sem câmaras: a hora da porta


class Vigia:
    def __init__(self) -> None:
        self._anteriores: dict[tuple[str, str], object] = {}
        self._porta_em: datetime | None = None  # a janela aberta: quando a porta abriu
        self._camaras_lidas = False  # alguma câmara interior deu leituras durante a janela

    @property
    def a_vigiar(self) -> bool:
        """A porta abriu há menos de SAIDA_MINUTOS e ainda não se sabe se a pessoa saiu."""
        return self._porta_em is not None

    def ver(self, leituras: list[Leitura], agora: datetime) -> Visto:
        abriu = False
        movimentos: list[Movimento] = []
        camaras = False
        for l in leituras:
            if l.dispositivo == "porta" and l.tipo == "sensorState" and _papel(l, inventario.PORTA_DA_RUA):
                anterior = self._trocar(l)
                abriu = abriu or (l.valor == "alarm" and anterior is not None and anterior != "alarm")
            elif l.dispositivo == "camara" and l.tipo == "motionDetected" and _papel(l, inventario.INTERIOR):
                camaras = True
                anterior = self._trocar(l)
                if sinais.movimento(l.valor, anterior):
                    movimentos.append(Movimento(inventario.de(l).divisao, agora))

        if abriu:
            # Uma janela nova (ou recomeçada); o movimento desta volta não conta.
            self._porta_em, self._camaras_lidas = agora, camaras
            return Visto(movimentos=movimentos, porta_abriu=agora)

        if self._porta_em is None:
            return Visto(movimentos=movimentos)
        porta_em = self._porta_em
        self._camaras_lidas = self._camaras_lidas or camaras
        if movimentos:
            self._porta_em = None  # alguém está em casa
            return Visto(movimentos=movimentos)
        if agora - porta_em < janela():
            return Visto()
        self._porta_em = None
        if self._camaras_lidas:
            return Visto(saiu=porta_em)
        return Visto(sem_conclusao=porta_em)

    def _trocar(self, leitura: Leitura) -> object:
        chave = (inventario.chave(leitura), leitura.tipo)
        anterior = self._anteriores.get(chave)
        self._anteriores[chave] = leitura.valor
        return anterior


def _papel(leitura: Leitura, papel: str) -> bool:
    return inventario.de(leitura).papel == papel
