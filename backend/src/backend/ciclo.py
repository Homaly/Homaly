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

Com as peças reais, o ciclo corre numa thread dentro da app (backend.main), só com
CICLO=1: lê a casa pelo MCP, usa a IA, o contexto e o histórico da base de dados e
publica pelo avisos.publicar (o WebSocket só chega à PWA a partir do processo da app).
Antes de mexer numa anomalia, lê o estado dela na base de dados: se o responsável já a
resolveu (resposta ou ação), a ocorrência fecha-se e o ciclo não a reescreve.

Na linha de comandos, só com as peças falsas (escreve no terminal):
  uv run python -m backend.ciclo <ficheiro.csv>   # reproduz um CSV; o 'agora' é a hora das leituras
  uv run python -m backend.ciclo --ao-vivo        # um polling a cada POLLING_SEGUNDOS, com o relógio
                                                  # de backend.relogio (RELOGIO_INICIO, RELOGIO_FATOR)
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
import sys
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Literal

from backend.contrato import Anomalia, TextoEm
from backend.dispositivos.mcp import ErroDispositivos
from backend.formatos import Contexto, Desvio, Leitura, Resolucao
from backend.ia.avaliar import explicacao_do_desvio
from backend.regras._comum import com_fuso
from backend.relogio import Relogio, partilhado

registo = logging.getLogger(__name__)

Regra = Callable[[list[Leitura], Contexto, datetime], list[Desvio | Resolucao]]

# Histórias cuja anomalia só se resolve com a resposta do responsável.
SO_COM_RESPOSTA = {"US07"}

# Histórias que não se reconstroem depois de um reinício: só disparam num momento (US07: a
# abertura; US09: a hora limite do dia) e não voltam a ver o mesmo desvio, por isso não duplicam.
# Reconstruí-las engolia o desvio seguinte (a madrugada da noite seguinte, o dia seguinte).
NAO_RECONSTRUIR = {"US07", "US09"}


@dataclass
class Ocorrencia:
    desvio: Desvio
    estado: Literal["ativa", "ignorada", "silenciada", "respondida"]
    anomalia: Anomalia | None = None
    # Vem de antes de um reinício (Ciclo.restaurar): a regra pode estar calada até voltar a
    # contar (a US14 guarda o estado em memória), por isso só se fecha com uma Resolucao da regra
    # ou com a resposta do responsável, nunca por a regra não a ver.
    reconstruida: bool = False


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
    """Um silêncio dessa US. Um temporário (com 'ate') nunca cala segurança: só uma regra
    recorrente explícita (sem 'ate') o faz, como no DECISIONS.md (ex.: recusar desligar a
    tomada silencia a US14 até ao fim do dia, mas com a casa vazia a US14 é segurança e avisa)."""
    return any(
        s.us == desvio.us
        and (s.ate is None or (desvio.classe != "seguranca" and com_fuso(s.ate) > com_fuso(agora)))
        for s in contexto.silencios
    )


def _passou_a_seguranca(ocorrencia: Ocorrencia, desvio: Desvio) -> bool:
    """Ex.: a tomada já gastava (eficiência, silenciada ou ignorada pela IA) e a casa ficou vazia."""
    return (
        ocorrencia.estado in ("silenciada", "ignorada")
        and desvio.classe == "seguranca"
        and ocorrencia.desvio.classe != "seguranca"
    )


