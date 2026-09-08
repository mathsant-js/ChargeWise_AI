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
    if not os.path.isfile(path):
        return "System prompt not found."
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
        # Load system prompt and initialise a per‑session memory manager.
        self.system_prompt = _load_system_prompt()
        from src.chain.memoria import memory_manager
        self.memory_manager = memory_manager

    def invoke(self, user_input: str, session_id: str | None = None) -> Dict[str, Any]:
        # Retrieve the current history for this session (including system prompt).
        # The memory manager guarantees the token budget.
        history = self.memory_manager.get_history(session_id)
        # If the history is empty we start with the system prompt.
        if not history:
            history = [{"role": "system", "content": self.system_prompt}]
        # Append the new user message.
        self.memory_manager.add_message(session_id, "user", user_input)
        # Build the full list of messages (system + prior + new user).
        # Append the user message to memory (already done above) and get the updated history.
        # Ensure the system prompt is the first entry – `memory_manager` never removes it.
        messages = self.memory_manager.get_history(session_id)


        # Ensure the system prompt is present – `memory_manager` guarantees it.
        # The client expects a list of dicts with keys "role" and "content".
        # No further transformation needed.
        # Call the client (real or mock)
        response = client.chat(
            model="gpt-oss:120b",
            messages=messages,
            options={"temperature": 0.3, "num_predict": 800},
            stream=False,
        )
        # Parse the raw model output (may be JSON or plain text)
        raw_output = response["message"]["content"]
        # Post‑model moderation – enforce schema compliance
        from src.guardrails.moderation import moderate_output
        parsed = moderate_output(json.loads(raw_output) if raw_output.strip().startswith('{') else {"resposta": raw_output})
        # Store assistant reply in memory (as plain text for future turns)
        self.memory_manager.add_message(session_id, "assistant", raw_output)
        return parsed



def create_chain() -> LCELChain:
    """Factory function used by tests and the application.
    """
    return LCELChain()
