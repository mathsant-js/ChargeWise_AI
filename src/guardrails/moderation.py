import re
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from src.schemas.consulta_recarga import ConsultaRecarga
from src.guardrails.scope_validator import (
    BlockCategory,
    DANGEROUS_COMPONENT_PATTERN,
    ELECTRICAL_ACTION_PATTERN,
    refusal_for,
)


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
_INVENTED_SPEC = re.compile(
    r"\b(?:goodwe|modelo\s+[a-z0-9-]+)\b.{0,100}\b(?:possui|suporta|fornece|opera|pot[eê]ncia|"
    r"tens[aã]o|corrente|capacidade)\b|\b(?:possui|suporta|fornece|opera)\b.{0,100}\bgoodwe\b",
    re.I,
)
_PROMPT_LEAK = re.compile(
    r"(?:<identidade>|<escopo>|<seguranca>|<precisao>|<saida>|system\s*prompt|"
    r"instru[cç][oõ]es\s+(?:internas|do\s+sistema)|mensagem\s+de\s+sistema)", re.I
)
_IMPROPER_LEGAL = re.compile(
    r"\b(?:voc[eê]\s+deve|recomendo|a\s+melhor\s+estrat[eé]gia\s+[eé])\b.{0,80}"
    r"\b(?:processar|ajuizar|assinar|rescindir|advogado|tribunal|indeniza[cç][aã]o)\b", re.I
)
_IMPROPER_FINANCIAL = re.compile(
    r"\b(?:voc[eê]\s+deve|recomendo|compre|venda|invista|a\s+melhor\s+op[cç][aã]o\s+[eé])\b.{0,80}"
    r"\b(?:a[cç][oõ]es|criptomoeda|investimento|empr[eé]stimo|financiamento)\b", re.I
)


def _safe_refusal(category: BlockCategory = BlockCategory.OUT_OF_SCOPE) -> dict:
    return refusal_for(category)


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
    if isinstance(response, str):
        if _PROMPT_LEAK.search(response):
            return _safe_refusal(BlockCategory.JAILBREAK)
        if ELECTRICAL_ACTION_PATTERN.search(response) and DANGEROUS_COMPONENT_PATTERN.search(response):
            return _safe_refusal(BlockCategory.ELECTRICAL_SAFETY)
        if _IMPROPER_LEGAL.search(response):
            return _safe_refusal(BlockCategory.LEGAL)
        if _IMPROPER_FINANCIAL.search(response):
            return _safe_refusal(BlockCategory.FINANCIAL)
        invented_spec = _INVENTED_SPEC.search(response) and _CONCRETE_SPEC.search(response)
        if (invented_spec or _claims_unprovided_official_spec(response, moderation_context)) and not moderation_context.official_sources:
            return _safe_refusal()

    try:
        return ConsultaRecarga.model_validate(data).model_dump()
    except (ValidationError, TypeError, ValueError):
        return _safe_refusal()
