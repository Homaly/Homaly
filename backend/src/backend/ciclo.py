"""O ciclo: a cada polling, lê os dispositivos, corre todas as regras, passa
cada desvio novo à IA e publica.

Uma ocorrência é o desvio de uma US desde que a regra o começa a ver até deixar
de o ver. Comportamento decidido a 2026-11-17:

- a IA avalia cada ocorrência uma só vez; se disser que não vale a pena,
  fica no histórico e não volta à IA até a ocorrência acabar;
- com um silêncio ativo para a US, não vai à IA, mas fica no histórico;
- com a anomalia já ativa, não volta à IA; se a classe ou o resumo mudarem
  (a junção US08+US12, feita nas regras), atualiza-se com o resumo da regra;
- quando o desvio desaparece, a anomalia ativa resolve-se sozinha, exceto as de
  SO_COM_RESPOSTA, que esperam pela resposta. Se a regra devolveu uma Resolucao
  (ex.: "a porta fechou às 14:12"), é esse o texto; senão, um texto genérico.

Uso:
  uv run python -m backend.ciclo <ficheiro.csv>   # reproduz um CSV; o 'agora' é a hora das leituras
  uv run python -m backend.ciclo --ao-vivo        # um polling a cada POLLING_SEGUNDOS, com o relógio
                                                  # de backend.relogio (RELOGIO_INICIO, RELOGIO_FATOR)
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Literal

from backend.contrato import Anomalia, TextoEm
from backend.formatos import Contexto, Desvio, Leitura, Resolucao
from backend.relogio import Relogio

Regra = Callable[[list[Leitura], Contexto, datetime], list[Desvio | Resolucao]]

# Histórias cuja anomalia só se resolve com a resposta do responsável.
SO_COM_RESPOSTA = {"US07"}


@dataclass
class Ocorrencia:
    desvio: Desvio
    estado: Literal["ativa", "ignorada", "silenciada", "respondida"]
    anomalia: Anomalia | None = None


def carregar_regras() -> list[Regra]:
    """Todas as funções verificar() dos ficheiros em backend/regras/."""
    from backend import regras

    encontradas = []
    for modulo in pkgutil.iter_modules(regras.__path__):
        m = importlib.import_module(f"backend.regras.{modulo.name}")
        if hasattr(m, "verificar"):
            encontradas.append(m.verificar)
    return encontradas


def silenciado(desvio: Desvio, contexto: Contexto, agora: datetime) -> bool:
    return any(
        s.us == desvio.us and (s.ate is None or s.ate > agora) for s in contexto.silencios
    )


class Ciclo:
    def __init__(
        self,
        regras: list[Regra],
        avaliar: Callable[[Desvio, Contexto], Anomalia | None],
        publicar: Callable[[Anomalia], None],
        obter_contexto: Callable[[], Contexto],
        registar_historico: Callable[[Desvio, str, datetime], None],
    ) -> None:
        self.regras = regras
        self.avaliar = avaliar
        self.publicar = publicar
        self.obter_contexto = obter_contexto
        self.registar_historico = registar_historico
        self.ocorrencias: dict[str, Ocorrencia] = {}

    def passo(self, leituras: list[Leitura], agora: datetime) -> None:
        contexto = self.obter_contexto()
        desvios: dict[str, Desvio] = {}
        resolucoes: dict[str, Resolucao] = {}
        for regra in self.regras:
            for saida in regra(leituras, contexto, agora):
                if isinstance(saida, Resolucao):
                    resolucoes[saida.us] = saida
                else:
                    desvios[saida.us] = saida
        for us in resolucoes:
            desvios.pop(us, None)  # a regra disse que acabou

        self._acabar_ocorrencias(desvios, resolucoes, agora)
        for us, desvio in desvios.items():
            ocorrencia = self.ocorrencias.get(us)
            if ocorrencia is None:
                self._nova_ocorrencia(desvio, contexto, agora)
            elif ocorrencia.estado == "ativa":
                self._continuar(ocorrencia, desvio)

    def respondida(self, anomalia_id: str) -> None:
        """O responsável resolveu a anomalia; a ocorrência fica fechada até o desvio desaparecer."""
        for ocorrencia in self.ocorrencias.values():
            if ocorrencia.anomalia is not None and ocorrencia.anomalia.id == anomalia_id:
                ocorrencia.estado = "respondida"

    def _nova_ocorrencia(self, desvio: Desvio, contexto: Contexto, agora: datetime) -> None:
        if silenciado(desvio, contexto, agora):
            self.ocorrencias[desvio.us] = Ocorrencia(desvio, "silenciada")
            self.registar_historico(desvio, "silenciado pelo responsável", agora)
            return
        anomalia = self.avaliar(desvio, contexto)
        if anomalia is None:
            self.ocorrencias[desvio.us] = Ocorrencia(desvio, "ignorada")
            self.registar_historico(desvio, "a IA decidiu não avisar", agora)
            return
        anomalia.detetada_em = agora
        self.ocorrencias[desvio.us] = Ocorrencia(desvio, "ativa", anomalia)
        self.publicar(anomalia)

    def _continuar(self, ocorrencia: Ocorrencia, desvio: Desvio) -> None:
        anterior = ocorrencia.desvio
        ocorrencia.desvio = desvio
        if (desvio.classe, desvio.resumo) == (anterior.classe, anterior.resumo):
            return
        assert ocorrencia.anomalia is not None
        ocorrencia.anomalia.classe = desvio.classe
        ocorrencia.anomalia.explicacao = desvio.resumo
        self.publicar(ocorrencia.anomalia)

    def _acabar_ocorrencias(
        self, desvios: dict[str, Desvio], resolucoes: dict[str, Resolucao], agora: datetime
    ) -> None:
        for us in [us for us in self.ocorrencias if us not in desvios]:
            ocorrencia = self.ocorrencias.pop(us)
            resolucao = resolucoes.get(us)
            if ocorrencia.estado != "ativa" or (resolucao is None and us in SO_COM_RESPOSTA):
                continue
            assert ocorrencia.anomalia is not None
            ocorrencia.anomalia.estado = "resolvida"
            if resolucao is not None:
                ocorrencia.anomalia.resolucao = TextoEm(texto=resolucao.texto, em=resolucao.em)
            else:
                ocorrencia.anomalia.resolucao = TextoEm(texto=f"Resolvida sozinha às {agora:%H:%M}.", em=agora)
            self.publicar(ocorrencia.anomalia)


def correr(ciclo: Ciclo, lotes: Iterable[tuple[datetime, list[Leitura]]]) -> None:
    """Corre um passo por lote de leituras; o 'agora' é a hora das leituras."""
    for agora, leituras in lotes:
        ciclo.passo(leituras, agora)


def ao_vivo(
    ciclo: Ciclo,
    ler: Callable[[], list[Leitura]],
    relogio: Relogio,
    intervalo: float,
    passos: int | None = None,
    dormir: Callable[[float], None] = time.sleep,
) -> None:
    """Um polling a cada intervalo segundos reais; o 'agora' é o do relógio (talvez acelerado).

    As regras usam o 'agora', não a hora das leituras, por isso a hora simulada chega a todas.
    passos limita o número de pollings (para os testes); None corre para sempre.
    """
    n = 0
    while passos is None or n < passos:
        ciclo.passo(ler(), relogio.agora())
        n += 1
        if passos is None or n < passos:
            dormir(intervalo)


def main(argv: list[str]) -> None:
    from backend import avisos, dispositivos, falsos

    avisos.configurar(falsos.avisos())  # por agora, com as peças falsas: só escreve no terminal
    if len(argv) != 1:
        sys.exit("uso: python -m backend.ciclo <ficheiro.csv> | --ao-vivo")
    ciclo = Ciclo(
        regras=carregar_regras(),
        avaliar=falsos.avaliar,
        publicar=avisos.publicar,
        obter_contexto=falsos.obter_contexto,
        registar_historico=falsos.registar_historico,
    )
    if argv[0] == "--ao-vivo":
        relogio = Relogio.do_ambiente()
        intervalo = dispositivos.intervalo_s()
        print(f"ciclo ao vivo: polling a cada {intervalo:g} s, a começar às {relogio.agora():%Y-%m-%d %H:%M}")
        ao_vivo(ciclo, falsos.ler, relogio, intervalo)
    else:
        correr(ciclo, falsos.ler_csv(argv[0]))


if __name__ == "__main__":
    main(sys.argv[1:])
