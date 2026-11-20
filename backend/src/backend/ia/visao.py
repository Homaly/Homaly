"""O modelo de visão olha para uma imagem da câmara da entrada de veículos (US13).

Uma chamada por imagem: o modelo diz se há um veículo, como é (tipo, cor, marca, matrícula se se
ler) e, com a lista dos veículos que a casa conhece, se é um deles. A matrícula manda sempre:
igual à de um conhecido, é esse; diferente, não é nenhum, diga o modelo o que disser. Sem matrícula,
fica a palavra do modelo pelo aspeto.

Testado a 2026-11-19 com o Haiku 5.5: três fotografias do mesmo carro (de frente, de trás, com
espuma no vidro) deram a mesma matrícula, o tipo, a cor e a marca certos.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from backend.contrato import Veiculo
from backend.ia.modelo import Modelo

SISTEMA = """És a câmara da entrada de veículos de uma casa. Olha para a imagem e responde só em JSON:
{"veiculo": true|false, "tipo": "carro|carrinha|mota|camião|outro" ou null, "cor": texto ou null,
 "marca": "marca e modelo, se os reconheceres" ou null,
 "matricula": "exatamente como se lê" ou null se não se ler,
 "descricao": "frase curta em português de Portugal sobre o que está na entrada",
 "conhecido_id": "o id do veículo conhecido que é este" ou null}
"veiculo" só é true se houver um veículo na imagem (uma fotografia de um veículo também conta).
Só dês um "conhecido_id" se tiveres a certeza de que é esse veículo; na dúvida, null."""


@dataclass(frozen=True)
class Observacao:
    veiculo: bool
    descricao: str
    tipo: str | None = None
    cor: str | None = None
    marca: str | None = None
    matricula: str | None = None
    conhecido_id: str | None = None  # o id do Veiculo conhecido que é este, se for

    def como_veiculo(self) -> Veiculo:
        """Para guardar como conhecido (US13: "Guardar este carro como conhecido?")."""
        nome = " ".join(p for p in (self.marca or self.tipo, self.cor) if p) or self.descricao
        return Veiculo(descricao=nome, tipo=self.tipo, cor=self.cor, marca=self.marca,
                       matricula=self.matricula)


def normalizar(matricula: str | None) -> str:
    """Só letras e algarismos, em maiúsculas: "35-19-ta" e "35 19 TA" são a mesma."""
    return re.sub(r"[^0-9A-Z]", "", (matricula or "").upper())


def observar(jpeg: bytes, conhecidos: list[Veiculo], modelo: Modelo) -> Observacao | None:
    """O que está na imagem, comparado com os conhecidos; None se o modelo falhou."""
    lista = [{"id": v.id, "descricao": v.descricao, "matricula": v.matricula} for v in conhecidos]
    mensagem = "Veículos que a casa conhece: " + json.dumps(lista, ensure_ascii=False)
    obs = _ler(modelo.completar_json_com_imagem(SISTEMA, mensagem, jpeg))
    if obs is None or not obs.veiculo:
        return obs
    return Observacao(**{**obs.__dict__, "conhecido_id": _conhecido(obs, conhecidos)})


def descrever(jpeg: bytes, modelo: Modelo) -> Veiculo | None:
    """O veículo de uma fotografia, para o registar como conhecido; None se não há veículo."""
    obs = _ler(modelo.completar_json_com_imagem(SISTEMA, "Veículos que a casa conhece: []", jpeg))
    return obs.como_veiculo() if obs is not None and obs.veiculo else None


def _conhecido(obs: Observacao, conhecidos: list[Veiculo]) -> str | None:
    lida = normalizar(obs.matricula)
    if lida:
        com_matricula = [v for v in conhecidos if normalizar(v.matricula)]
        igual = next((v.id for v in com_matricula if normalizar(v.matricula) == lida), None)
        if igual is not None:
            return igual
        # Leu-se uma matrícula que não é de nenhum conhecido: só o aspeto de um conhecido sem
        # matrícula registada ainda pode valer.
        sem_matricula = {v.id for v in conhecidos if not normalizar(v.matricula)}
        return obs.conhecido_id if obs.conhecido_id in sem_matricula else None
    return obs.conhecido_id if obs.conhecido_id in {v.id for v in conhecidos} else None


def _texto(valor) -> str | None:
    return valor.strip() if isinstance(valor, str) and valor.strip() else None


def _ler(dados: dict | None) -> Observacao | None:
    if not isinstance(dados, dict) or not isinstance(dados.get("veiculo"), bool):
        return None
    descricao = _texto(dados.get("descricao"))
    if descricao is None:
        return None
    return Observacao(
        veiculo=dados["veiculo"],
        descricao=descricao,
        tipo=_texto(dados.get("tipo")),
        cor=_texto(dados.get("cor")),
        marca=_texto(dados.get("marca")),
        matricula=_texto(dados.get("matricula")),
        conhecido_id=_texto(dados.get("conhecido_id")),
    )
