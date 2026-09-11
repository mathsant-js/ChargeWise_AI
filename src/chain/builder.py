import os
from typing import Any

import tiktoken
from langchain.memory import ConversationTokenBufferMemory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_ollama import ChatOllama

from src.config import (
    MAX_OUTPUT_TOKENS,
    MESSAGE_TOKEN_LIMIT,
    MODELO_IA,
    OLLAMA_API_KEY,
    OLLAMA_HOST,
    TEMPERATURE,
    TOP_P,
    USE_MOCK_MODEL,
)
from src.guardrails.moderation import moderate_output
from src.guardrails.scope_validator import validate_scope
from src.schemas.consulta_recarga import ConsultaRecarga


def _load_system_prompt() -> str:
    """Load the latest system prompt (v2 if present, otherwise v1)."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    prompts_dir = os.path.join(base_dir, "prompts")
    v2_path = os.path.join(prompts_dir, "system_prompt_v2.md")
    v1_path = os.path.join(prompts_dir, "system_prompt_v1.md")
    path = v2_path if os.path.isfile(v2_path) else v1_path
    if not os.path.isfile(path):
        return "System prompt not found."
    with open(path, "r", encoding="utf-8") as prompt_file:
        return prompt_file.read()


parser = PydanticOutputParser(pydantic_object=ConsultaRecarga)
_tokenizer = tiktoken.get_encoding("cl100k_base")


class DeterministicChatModel(BaseChatModel):
    """Offline fallback used when the cloud endpoint has no API key."""

    @property
    def _llm_type(self) -> str:
        return "chargewise-deterministic"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        del stop, run_manager, kwargs
        question = next(
            (str(message.content) for message in reversed(messages) if isinstance(message, HumanMessage)),
            "",
        )
        normalized = question.lower()
        if any(term in normalized for term in ("custo", "custou", "tarifa", "preço", "preco", "valor", "gastei", "reais")):
            intent = "faturamento"
            answer = "O custo é calculado por consumo em kWh multiplicado pela tarifa em R$/kWh."
        elif any(term in normalized for term in ("status", "online", "offline", "estado", "terminou", "manutenção", "manutencao", "sessão ativa")):
            intent = "status_carregador"
            answer = "Informe a telemetria ou o identificador do carregador para consultar o estado."
        elif any(term in normalized for term in ("sustent", "solar", "emiss", "co2", "renovável", "renovavel", "ambiental", "fotovoltaic")):
            intent = "sustentabilidade"
            answer = "A recarga pode ser combinada com geração solar para reduzir o uso da rede."
        else:
            intent = "potencia"
            answer = "A potência e o tempo dependem do carregador e do veículo informados."
        content = ConsultaRecarga(
            intencao=intent,
            resposta=answer,
            confianca=0.7,
        ).model_dump_json()
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])


def _message_tokens(message: BaseMessage) -> int:
    return len(_tokenizer.encode(str(message.content))) + 4


def _trim_messages(messages: list[BaseMessage], token_limit: int) -> list[BaseMessage]:
    selected: list[BaseMessage] = []
    used = 0
    for message in reversed(messages):
        token_count = _message_tokens(message)
        if not selected and token_count > token_limit:
            tokens = _tokenizer.encode(str(message.content))[-max(1, token_limit - 4) :]
            selected.append(message.model_copy(update={"content": _tokenizer.decode(tokens)}))
            break
        if used + token_count > token_limit:
            break
        selected.append(message)
        used += token_count
    return list(reversed(selected))


class TokenBufferChatMessageHistory(InMemoryChatMessageHistory):
    """In-memory history that enforces the configured token budget on every write."""

    token_limit: int

    def add_messages(self, messages: list[BaseMessage]) -> None:
        super().add_messages(messages)
        self.messages = _trim_messages(self.messages, self.token_limit)


def robust_parse_and_moderate(llm_output: BaseMessage) -> dict[str, Any]:
    """Parse structured JSON and always apply post-model moderation."""
    raw_text = str(llm_output.content)
    try:
        parsed_obj = parser.parse(raw_text)
        return moderate_output(parsed_obj.model_dump())
    except Exception:
        return moderate_output({"resposta": raw_text})


def _create_model() -> BaseChatModel:
    if USE_MOCK_MODEL:
        return DeterministicChatModel()
    client_kwargs: dict[str, Any] = {}
    if OLLAMA_API_KEY:
        client_kwargs["headers"] = {"Authorization": f"Bearer {OLLAMA_API_KEY}"}
    return ChatOllama(
        model=MODELO_IA,
        base_url=OLLAMA_HOST,
        client_kwargs=client_kwargs,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        num_predict=MAX_OUTPUT_TOKENS,
    )


def create_chain(
    model: BaseChatModel | None = None,
    history_limit: int = MESSAGE_TOKEN_LIMIT,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
):
    """Build the LCEL chain with isolated, token-bounded session history."""
    chat_model = model or _create_model()
    system_prompt = _load_system_prompt()
    format_instructions = parser.get_format_instructions()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt + "\n\n{format_instructions}"),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    ).partial(format_instructions=format_instructions)

    fixed_tokens = len(_tokenizer.encode(system_prompt + format_instructions))
    history_budget = max(1, history_limit - max_output_tokens - fixed_tokens)
    memories: dict[str, ConversationTokenBufferMemory] = {}

    def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
        if session_id not in memories:
            chat_history = TokenBufferChatMessageHistory(token_limit=history_budget)
            memories[session_id] = ConversationTokenBufferMemory(
                llm=chat_model,
                chat_memory=chat_history,
                return_messages=True,
                max_token_limit=history_budget,
            )
        return memories[session_id].chat_memory

    def bounded_history(values: dict[str, Any]) -> list[BaseMessage]:
        input_tokens = _message_tokens(HumanMessage(content=str(values["input"])))
        return _trim_messages(values.get("history", []), max(1, history_budget - input_tokens))

    model_chain = (
        RunnablePassthrough.assign(history=RunnableLambda(bounded_history))
        | prompt
        | chat_model
    )
    with_history = RunnableWithMessageHistory(
        model_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )
    return with_history | RunnableLambda(robust_parse_and_moderate)


class LCELChainWrapper:
    def __init__(
        self,
        model: BaseChatModel | None = None,
        history_limit: int = MESSAGE_TOKEN_LIMIT,
    ) -> None:
        self.chain = create_chain(model=model, history_limit=history_limit)

    def invoke(self, user_input: str, session_id: str = "default") -> dict[str, Any]:
        if not validate_scope(user_input):
            return {
                "intencao": "fora_do_escopo",
                "resposta": "Não posso atender a essa solicitação.",
                "confianca": 0.0,
            }

        return self.chain.invoke(
            {"input": user_input},
            config={"configurable": {"session_id": session_id}},
        )


def create_chain_wrapper(
    model: BaseChatModel | None = None,
    history_limit: int = MESSAGE_TOKEN_LIMIT,
) -> LCELChainWrapper:
    return LCELChainWrapper(model=model, history_limit=history_limit)
