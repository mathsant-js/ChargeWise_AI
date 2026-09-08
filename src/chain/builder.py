import os
import json
from typing import Any, Dict

from config import client
from src.guardrails.moderation import moderate_output
from src.chain.memoria import memory_manager


def _load_system_prompt() -> str:
    """Load the latest system prompt (v2 if present, otherwise v1)."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    prompts_dir = os.path.join(base_dir, "prompts")
    v2_path = os.path.join(prompts_dir, "system_prompt_v2.md")
    v1_path = os.path.join(prompts_dir, "system_prompt_v1.md")
    path = v2_path if os.path.isfile(v2_path) else v1_path
    if not os.path.isfile(path):
        return "System prompt not found."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class LCELChain:
    """Simple LCEL‑like chain that respects per‑session memory.

    It loads the system prompt, stores it in the in‑memory ``memory_manager``
    (so it persists across turns), sends the assembled messages to the
    ``client`` and finally runs post‑model moderation.
    """

    def __init__(self) -> None:
        self.system_prompt = _load_system_prompt()
        self.memory_manager = memory_manager

    def _ensure_system_prompt(self, session_id: str | None) -> None:
        """Guarantee that the system prompt is the first message for a session."""
        if not self.memory_manager.get_history(session_id):
            self.memory_manager.add_message(session_id, "system", self.system_prompt)

    def invoke(self, user_input: str, session_id: str | None = None) -> Dict[str, Any]:
        # Seed system prompt if necessary.
        self._ensure_system_prompt(session_id)
        # Record user turn.
        self.memory_manager.add_message(session_id, "user", user_input)
        # Retrieve full conversation history.
        messages = self.memory_manager.get_history(session_id)

        # Call the model with the required options.
        response = client.chat(
            model="gpt-oss:120b",
            messages=messages,
            options={"temperature": 0.3, "max_tokens": 800, "top_p": 0.9},
            stream=False,
        )
        raw_output = response["message"]["content"]

        # Post‑model moderation / schema validation.
        if isinstance(raw_output, str) and raw_output.strip().startswith('{'):
            parsed = moderate_output(json.loads(raw_output))
        else:
            parsed = moderate_output({"resposta": raw_output})

        # Store assistant reply for subsequent turns.
        self.memory_manager.add_message(session_id, "assistant", raw_output)
        return parsed


def create_chain() -> LCELChain:
    """Factory used by the application and tests."""
    return LCELChain()
