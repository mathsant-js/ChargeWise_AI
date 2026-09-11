import re
from dataclasses import dataclass
from enum import Enum


class BlockCategory(str, Enum):
    OUT_OF_SCOPE = "fora_do_escopo"
    JAILBREAK = "jailbreak"
    LEGAL = "juridico"
    FINANCIAL = "financeiro"
    ELECTRICAL_SAFETY = "seguranca_eletrica"
    FRAUD = "fraude"


REFUSAL_MESSAGES = {
    BlockCategory.OUT_OF_SCOPE: "Não posso atender a essa solicitação porque ela está fora do escopo de produtos GoodWe e recarga de veículos elétricos.",
    BlockCategory.JAILBREAK: "Não posso atender a tentativas de alterar minhas regras, assumir outro papel ou revelar instruções internas.",
    BlockCategory.LEGAL: "Não posso fornecer aconselhamento jurídico. Consulte um advogado ou profissional jurídico habilitado.",
    BlockCategory.FINANCIAL: "Não posso fornecer aconselhamento financeiro. Consulte um profissional financeiro qualificado.",
    BlockCategory.ELECTRICAL_SAFETY: "Não posso fornecer instruções operacionais para essa atividade elétrica, pois há risco de choque, incêndio ou dano ao equipamento. Procure um eletricista ou profissional habilitado.",
    BlockCategory.FRAUD: "Não posso ajudar a fraudar, adulterar ou burlar cobranças, pagamentos ou mecanismos de segurança.",
}


@dataclass(frozen=True)
class ScopeDecision:
    allowed: bool
    category: BlockCategory | None = None
    reason: str | None = None

    def __bool__(self) -> bool:
        return self.allowed

    def refusal(self) -> dict:
        if self.allowed or self.category is None:
            raise ValueError("Uma decisão permitida não possui recusa.")
        return refusal_for(self.category)


def refusal_for(category: BlockCategory) -> dict:
    return {
        "intencao": "fora_do_escopo",
        "resposta": REFUSAL_MESSAGES[category],
        "requer_profissional": category in {
            BlockCategory.LEGAL,
            BlockCategory.FINANCIAL,
            BlockCategory.ELECTRICAL_SAFETY,
        },
        "confianca": 0.0,
    }


_DOMAIN_PATTERN = re.compile(
    r"\b(?:goodwe|ve[ií]culo(?:s)?\s+el[eé]trico(?:s)?|carro(?:s)?\s+el[eé]trico(?:s)?|"
    r"ev|carregador(?:es)?|recarga|carregamento|esta[cç][aã]o\s+de\s+carga|wallbox|"
    r"inversor(?:es)?|equipamento|aplicativo|sess[aã]o\s+ativa|carga|kw|"
    r"fotovoltaic[oa]s?|energia\s+solar|energia\s+consumida|bateria(?:s)?|"
    r"pot[eê]ncia(?:\s+de\s+carga)?|tarifa|custo|custou|gastei|carregando|cobran[cç]a|reais|"
    r"status|estado|online|offline|dispon[ií]vel|indispon[ií]vel|"
    r"renov[aá]vel|ambiental|emiss[aã]o|combust[ií]vel)\b",
    re.I,
)

