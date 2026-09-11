import re
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from src.schemas.consulta_recarga import ConsultaRecarga


SAFE_REFUSAL = {
    "intencao": "fora_do_escopo",
    "resposta": "Não posso atender a essa solicitação.",
    "confianca": 0.0,
}


@dataclass(frozen=True)
class ModerationContext:
    """Trusted metadata supplied by the application, never by the model."""

    official_sources: tuple[str, ...] = ()

_OFFICIAL_SPEC_CLAIM = re.compile(
    r"\b(?:segundo|conforme|de\s+acordo\s+com)\s+(?:o\s+|a\s+)?"
    r"(?:manual|datasheet|ficha\s+t[eé]cnica|documenta[cç][aã]o)\s+(?:oficial\s+)?(?:da\s+)?goodwe\b",
    re.IGNORECASE,
)
_CONCRETE_SPEC = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:kw|w|v|a|kwh|%|amp[eè]res?|volts?)\b",
    re.IGNORECASE,
)
_NON_ASSERTIVE_CONTEXT = re.compile(
    r"\b(?:consulte|verifique|confirme|não\s+(?:sei|tenho|foi\s+fornecid[oa])|sem\s+acesso)\b",
    re.IGNORECASE,
)


def _safe_refusal() -> dict:
    return SAFE_REFUSAL.copy()


def _claims_unprovided_official_spec(
    response: str, context: ModerationContext
) -> bool:
    claim = _OFFICIAL_SPEC_CLAIM.search(response)
    if not claim or not _CONCRETE_SPEC.search(response) or _NON_ASSERTIVE_CONTEXT.search(response):
        return False

    return not any(source.strip() for source in context.official_sources)


def moderate_output(
    data: dict, context: ModerationContext | None = None
) -> dict:
    """Return validated structured output, never untrusted raw model output."""
    if not isinstance(data, dict):
        return _safe_refusal()

    moderation_context = context or ModerationContext()
    response = data.get("resposta")
    if isinstance(response, str) and _claims_unprovided_official_spec(
        response, moderation_context
    ):
        return _safe_refusal()

    try:
        return ConsultaRecarga.model_validate(data).model_dump()
    except (ValidationError, TypeError, ValueError):
        return _safe_refusal()
