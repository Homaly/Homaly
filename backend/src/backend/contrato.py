"""O contrato com a PWA, em Python.

Espelha `frontend/src/types/contract.ts` (fonte: `docs/frontend-design.md`). Mudar um obriga a
mudar o outro, avisando a equipa.

Em Python os campos usam snake_case (`detetada_em`); no JSON saem em camelCase (`detetadaEm`),
como no contract.ts. Os campos opcionais que ficam a `None` não saem no JSON.
"""

import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)
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


def _telemovel(texto: str) -> str:
    """Um telemóvel no formato internacional (+351912345678), que é o que o textbee recebe.

    Aceita 912 345 678, +351 912 345 678 ou 00351912345678; um número estrangeiro tem de trazer o
    indicativo. Um número fixo português não recebe SMS e é recusado.
    """
    numero = re.sub(r"[\s\-.()]", "", texto)
    if numero.startswith("00"):
        numero = "+" + numero[2:]
    if re.fullmatch(r"\d{9}", numero):
        numero = "+351" + numero
    if numero.startswith("+351"):
        if not re.fullmatch(r"\+3519[1236]\d{7}", numero):
            raise ValueError(
                "um telemóvel português tem 9 algarismos e começa por 91, 92, 93 ou 96 (os fixos não recebem SMS)"
            )
        return numero
    if not re.fullmatch(r"\+[1-9]\d{7,14}", numero):
        raise ValueError("número de telemóvel inválido; um número estrangeiro começa por + e o indicativo")
    return numero


Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]


class Contacto(Modelo):
    nome: Nome
    telemovel: Annotated[str, AfterValidator(_telemovel)]


class Definicoes(Modelo):
    """US04. Sem `nome_casa`, a SMS ao contacto externo diz só "Homaly"."""

    contacto: Contacto | None
    # Em minutos, até um dia; aceita frações: 0.5 são os 30 segundos das Definições.
    espera_minutos: Annotated[float, Field(ge=0, le=1440)]
    nome_casa: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] | None = None

    @field_validator("nome_casa")
    @classmethod
    def _sem_nome_vazio(cls, nome: str | None) -> str | None:
        return nome or None

    def para_json(self) -> dict:
        """Como as outras, sem os campos a None, exceto `contacto`, que vai a null sem contacto."""
        return {**super().para_json(), "contacto": self.contacto.para_json() if self.contacto else None}
