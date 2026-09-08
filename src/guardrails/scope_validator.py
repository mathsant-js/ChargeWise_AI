import re

# Simple placeholder implementation – real project will have extensive regexes
import re

# Expanded blacklist covering jailbreak, injection, illegal requests and domain‑specific risks.
FORBIDDEN_PATTERNS = [
    r"(?:\\b(?:jailbreak|hack|bypass|prompt\\s*injection)\\b)",
    r"(?:\\b(?:lei|legal|jur\u00eddico|financeiro|fraud|dangerous)\\b)",
    r"(?:\\b(?:instala\u00e7\u00e3o|eletricidade|risco|system\\s*prompt|reveal\\s*system\\s*prompt)\\b)",
]

def validate_scope(user_input: str) -> bool:
    """Return ``True`` if the input is within the allowed GoodWe scope.

    Checks the expanded ``FORBIDDEN_PATTERNS`` list.  Future versions may use
    LLM‑driven classification, but for now a simple regex match suffices.
    """
    lowered = user_input.lower()
    for pat in FORBIDDEN_PATTERNS:
        if re.search(pat, lowered):
            return False
    return True
