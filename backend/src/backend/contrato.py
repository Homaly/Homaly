"""O contrato com a PWA, em Python.

Espelha `frontend/src/types/contract.ts` (fonte: `docs/frontend-design.md`). Mudar um obriga a
mudar o outro, avisando a equipa.

Em Python os campos usam snake_case (`detetada_em`); no JSON saem em camelCase (`detetadaEm`),
como no contract.ts. Os campos opcionais que ficam a `None` não saem no JSON.
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import AfterValidator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


def _com_fuso(d: datetime) -> datetime:
    # Uma hora sem fuso (ex.: datetime.now()) é tomada como hora local.
    return d if d.tzinfo else d.astimezone()


Instante = Annotated[datetime, AfterValidator(_com_fuso)]
"""Uma data e hora, sempre com fuso. No JSON sai em ISO 8601."""


def agora() -> datetime:
    return datetime.now().astimezone()


def novo_id() -> str:
    return uuid4().hex


class Modelo(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    def para_json(self) -> dict:
        """O dicionário que vai para a PWA: camelCase, sem os campos a None."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


Classe = Literal["seguranca", "bem_estar", "saude_conforto", "eficiencia"]


class AcaoProposta(Modelo):
    descricao: str


class TextoEm(Modelo):
    texto: str
    em: Instante = Field(default_factory=agora)


class PropostaSilencio(Modelo):
    """US02: a casa propõe deixar de avisar até uma hora; só se aplica depois de aceite."""

    texto: str
    ate: Instante
    estado: Literal["pendente", "aceite", "recusada"] = "pendente"


class Anomalia(Modelo):
    id: str = Field(default_factory=novo_id)
    classe: Classe
    titulo: str
    explicacao: str
    """Texto da IA: o que aconteceu e o que é habitual."""
    detetada_em: Instante = Field(default_factory=agora)
    estado: Literal["ativa", "resolvida"] = "ativa"
    acao_proposta: AcaoProposta | None = None
    imagem_url: str | None = None
    resposta: TextoEm | None = None
    proposta_silencio: PropostaSilencio | None = None
    resolucao: TextoEm | None = None
    """Como se resolveu (ex.: "a porta fechou às 14:12"); só com estado 'resolvida'."""


class Evento(Modelo):
    id: str = Field(default_factory=novo_id)
    em: Instante = Field(default_factory=agora)
    dispositivo: str
    descricao: str
    anomalia_id: str | None = None


class MensagemConversa(Modelo):
    id: str = Field(default_factory=novo_id)
    autor: Literal["pessoa", "casa"]
    texto: str
    em: Instante = Field(default_factory=agora)


class Contacto(Modelo):
    nome: str
    telemovel: str


class Definicoes(Modelo):
    contacto: Contacto | None
    espera_minutos: int
