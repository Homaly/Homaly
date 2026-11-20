"""US13: um veículo que a casa não conhece está na entrada há mais de dois minutos (Segurança).

Dois gatilhos levam ao mesmo caminho:

- o `motionDetected` de uma câmara exterior (papel `exterior` no inventário: a da entrada de
  veículos) muda no MCP (qualquer mudança; a primeira leitura é só ponto de partida). A
  2026-11-19 vinha sempre "", por isso hoje não dispara; as câmaras de dentro não contam;
- o detetor de movimento no vídeo (backend.camara) conta mais um movimento. É o gatilho real.

Depois: uma imagem da câmara vai ao modelo de visão (backend.ia.visao), que diz se há um veículo
e se é um dos conhecidos. Desconhecido: espera VEICULO_MINUTOS (2, para não avisar por quem só faz
inversão de marcha) e olha outra vez. Se ainda lá estiver um veículo desconhecido, o desvio leva a
imagem; a anomalia só se resolve com a resposta do responsável (SO_COM_RESPOSTA, no ciclo), que
pode guardar o carro como conhecido. Depois de um aviso, VEICULO_PAUSA_MINUTOS (30) sem olhar,
para não avisar outra vez pelo mesmo carro.

A captura e o modelo demoram segundos: correm noutra thread (`submeter`), e cada volta só vê se
já acabaram. O tempo conta pelo `agora` do ciclo (acelera na demo), nunca pela hora real.
Sem modelo de visão (IA_FORNECEDOR=falso) não se tira nenhuma imagem.
"""

from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from backend import camara, inventario, veiculos
from backend.dependencias import obter_modelo_dep
from backend.formatos import Contexto, Desvio, Leitura
from backend.ia import visao
from backend.ia.modelo import ModeloFalso
from backend.regras import casa_vazia

from ._comum import hora, numero

registo = logging.getLogger(__name__)


@dataclass(frozen=True)
class Visto:
    imagem: str  # a imagemUrl guardada; "" quando não se guardou (nada a avisar)
    obs: visao.Observacao

    @property
    def desconhecido(self) -> bool:
        return self.obs.veiculo and self.obs.conhecido_id is None


def _observar() -> Visto | None:
    """Tira uma imagem e pergunta ao modelo de visão; só guarda a imagem se o veículo é desconhecido."""
    modelo = obter_modelo_dep()
    if isinstance(modelo, ModeloFalso):
        return None
    jpeg = camara.capturar()
    if jpeg is None:
        return None
    obs = visao.observar(jpeg, veiculos.listar(), modelo)
    if obs is None:
        return None
    visto = Visto("", obs)
    if visto.desconhecido:
        visto = Visto(camara.guardar(jpeg), obs)
        veiculos.registar_visto(visto.imagem, obs)
    return visto


_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="us13")

# Trocáveis nos testes.
observar = _observar
submeter = _executor.submit
contar_movimentos = camara.movimentos

Fase = Literal["livre", "a_ver", "a_esperar", "a_confirmar"]

_fase: Fase = "livre"
_tarefa: Future | None = None
_pedido_em: datetime | None = None  # quando se pediu a primeira observação
_visto_em: datetime | None = None  # desde quando está lá o veículo desconhecido
_pausa_ate: datetime | None = None
_movimento_anterior: object = None  # o último motionDetected visto
_contador_anterior: int | None = None


def reiniciar() -> None:
    global _fase, _tarefa, _pedido_em, _visto_em, _pausa_ate, _movimento_anterior, _contador_anterior
    _fase, _tarefa, _pedido_em, _visto_em, _pausa_ate = "livre", None, None, None, None
    _movimento_anterior, _contador_anterior = None, None


def verificar(leituras: list[Leitura], contexto: Contexto, agora: datetime) -> list[Desvio]:
    global _fase, _tarefa, _pedido_em, _visto_em, _pausa_ate
    houve_movimento = _houve_movimento(leituras)
    desvios: list[Desvio] = []

    if _tarefa is not None and _tarefa.done():
        visto = _resultado(_tarefa)
        _tarefa = None
        if _fase == "a_ver":
            _fase = "a_esperar" if visto is not None and visto.desconhecido else "livre"
            _visto_em = _pedido_em
        elif _fase == "a_confirmar":
            _fase = "livre"
            if visto is not None and visto.desconhecido:
                desvios.append(_desvio(visto, contexto, agora))
                _pausa_ate = agora + timedelta(minutes=numero("VEICULO_PAUSA_MINUTOS", 30))

    if _fase == "a_esperar" and agora - _visto_em >= timedelta(minutes=numero("VEICULO_MINUTOS", 2)):
        _tarefa, _fase = submeter(observar), "a_confirmar"
    elif _fase == "livre" and houve_movimento and (_pausa_ate is None or agora >= _pausa_ate):
        _tarefa, _fase, _pedido_em = submeter(observar), "a_ver", agora
    return desvios


def _houve_movimento(leituras: list[Leitura]) -> bool:
    global _movimento_anterior, _contador_anterior
    houve = False
    exteriores = inventario.com_papel(leituras, "camara", "motionDetected", "exterior")
    valor = exteriores[-1].valor if exteriores else None
    if valor is not None:
        houve = _movimento_anterior is not None and valor != _movimento_anterior
        _movimento_anterior = valor
    contador = contar_movimentos()
    if _contador_anterior is not None and contador > _contador_anterior:
        houve = True
    _contador_anterior = contador
    return houve


def _resultado(tarefa: Future) -> Visto | None:
    try:
        return tarefa.result()
    except Exception:
        registo.warning("A observação da câmara falhou", exc_info=True)
        return None


def _desvio(visto: Visto, contexto: Contexto, agora: datetime) -> Desvio:
    obs = visto.obs
    como = " ".join(p for p in (obs.tipo, obs.cor) if p) or "veículo"
    if obs.marca:
        como += f" ({obs.marca})"
    if obs.matricula:
        como += f", matrícula {obs.matricula}"
    return Desvio(
        us="US13",
        classe="seguranca",
        resumo=f"Veículo desconhecido na entrada desde as {hora(_visto_em or agora)}: {como}.",
        habitual="Nenhum dos veículos que a casa conhece.",
        imediato=casa_vazia(contexto, agora),
        imagem=visto.imagem,
    )
