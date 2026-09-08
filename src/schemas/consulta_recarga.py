from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional

class ConsultaRecarga(BaseModel):
    intencao: Literal[
        "status_carregador",
        "potencia",
        "faturamento",
        "sustentabilidade",
        "fora_do_escopo",
    ] = Field(description="Intenção reconhecida da pergunta do usuário.")
    resposta: str = Field(description="Resposta em linguagem natural para o usuário.")
    estado_carregador: Optional[str] = Field(
        default=None,
        description="Estado atual do carregador (ex.: online, offline, manutenção).",
    )
    potencia_kw: Optional[float] = Field(
        default=None,
        description="Potência do carregador em kW, se relevante.",
        ge=0,
    )
    valor_estimado: Optional[float] = Field(
        default=None,
        description="Valor monetário estimado da recarga, se aplicável.",
        ge=0,
    )
    requer_profissional: bool = Field(
        default=False,
        description="Indica se a resposta requer avaliação de um profissional habilitado.",
    )
    confianca: float = Field(
        description="Nível de confiança da resposta (0‑1).",
        ge=0,
        le=1,
    )

    @field_validator("confianca")
    @classmethod
    def validar_confianca(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("A confiança deve estar entre 0 e 1.")
        return v
