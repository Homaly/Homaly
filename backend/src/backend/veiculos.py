"""US13: os veículos que a casa conhece, e o que o modelo de visão viu em cada imagem.

- `veiculos_conhecidos`: os que não dão aviso. Entram por fotografia (`POST /veiculos`, o modelo de
  visão descreve-a) ou pela resposta a um aviso ("Guardar este carro como conhecido?", em
  backend.resposta). `GET /veiculos` lista-os, `DELETE /veiculos/{id}` esquece um.
- `veiculos_vistos`: o que o modelo viu em cada imagem guardada, pela `imagemUrl`. É daqui que a
  resposta ao aviso tira o carro a guardar.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import Field

from . import camara, db
from .contrato import Modelo as ModeloContrato
from .contrato import Veiculo
from .dependencias import obter_modelo_dep
from .ia import visao
from .ia.modelo import Modelo

db.esquema(
    """
    CREATE TABLE IF NOT EXISTS veiculos_conhecidos (
        id    TEXT PRIMARY KEY,
        dados TEXT NOT NULL  -- o Veiculo em JSON
    );
    CREATE TABLE IF NOT EXISTS veiculos_vistos (
        imagem TEXT PRIMARY KEY,  -- a imagemUrl, ex.: /imagens/<id>.jpg
        dados  TEXT NOT NULL      -- a visao.Observacao em JSON
    );
    """
)


def listar() -> list[Veiculo]:
    with db.ligar() as con:
        linhas = con.execute("SELECT dados FROM veiculos_conhecidos ORDER BY rowid").fetchall()
    return [Veiculo.model_validate_json(l["dados"]) for l in linhas]


def guardar(veiculo: Veiculo) -> Veiculo:
    with db.ligar() as con:
        con.execute(
            "INSERT OR REPLACE INTO veiculos_conhecidos (id, dados) VALUES (?, ?)",
            (veiculo.id, veiculo.model_dump_json()),
        )
    return veiculo


def apagar(id: str) -> bool:
    with db.ligar() as con:
        return con.execute("DELETE FROM veiculos_conhecidos WHERE id = ?", (id,)).rowcount > 0


def registar_visto(imagem: str, obs: visao.Observacao) -> None:
    with db.ligar() as con:
        con.execute(
            "INSERT OR REPLACE INTO veiculos_vistos (imagem, dados) VALUES (?, ?)",
            (imagem, json.dumps(obs.__dict__, ensure_ascii=False)),
        )


def visto(imagem: str | None) -> visao.Observacao | None:
    """O que o modelo viu na imagem com esta `imagemUrl`, se foi uma da US13."""
    if not imagem:
        return None
    with db.ligar() as con:
        linha = con.execute("SELECT dados FROM veiculos_vistos WHERE imagem = ?", (imagem,)).fetchone()
    return visao.Observacao(**json.loads(linha["dados"])) if linha else None


class PedidoRegisto(ModeloContrato):
    imagem: Annotated[str, Field(min_length=1, max_length=15_000_000)]  # JPEG em base64 (ou data:)
    nome: Annotated[str, Field(max_length=60)] | None = None  # ex.: "o carro do meu irmão"


router = APIRouter(prefix="/veiculos", tags=["veículos"])


@router.get("")
def pedir_lista() -> list[dict]:
    return [v.para_json() for v in listar()]


@router.post("", status_code=201)
def pedir_registo(pedido: PedidoRegisto, modelo: Modelo = Depends(obter_modelo_dep)) -> dict:
    texto = pedido.imagem.split(",", 1)[1] if pedido.imagem.startswith("data:") else pedido.imagem
    try:
        jpeg = base64.b64decode(texto, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=422, detail="A imagem tem de vir em base64") from None
    veiculo = visao.descrever(camara.reduzir(jpeg), modelo)
    if veiculo is None:
        raise HTTPException(status_code=422, detail="Não vi nenhum veículo na fotografia")
    if pedido.nome and pedido.nome.strip():
        veiculo = veiculo.model_copy(update={"descricao": pedido.nome.strip()})
    return guardar(veiculo).para_json()


@router.delete("/{id}", status_code=204)
def pedir_apagar(id: str) -> Response:
    if not apagar(id):
        raise HTTPException(status_code=404, detail="Veículo não encontrado")
    return Response(status_code=204)
