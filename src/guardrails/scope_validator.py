import re

# Simple placeholder implementation – real project will have extensive regexes
# and keyword blacklists.  For now we block obvious out‑of‑scope patterns.

FORBIDDEN_PATTERNS = [
    r"(?:\b(?:jailbreak|hack|bypass)\b)",
    r"(?:\b(?:lei|legal|jurídico|financeiro)\b)",
    r"(?:\b(?:instalação|eletricidade|risco)\b)",
]

def is_allowed(user_input: str) -> bool:
    """Return ``True`` if the input is within the allowed GoodWe scope.

    The function currently checks a small set of disallowed keywords.  It can be
    expanded with more sophisticated language‑model‑driven checks later.
    """
    lowered = user_input.lower()
    for pat in FORBIDDEN_PATTERNS:
        if re.search(pat, lowered):
            return False
    return True
