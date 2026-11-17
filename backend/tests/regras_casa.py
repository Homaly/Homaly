"""Corre um ficheiro de dados/ pelo Ciclo real, com as regras reais e peças que registam."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from backend import falsos
from backend.ciclo import Ciclo, correr
from backend.contrato import Anomalia
from backend.formatos import Contexto, Desvio

DADOS = Path(__file__).resolve().parents[1] / "dados"


class Registo:
    def __init__(self, regra, contexto: Contexto):
        regra.reiniciar()
        self.avaliados: list[tuple[datetime, Desvio]] = []
        self.publicadas: list[tuple[datetime, str, str]] = []  # (quando, estado, classe)
        self.resolucoes: list[str] = []  # o texto da resolução de cada anomalia resolvida
        self._agora: datetime | None = None
        self.ciclo = Ciclo(
            regras=[regra.verificar],
            avaliar=self._avaliar,
            publicar=self._publicar,
            obter_contexto=lambda: contexto,
            registar_historico=lambda d, motivo, agora: None,
        )

    def _avaliar(self, desvio: Desvio, contexto: Contexto) -> Anomalia:
        self.avaliados.append((self._agora, desvio))
        return Anomalia(id=str(len(self.avaliados)), classe=desvio.classe, titulo="t",
                        explicacao=desvio.resumo, detetada_em=self._agora)

    def _publicar(self, anomalia: Anomalia, imediato: bool = False) -> None:
        self.publicadas.append((self._agora, anomalia.estado, anomalia.classe))
        if anomalia.resolucao is not None:
            self.resolucoes.append(anomalia.resolucao.texto)

    def correr(self, ficheiro: str) -> "Registo":
        def lotes():
            for agora, leituras in falsos.ler_csv(str(DADOS / ficheiro)):
                self._agora = agora
                yield agora, leituras
        correr(self.ciclo, lotes())
        return self