class Ciclo:
    def __init__(
        self,
        regras: list[Regra],
        avaliar: Callable[[Desvio, Contexto], Anomalia | None],
        publicar: Callable[..., None],  # publicar(anomalia, imediato=False), como avisos.publicar
        obter_contexto: Callable[[], Contexto],
        registar_historico: Callable[[Desvio, str, datetime], None],
        obter_anomalia: Callable[[str], Anomalia | None] | None = None,
    ) -> None:
        self.regras = regras
        self.avaliar = avaliar
        self.publicar = publicar
        self.obter_contexto = obter_contexto
        self.registar_historico = registar_historico
        self.obter_anomalia = obter_anomalia  # o estado atual na base de dados; None: só a memória
        self.ocorrencias: dict[str, Ocorrencia] = {}

    def restaurar(self, ativas: Iterable[tuple[str, Anomalia]]) -> int:
        """No arranque: as anomalias ativas (us, anomalia), da mais recente para a mais antiga,
        voltam a ser ocorrências. Sem isto, as regras que guardam o estado em SQLite (porta, luz,
        temperatura) continuavam a ver o desvio e o ciclo criava outra anomalia, com outra SMS,
        deixando a antiga ativa para sempre. Devolve quantas reconstruiu."""
        for us, anomalia in ativas:
            if us in NAO_RECONSTRUIR or us in self.ocorrencias:
                continue  # das repetidas, fica a mais recente
            desvio = Desvio(us=us, classe=anomalia.classe, resumo="", habitual=None)
            self.ocorrencias[us] = Ocorrencia(desvio, "ativa", anomalia, reconstruida=True)
        return sum(o.reconstruida for o in self.ocorrencias.values())

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
            if ocorrencia is not None and _passou_a_seguranca(ocorrencia, desvio):
                ocorrencia = None  # calada como outra classe; como segurança é uma ocorrência nova
            if ocorrencia is None:
                self._nova_ocorrencia(desvio, contexto, agora)
            elif ocorrencia.estado == "ativa":
                self._continuar(ocorrencia, desvio)

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
        self.publicar(anomalia, imediato=desvio.imediato)

    def _atualizar(self, ocorrencia: Ocorrencia) -> bool:
        """Traz a anomalia da base de dados; False se o responsável já a resolveu."""
        if self.obter_anomalia is None or ocorrencia.anomalia is None:
            return True
        atual = self.obter_anomalia(ocorrencia.anomalia.id)
        if atual is None:
            return True
        ocorrencia.anomalia = atual
        if atual.estado == "resolvida":
            ocorrencia.estado = "respondida"
            return False
        return True

    def _continuar(self, ocorrencia: Ocorrencia, desvio: Desvio) -> None:
        anterior = ocorrencia.desvio
        ocorrencia.desvio = desvio
        if ocorrencia.reconstruida:
            # O resumo de antes do reinício perdeu-se: só a classe diz se a anomalia mudou.
            ocorrencia.reconstruida = False
            if desvio.classe == anterior.classe:
                return
        elif (desvio.classe, desvio.resumo) == (anterior.classe, anterior.resumo):
            return
        if not self._atualizar(ocorrencia):
            return
        assert ocorrencia.anomalia is not None
        ocorrencia.anomalia.classe = desvio.classe
        ocorrencia.anomalia.explicacao = explicacao_do_desvio(desvio)  # sem IA, mas com o habitual
        self.publicar(ocorrencia.anomalia)

    def _acabar_ocorrencias(
        self, desvios: dict[str, Desvio], resolucoes: dict[str, Resolucao], agora: datetime
    ) -> None:
        for us in [us for us in self.ocorrencias if us not in desvios]:
            resolucao = resolucoes.get(us)
            if self.ocorrencias[us].reconstruida and resolucao is None:
                # A regra ainda não a voltou a ver: fica, a não ser que o responsável a tenha
                # resolvido (senão o próximo desvio desta US passava por continuação dela).
                if not self._atualizar(self.ocorrencias[us]):
                    del self.ocorrencias[us]
                continue
            ocorrencia = self.ocorrencias.pop(us)
            if ocorrencia.estado != "ativa" or (resolucao is None and us in SO_COM_RESPOSTA):
                continue
            if not self._atualizar(ocorrencia):
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
    parar: threading.Event | None = None,
    dormir: Callable[[float], None] | None = None,
) -> None:
    """Um polling a cada intervalo segundos reais; o 'agora' é o do relógio (talvez acelerado).

    As regras usam o 'agora', não a hora das leituras, por isso a hora simulada chega a todas.
    Uma volta que falha (ex.: ErroDispositivos, o MCP não respondeu) fica no registo e
    salta-se; o ciclo não pára. passos limita o número de pollings (para os testes); parar
    acaba o ciclo entre duas voltas.
    """
    parar = parar or threading.Event()
    dormir = dormir or parar.wait
    n = 0
    while (passos is None or n < passos) and not parar.is_set():
        try:
            ciclo.passo(ler(), relogio.agora())
        except ErroDispositivos as e:  # o MCP falhou: esperado, uma linha chega
            registo.warning("Volta saltada, sem leitura da casa: %s", e)
        except Exception:
            registo.exception("A volta do ciclo falhou; segue-se a próxima.")
        n += 1
        if passos is None or n < passos:
            dormir(intervalo)


def real(relogio: Relogio) -> tuple[Ciclo, Callable[[], list[Leitura]]]:
    """O ciclo com as peças reais, e a leitura da casa pelo MCP, ambos com a hora do relógio."""
    from backend import anomalias, avisos, dispositivos, historico
    from backend.contexto.repositorio import carregar_contexto
    from backend.ia.avaliar import avaliar, us_da_anomalia

    ciclo = Ciclo(
        regras=carregar_regras(),
        avaliar=lambda desvio, contexto: avaliar(desvio, contexto, agora=relogio.agora()),
        publicar=avisos.publicar,
        obter_contexto=lambda: carregar_contexto(relogio.agora()),
        registar_historico=historico.registar_desvio,
        obter_anomalia=anomalias.obter,
    )
    ativas = ((us_da_anomalia(a.id), a) for a in anomalias.listar("ativa"))
    reconstruidas = ciclo.restaurar((us, a) for us, a in ativas if us is not None)
    if reconstruidas:
        registo.info("Reconstruídas %d ocorrência(s) a partir das anomalias ativas.", reconstruidas)
    return ciclo, lambda: dispositivos.ler(relogio.agora())


def arrancar() -> threading.Event:
    """Põe o ciclo real a correr numa thread da app; devolve o Event que o pára."""
    from backend import dispositivos

    relogio = partilhado()  # o mesmo que a API usa (dependencias.obter_agora)
    intervalo = dispositivos.intervalo_s()
    ciclo, ler = real(relogio)
    parar = threading.Event()
    threading.Thread(
        target=ao_vivo, args=(ciclo, ler, relogio, intervalo), kwargs={"parar": parar},
        name="ciclo", daemon=True,
    ).start()
    registo.info("Ciclo a correr: polling a cada %g s, a começar às %s.", intervalo, f"{relogio.agora():%Y-%m-%d %H:%M}")
    return parar


def main(argv: list[str]) -> None:
    import tempfile

    from backend import avisos, db, dispositivos, falsos

    # O estado das regras (porta, US11, US10) vai para um ficheiro temporário, não para o
    # homaly.db da app: correr um CSV não deixa rasto nas anomalias de desenvolvimento.
    db.usar(str(Path(tempfile.mkdtemp(prefix="homaly-ciclo-")) / "ciclo.db"))
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
