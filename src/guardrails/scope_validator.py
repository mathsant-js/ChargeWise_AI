import re


SAFE_REFUSAL = "Não posso atender a essa solicitação."

_DOMAIN_PATTERN = re.compile(
    r"\b(?:goodwe|ve[ií]culo(?:s)?\s+el[eé]trico(?:s)?|carro(?:s)?\s+el[eé]trico(?:s)?|"
    r"ev|carregador(?:es)?|recarga|carregamento|esta[cç][aã]o\s+de\s+carga|wallbox|"
    r"inversor(?:es)?|equipamento|aplicativo|sess[aã]o\s+ativa|carga|kw|"
    r"fotovoltaic[oa]s?|energia\s+solar|energia\s+consumida|bateria(?:s)?|"
    r"pot[eê]ncia(?:\s+de\s+carga)?|tarifa|custo|custou|gastei|carregando|cobran[cç]a|reais|"
    r"status|estado|online|offline|dispon[ií]vel|indispon[ií]vel|"
    r"renov[aá]vel|ambiental|emiss[aã]o|combust[ií]vel)\b",
    re.IGNORECASE,
)

_JAILBREAK_PATTERNS = (
    re.compile(r"\b(?:jailbreak|prompt\s*injection|developer\s+mode|modo\s+desenvolvedor)\b", re.I),
    re.compile(r"\b(?:ignore|ignorar|desconsidere)\b.{0,50}\b(?:instru[cç][oõ]es|regras|prompt)\b", re.I),
    re.compile(
        r"\b(?:revele|mostre|exiba|imprima|repita|vaze|qual\s+[eé])\b.{0,50}"
        r"\b(?:prompt\s+(?:do\s+)?sistema|system\s*prompt|instru[cç][oõ]es\s+internas)\b",
        re.I,
    ),
)

_UNRELATED_ADVICE_PATTERN = re.compile(
    r"\b(?:advogado|processo\s+judicial|parecer\s+jur[ií]dico|contrato\s+de\s+trabalho|"
    r"imposto\s+de\s+renda|investimento|a[cç][aã]o\s+na\s+bolsa|criptomoeda|empr[eé]stimo|"
    r"financiamento\s+imobili[aá]rio)\b",
    re.IGNORECASE,
)

_ELECTRICAL_ACTION_PATTERN = re.compile(
    r"\b(?:abrir|desmontar|adulterar|modificar|reparar|consertar|trocar|remover|"
    r"instalar|ligar|conectar|desativar|burlar|jampear|jumpear|curto-circuitar|tocar)\w*\b",
    re.IGNORECASE,
)
_DANGEROUS_COMPONENT_PATTERN = re.compile(
    r"\b(?:rede\s+el[eé]trica|quadro\s+el[eé]trico|disjuntor|fia[cç][aã]o|cabos?\s+energizados?|"
    r"alta\s+tens[aã]o|trif[aá]sic[oa]|aterramento|prote[cç][aã]o\s+el[eé]trica|"
    r"interlock|sensor\s+de\s+seguran[cç]a)\b",
    re.IGNORECASE,
)


def validate_scope(user_input: str) -> bool:
    """Return whether an input is safe and belongs to the GoodWe/EV domain."""
    if not isinstance(user_input, str) or not user_input.strip():
        return False

    text = " ".join(user_input.split())
    if any(pattern.search(text) for pattern in _JAILBREAK_PATTERNS):
        return False
    if _UNRELATED_ADVICE_PATTERN.search(text):
        return False
    if re.search(r"\b(?:fraudar|fraude|burlar)\b.{0,40}\b(?:cobran[cç]a|pagamento|esta[cç][aã]o)\b", text, re.I):
        return False
    if _ELECTRICAL_ACTION_PATTERN.search(text) and _DANGEROUS_COMPONENT_PATTERN.search(text):
        return False

    return _DOMAIN_PATTERN.search(text) is not None