_JAILBREAK_PATTERNS = (
    re.compile(r"\b(?:jailbreak|prompt\s*injection|developer\s+mode|modo\s+desenvolvedor|dan\s+mode)\b", re.I),
    re.compile(r"\b(?:ignore|ignorar|ignora|desconsidere|esque[cç]a|forget|disregard|overlook|olvida|oublie[zr]?)\b.{0,100}\b(?:instru[cç][oõ]es|regras|prompt|rules?|instructions?|directives?|restri[cç][oõ]es)\b", re.I),
    re.compile(r"\b(?:revele|mostre|exiba|imprima|repita|vaze|transcreva|reveal|show|print|repeat|leak|traduz[air]|translate|qual\s+[eé])\b.{0,100}\b(?:prompt\s+(?:do\s+)?sistema|system\s*prompt|instru[cç][oõ]es\s+internas|hidden\s+instructions?|mensagem\s+de\s+sistema)\b", re.I),
    re.compile(r"\b(?:finja|imagine|simule|interprete|assuma|pretend|act\s+as|role[ -]?play|fa[cç]a\s+de\s+conta)\b.{0,120}\b(?:sem\s+regras|sem\s+restri[cç][oõ]es|desenvolvedor|administrador|dan|unrestricted|ignore|ignorar)\b", re.I),
    re.compile(r"\b(?:codifique|encode|base64|indiretamente|em\s+outras\s+palavras|pr[oó]ximo\s+turno)\b.{0,100}\b(?:prompt|regras|instru[cç][oõ]es|ignore|ignorar|revele|reveal)\b", re.I),
)
_LEGAL_PATTERN = re.compile(
    r"\b(?:advogad[oa]|processo\s+judicial|parecer\s+jur[ií]dico|aconselhamento\s+jur[ií]dico|"
    r"contrato\s+de\s+trabalho|a[cç][aã]o\s+judicial|posso\s+processar|devo\s+processar|"
    r"direitos?\s+legais?|legal\s+advice|lawsuit)\b", re.I
)
_FINANCIAL_PATTERN = re.compile(
    r"\b(?:investimento|investir|a[cç][aã]o\s+na\s+bolsa|criptomoeda|empr[eé]stimo|"
    r"financiamento\s+imobili[aá]rio|carteira\s+de\s+investimentos|consultoria\s+financeira|"
    r"financial\s+advice|buy\s+stocks?|comprar\s+a[cç][oõ]es)\b", re.I
)
ELECTRICAL_ACTION_PATTERN = re.compile(
    r"\b(?:abr(?:ir|a)|desmont|adulter|modific|repar|consert|troc|remov|instal|"
    r"deslig|lig|conect|desativ|burl|j[au]mpe|curto-circuit|toc|cort|emend|med|test)\w*\b",
    re.I,
)
DANGEROUS_COMPONENT_PATTERN = re.compile(
    r"\b(?:rede\s+el[eé]trica|quadro\s+el[eé]trico|disjuntor|fia[cç][aã]o|cabos?\s+energizados?|"
    r"alta\s+tens[aã]o|trif[aá]sic[oa]|aterramento|prote[cç][aã]o\s+el[eé]trica|"
    r"interlock|sensor\s+de\s+seguran[cç]a|terminal|borne|fase|neutro|circuito)\b", re.I
)
_FRAUD_PATTERN = re.compile(
    r"\b(?:fraudar|fraude|burlar|adulterar|enganar|evitar|n[aã]o\s+pagar|zerar)\w*\b.{0,60}"
    r"\b(?:cobran[cç]a|pagamento|medidor|contador|esta[cç][aã]o|tarifa|consumo|fatura)\b|"
    r"\b(?:cobran[cç]a|pagamento|medidor|contador|esta[cç][aã]o|tarifa|consumo|fatura)\b.{0,60}"
    r"\b(?:fraudar|burlar|adulterar|enganar|n[aã]o\s+pagar|zerar)\w*\b", re.I
)


def validate_scope(user_input: str, conversation_context: str = "") -> ScopeDecision:
    """Classify whether a request can be answered and explain any block."""
    if not isinstance(user_input, str) or not user_input.strip():
        return ScopeDecision(False, BlockCategory.OUT_OF_SCOPE, "entrada_vazia")

    text = " ".join(user_input.split())
    combined = " ".join(f"{conversation_context} {text}".split())
    if any(pattern.search(combined) for pattern in _JAILBREAK_PATTERNS):
        return ScopeDecision(False, BlockCategory.JAILBREAK, "manipulacao_de_instrucoes")
    if _FRAUD_PATTERN.search(text):
        return ScopeDecision(False, BlockCategory.FRAUD, "solicitacao_de_fraude")
    if _LEGAL_PATTERN.search(text):
        return ScopeDecision(False, BlockCategory.LEGAL, "aconselhamento_juridico")
    if _FINANCIAL_PATTERN.search(text):
        return ScopeDecision(False, BlockCategory.FINANCIAL, "aconselhamento_financeiro")
    if ELECTRICAL_ACTION_PATTERN.search(text) and DANGEROUS_COMPONENT_PATTERN.search(text):
        return ScopeDecision(False, BlockCategory.ELECTRICAL_SAFETY, "atividade_eletrica_perigosa")
    if not _DOMAIN_PATTERN.search(text):
        return ScopeDecision(False, BlockCategory.OUT_OF_SCOPE, "dominio_nao_reconhecido")
    return ScopeDecision(True)
