import os
import json
from typing import Any, Dict

from config import client

# Load the latest system prompt (v2 if exists else v1)
def _load_system_prompt() -> str:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    prompts_dir = os.path.join(base_dir, "prompts")
    v2_path = os.path.join(prompts_dir, "system_prompt_v2.md")
    v1_path = os.path.join(prompts_dir, "system_prompt_v1.md")
    path = v2_path if os.path.isfile(v2_path) else v1_path
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# Simple fallback parser: try JSON -> ConsultaRecarga, otherwise wrap raw text
def _parse_response(raw: str) -> Dict[str, Any]:
    from src.schemas.consulta_recarga import ConsultaRecarga
    try:
        # Assume the model may return a JSON representation of the schema
        data = json.loads(raw)
        # Validate via Pydantic
        model = ConsultaRecarga.model_validate(data)
        return model.model_dump()
    except Exception:
        # Fallback – treat as plain text, set minimal fields
        return ConsultaRecarga(
            intencao="fora_do_escopo",
            resposta=raw,
            confianca=0.5,
        ).model_dump()

class LCELChain:
    """Very lightweight stand‑in for the LangChain LCEL chain.

    It builds a simple prompt, calls the Ollama client (or the mock client) and
    returns a validated ``ConsultaRecarga`` dictionary.
    """

    def __init__(self):
        self.system_prompt = _load_system_prompt()

    def invoke(self, user_input: str, session_id: str | None = None) -> Dict[str, Any]:
        # Build message list – compatible with the expected client interface
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]
        # Call the client (real or mock)
        response = client.chat(
            model="gpt-oss:120b",
            messages=messages,
            options={"temperature": 0.3, "num_predict": 800},
            stream=False,
        )
        raw_text = response["message"]["content"]
        return _parse_response(raw_text)

def create_chain() -> LCELChain:
    """Factory function used by tests and the application.
    """
    return LCELChain()
