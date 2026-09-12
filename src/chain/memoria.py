import re
from typing import Any

import tiktoken
from langchain.memory import ConversationTokenBufferMemory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import BaseMessage, SystemMessage


MEMORY_INPUT_KEY = "input"
MEMORY_HISTORY_KEY = "history"
TOKEN_COUNTING_MODEL = "cl100k_base"

_tokenizer = tiktoken.get_encoding(TOKEN_COUNTING_MODEL)
_SPACE = re.compile(r"\s+")
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_FACT = re.compile(
    r"\b(?:\d+(?:[.,]\d+)?|r\$|kw|kwh|carregador|wallbox|tarifa|status|"
    r"online|offline|sess[aã]o|garagem|apartamento)\b",
    re.IGNORECASE,
)
_SUMMARY_PREFIX = "Resumo determinístico dos turnos anteriores:\n"


def count_text_tokens(text: str) -> int:
    return len(_tokenizer.encode(text))


def count_message_tokens(message: BaseMessage) -> int:
    return count_text_tokens(str(message.content)) + 4


def count_messages_tokens(messages: list[BaseMessage]) -> int:
    return sum(count_message_tokens(message) for message in messages)


def truncate_text(text: str, token_limit: int, keep_end: bool = False) -> str:
    if token_limit <= 0:
        return ""
    tokens = _tokenizer.encode(text)
    if len(tokens) <= token_limit:
        return text
    selected = tokens[-token_limit:] if keep_end else tokens[:token_limit]
    return _tokenizer.decode(selected)


def _bounded_summary(text: str, token_limit: int) -> str:
    prefix = _SUMMARY_PREFIX
    body = text.removeprefix(prefix).removeprefix(prefix.rstrip()).strip()
    body_limit = max(0, token_limit - count_text_tokens(prefix) - 4)
    return prefix + truncate_text(body, body_limit, keep_end=True)


def _extract_facts(message: BaseMessage) -> str:
    text = _SPACE.sub(" ", str(message.content)).strip()
    if not text:
        return ""
    sentences = _SENTENCE.split(text)
    selected = [sentence for sentence in sentences if _FACT.search(sentence)]
    if not selected:
        selected = sentences[:1]
    role = "Usuário" if message.type == "human" else "Assistente"
    return f"{role}: {truncate_text(' '.join(selected), 80)}"


def trim_history(messages: list[BaseMessage], token_limit: int) -> list[BaseMessage]:
    """Select recent complete turns, preserving an existing summary when possible."""
    if token_limit <= 0:
        return []

    summary = messages[0] if messages and isinstance(messages[0], SystemMessage) else None
    conversation = messages[1:] if summary else messages
    selected: list[BaseMessage] = []
    used = 0

    index = len(conversation)
    while index > 0:
        start = max(0, index - 2)
        turn = conversation[start:index]
        turn_tokens = count_messages_tokens(turn)
        if used + turn_tokens > token_limit:
            break
        selected[0:0] = turn
        used += turn_tokens
        index = start

    if summary:
        remaining = token_limit - used - 4
        if remaining > 0:
            summary_text = _bounded_summary(str(summary.content), remaining)
            selected.insert(0, SystemMessage(content=summary_text))
    return selected


class DeterministicSummaryHistory(InMemoryChatMessageHistory):
    token_limit: int
    summary_token_limit: int

    def add_messages(self, messages: list[BaseMessage]) -> None:
        super().add_messages(messages)
        self._compact()

    def _compact(self) -> None:
        while count_messages_tokens(self.messages) > self.token_limit:
            summary = (
                self.messages.pop(0)
                if self.messages and isinstance(self.messages[0], SystemMessage)
                else None
            )
            if len(self.messages) < 3:
                self.messages = trim_history(
                    ([summary] if summary else []) + self.messages,
                    self.token_limit,
                )
                return

            removed_turn = self.messages[:2]
            del self.messages[:2]
            facts = "\n".join(filter(None, (_extract_facts(item) for item in removed_turn)))
            previous = str(summary.content) if summary else _SUMMARY_PREFIX.rstrip()
            summary_text = _bounded_summary(
                f"{previous}\n{facts}", self.summary_token_limit
            )
            self.messages.insert(0, SystemMessage(content=summary_text))


class SessionMemoryStore:
    """Own token-bounded conversational memories isolated by session ID."""

    def __init__(
        self,
        llm: BaseLanguageModel,
        token_limit: int,
        summary_ratio: float = 0.25,
    ) -> None:
        if token_limit < 1:
            raise ValueError("O limite de tokens do histórico deve ser positivo.")
        if not 0 < summary_ratio < 1:
            raise ValueError("A proporção do resumo deve estar entre 0 e 1.")
        self.llm = llm
        self.token_limit = token_limit
        self.summary_token_limit = max(32, int(token_limit * summary_ratio))
        self._memories: dict[str, ConversationTokenBufferMemory] = {}

    def get_memory(self, session_id: str) -> ConversationTokenBufferMemory:
        if not session_id:
            raise ValueError("session_id não pode ser vazio.")
        if session_id not in self._memories:
            history = DeterministicSummaryHistory(
                token_limit=self.token_limit,
                summary_token_limit=min(self.summary_token_limit, self.token_limit),
            )
            self._memories[session_id] = ConversationTokenBufferMemory(
                llm=self.llm,
                chat_memory=history,
                input_key=MEMORY_INPUT_KEY,
                memory_key=MEMORY_HISTORY_KEY,
                return_messages=True,
                max_token_limit=self.token_limit,
            )
        return self._memories[session_id]

    def get_session_history(self, session_id: str) -> InMemoryChatMessageHistory:
        return self.get_memory(session_id).chat_memory

    def clear(self, session_id: str) -> None:
        memory = self._memories.pop(session_id, None)
        if memory is not None:
            memory.clear()

    def metrics(self, session_id: str) -> dict[str, Any]:
        messages = self.get_session_history(session_id).messages
        return {
            "message_count": len(messages),
            "history_tokens": count_messages_tokens(messages),
            "has_summary": bool(messages and isinstance(messages[0], SystemMessage)),
        }
