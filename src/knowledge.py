from html import escape
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONDOMINIUM_KNOWLEDGE_PATH = (
    PROJECT_ROOT / "data" / "conhecimento_condominio_v2.md"
)
MAX_KNOWLEDGE_BYTES = 64 * 1024


def load_condominium_knowledge(path: str | Path | None = None) -> str:
    """Load the reviewed condominium context with explicit size validation."""
    knowledge_path = Path(path) if path is not None else DEFAULT_CONDOMINIUM_KNOWLEDGE_PATH
    try:
        size = knowledge_path.stat().st_size
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Base de conhecimento do condomínio não encontrada: {knowledge_path}"
        ) from exc
    if size > MAX_KNOWLEDGE_BYTES:
        raise ValueError(
            f"Base de conhecimento excede o limite de {MAX_KNOWLEDGE_BYTES} bytes."
        )

    content = knowledge_path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError("Base de conhecimento do condomínio está vazia.")
    return content


def format_condominium_context(content: str, source: str = "injetado") -> str:
    """Delimit condominium data as content, not executable instructions."""
    normalized = content.strip()
    if not normalized:
        raise ValueError("Base de conhecimento do condomínio está vazia.")
    safe_source = escape(source, quote=True)
    safe_content = escape(normalized)
    return (
        f'<conhecimento_condominio fonte="{safe_source}" '
        'tipo="dados_operacionais">\n'
        f"{safe_content}\n"
        "</conhecimento_condominio>"
    )
