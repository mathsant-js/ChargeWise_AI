import os
import tiktoken
from typing import List, Dict

# Simple in‑memory manager for session‑scoped conversation history.
# It tracks messages and respects a configurable token limit.

DEFAULT_TOKEN_LIMIT = 500  # adjustable per project needs

_encoding = tiktoken.get_encoding("cl100k_base")

class MemoryManager:
    """Manage per‑session message history with token budgeting.

    The implementation is deliberately lightweight – it stores the history in a
    dictionary for the lifetime of the Python process.  For production you would
    replace this with a persistent store.
    """

    def __init__(self, token_limit: int = DEFAULT_TOKEN_LIMIT):
        self._store: Dict[str, List[Dict[str, str]]] = {}
        self.token_limit = token_limit

    def _count_tokens(self, messages: List[Dict[str, str]]) -> int:
        total = 0
        for msg in messages:
            total += len(_encoding.encode(msg["content"]))
        return total

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return self._store.get(session_id, []).copy()

    def add_message(self, session_id: str, role: str, content: str) -> None:
        # Retrieve current history, append new message, then trim if needed.
        history = self._store.get(session_id, [])
        history.append({"role": role, "content": content})
        # Trim oldest messages until token budget satisfied.
        while self._count_tokens(history) > self.token_limit and len(history) > 1:
            # Remove the earliest (non‑system) message – keep system prompt if present.
            # Assume the first message is the system prompt; never drop it.
            if history[0]["role"] == "system":
                # Drop the next one instead of the system prompt.
                del history[1]
            else:
                del history[0]
        self._store[session_id] = history

# Global singleton used by the chain implementation.
memory_manager = MemoryManager()
