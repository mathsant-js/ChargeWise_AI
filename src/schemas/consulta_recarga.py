import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


EstadoCarregador = Literal[
    "online",
    "offline",
    "carregando",
    "disponivel",
    "disponível",
    "indisponivel",
    "indisponível",
    "erro",
    "manutencao",
    "manutenção",
]


class ConsultaRecarga(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intencao: Literal[
        "status_carregador",
        "potencia",
        "faturamento",
        "sustentabilidade",
        "fora_do_escopo",
    ] = Field(description="Intenção reconhecida da pergunta do usuário.")
    resposta: str = Field(min_length=1, description="Resposta em linguagem natural para o usuário.")
    estado_carregador: EstadoCarregador | None = Field(
        default=None,
        description="Estado conhecido do carregador, sem acentos e em minúsculas.",
    )
    potencia_kw: float | None = Field(default=None, ge=0, allow_inf_nan=False, strict=True)
    valor_estimado: float | None = Field(default=None, ge=0, allow_inf_nan=False, strict=True)
    requer_profissional: bool = False
    confianca: float = Field(ge=0, le=1, allow_inf_nan=False, strict=True)

    @field_validator("resposta")
    @classmethod
    def validar_resposta(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A resposta não pode ser vazia.")
        return value

    @field_validator("potencia_kw", "valor_estimado", "confianca")
    @classmethod
    def validar_numero_finito(cls, value: float | None) -> float | None:
        if value is not None and (isinstance(value, bool) or not math.isfinite(value)):
            raise ValueError("O valor deve ser um número finito.")
        return value

    @model_validator(mode="after")
    def validar_coerencia(self) -> "ConsultaRecarga":
        if self.estado_carregador is not None and self.intencao != "status_carregador":
            raise ValueError("estado_carregador exige intenção status_carregador.")
        if self.valor_estimado is not None and self.intencao != "faturamento":
            raise ValueError("valor_estimado exige intenção faturamento.")
        if self.intencao == "fora_do_escopo" and any(
            value is not None
            for value in (self.estado_carregador, self.potencia_kw, self.valor_estimado)
        ):
            raise ValueError("Uma recusa não pode conter dados operacionais.")
        return self
