import os
from typing import Any

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
from src.chain.memoria import (
    SessionMemoryStore,
    count_message_tokens,
    count_text_tokens,
    trim_history,
    truncate_text,
)


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
    memory_store: SessionMemoryStore | None = None,
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

    fixed_tokens = count_text_tokens(system_prompt + format_instructions)
    history_budget = history_limit - max_output_tokens - fixed_tokens
    if history_budget < 1:
        raise ValueError("MESSAGE_TOKEN_LIMIT é insuficiente para o prompt e a saída reservada.")
    store = memory_store or SessionMemoryStore(chat_model, history_budget)

    def bounded_history(values: dict[str, Any]) -> list[BaseMessage]:
        bounded_input = truncate_text(str(values["input"]), max(1, history_budget - 4))
        input_tokens = count_message_tokens(HumanMessage(content=bounded_input))
        available = max(0, history_budget - input_tokens)
        return trim_history(values.get("history", []), available)

    def bounded_input(values: dict[str, Any]) -> str:
        return truncate_text(str(values["input"]), max(1, history_budget - 4))

    model_chain = (
        RunnablePassthrough.assign(
            history=RunnableLambda(bounded_history),
            input=RunnableLambda(bounded_input),
        )
        | prompt
        | chat_model
    )
    with_history = RunnableWithMessageHistory(
        model_chain,
        store.get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )
    return with_history | RunnableLambda(robust_parse_and_moderate)


class LCELChainWrapper:
    def __init__(
        self,
        model: BaseChatModel | None = None,
        history_limit: int = MESSAGE_TOKEN_LIMIT,
        max_output_tokens: int = MAX_OUTPUT_TOKENS,
    ) -> None:
        chat_model = model or _create_model()
        system_prompt = _load_system_prompt()
        fixed_tokens = count_text_tokens(system_prompt + parser.get_format_instructions())
        memory_limit = history_limit - max_output_tokens - fixed_tokens
        self.memory_store = SessionMemoryStore(chat_model, memory_limit)
        self.chain = create_chain(
            model=chat_model,
            history_limit=history_limit,
            max_output_tokens=max_output_tokens,
            memory_store=self.memory_store,
        )

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

    def clear_session(self, session_id: str) -> None:
        self.memory_store.clear(session_id)

    def memory_metrics(self, session_id: str) -> dict[str, Any]:
        return self.memory_store.metrics(session_id)


def create_chain_wrapper(
    model: BaseChatModel | None = None,
    history_limit: int = MESSAGE_TOKEN_LIMIT,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
) -> LCELChainWrapper:
    return LCELChainWrapper(
        model=model,
        history_limit=history_limit,
        max_output_tokens=max_output_tokens,
    )
