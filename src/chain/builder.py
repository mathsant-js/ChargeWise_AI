import os
import re
import json
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
from src.guardrails.moderation import ModerationContext, moderate_output
from src.guardrails.scope_validator import validate_scope
from src.schemas.consulta_recarga import ConsultaRecarga
from src.chain.memoria import (
    MEMORY_HISTORY_KEY,
    MEMORY_INPUT_KEY,
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


class ValidatedOutput(dict[str, Any]):
    """Public response data carrying non-serialized parser diagnostics."""

    def __init__(self, data: dict[str, Any], schema_valid: bool) -> None:
        super().__init__(data)
        self.schema_valid = schema_valid


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
        context = " ".join(str(message.content) for message in messages)
        user_context = " ".join(
            str(message.content)
            for message in messages
            if isinstance(message, HumanMessage)
        ).lower()
        charger_ids = re.findall(r"\bGW-[A-Z0-9-]+\b", context, re.IGNORECASE)
        asks_context = "qual carregador" in normalized or "qual é o problema" in normalized
        if asks_context and charger_ids:
            charger_id = charger_ids[-1].upper()
            is_offline = "offline" in context.lower()
            problem = (
                "está offline desde ontem"
                if "offline desde ontem" in user_context
                else "está offline"
            )
            answer = (
                f"Você mencionou o carregador {charger_id}, que {problem}."
                if is_offline
                else f"Você mencionou o carregador {charger_id}; não há problema registrado no histórico."
            )
            intent = "status_carregador"
        elif any(term in normalized for term in ("custo", "custou", "tarifa", "preço", "preco", "valor", "gastei", "reais")):
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


def robust_parse_and_moderate(
    llm_output: BaseMessage,
    moderation_context: ModerationContext | None = None,
) -> ValidatedOutput:
    """Parse structured JSON and always apply post-model moderation."""
    raw_text = str(llm_output.content)
    try:
        raw_data = json.loads(
            raw_text,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"Constante JSON inválida: {value}")
            ),
        )
        parsed_obj = ConsultaRecarga.model_validate(raw_data)
        moderated = moderate_output(parsed_obj.model_dump(), moderation_context)
        return ValidatedOutput(moderated, schema_valid=True)
    except (json.JSONDecodeError, TypeError, ValueError):
        return ValidatedOutput(moderate_output({"resposta": raw_text}), schema_valid=False)


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
    moderation_context: ModerationContext | None = None,
):
    """Build the LCEL chain with isolated, token-bounded session history."""
    chat_model = model or _create_model()
    system_prompt = _load_system_prompt()
    format_instructions = parser.get_format_instructions()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt + "\n\n{format_instructions}"),
            MessagesPlaceholder(variable_name=MEMORY_HISTORY_KEY),
            ("human", "{" + MEMORY_INPUT_KEY + "}"),
        ]
    ).partial(format_instructions=format_instructions)

    fixed_tokens = count_text_tokens(system_prompt + format_instructions)
    history_budget = history_limit - max_output_tokens - fixed_tokens
    if history_budget < 1:
        raise ValueError("MESSAGE_TOKEN_LIMIT é insuficiente para o prompt e a saída reservada.")
    store = memory_store or SessionMemoryStore(chat_model, history_budget)

    def bounded_history(values: dict[str, Any]) -> list[BaseMessage]:
        bounded_input = truncate_text(
            str(values[MEMORY_INPUT_KEY]), max(1, history_budget - 4)
        )
        input_tokens = count_message_tokens(HumanMessage(content=bounded_input))
        available = max(0, history_budget - input_tokens)
        return trim_history(values.get(MEMORY_HISTORY_KEY, []), available)

    def bounded_input(values: dict[str, Any]) -> str:
        return truncate_text(
            str(values[MEMORY_INPUT_KEY]), max(1, history_budget - 4)
        )

    model_chain = (
        RunnablePassthrough.assign(
            **{
                MEMORY_HISTORY_KEY: RunnableLambda(bounded_history),
                MEMORY_INPUT_KEY: RunnableLambda(bounded_input),
            }
        )
        | prompt
        | chat_model
    )
    with_history = RunnableWithMessageHistory(
        model_chain,
        store.get_session_history,
        input_messages_key=MEMORY_INPUT_KEY,
        history_messages_key=MEMORY_HISTORY_KEY,
    )
    return with_history | RunnableLambda(
        lambda output: robust_parse_and_moderate(output, moderation_context)
    )


class LCELChainWrapper:
    def __init__(
        self,
        model: BaseChatModel | None = None,
        history_limit: int = MESSAGE_TOKEN_LIMIT,
        max_output_tokens: int = MAX_OUTPUT_TOKENS,
        moderation_context: ModerationContext | None = None,
    ) -> None:
        chat_model = model or _create_model()
        system_prompt = _load_system_prompt()
        fixed_tokens = count_text_tokens(system_prompt + parser.get_format_instructions())
        memory_limit = history_limit - max_output_tokens - fixed_tokens
        self.memory_store = SessionMemoryStore(chat_model, memory_limit)
        self._schema_validity: dict[str, bool] = {}
        self.chain = create_chain(
            model=chat_model,
            history_limit=history_limit,
            max_output_tokens=max_output_tokens,
            memory_store=self.memory_store,
            moderation_context=moderation_context,
        )

    def invoke(self, user_input: str, session_id: str = "default") -> dict[str, Any]:
        if not validate_scope(user_input):
            self._schema_validity[session_id] = True
            return {
                "intencao": "fora_do_escopo",
                "resposta": "Não posso atender a essa solicitação.",
                "confianca": 0.0,
            }

        result = self.chain.invoke(
            {MEMORY_INPUT_KEY: user_input},
            config={"configurable": {"session_id": session_id}},
        )
        self._schema_validity[session_id] = getattr(result, "schema_valid", False)
        return dict(result)

    def clear_session(self, session_id: str) -> None:
        self.memory_store.clear(session_id)

    def memory_metrics(self, session_id: str) -> dict[str, Any]:
        return self.memory_store.metrics(session_id)

    def structured_output_valid(self, session_id: str) -> bool:
        return self._schema_validity.get(session_id, False)


def create_chain_wrapper(
    model: BaseChatModel | None = None,
    history_limit: int = MESSAGE_TOKEN_LIMIT,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
    moderation_context: ModerationContext | None = None,
) -> LCELChainWrapper:
    return LCELChainWrapper(
        model=model,
        history_limit=history_limit,
        max_output_tokens=max_output_tokens,
        moderation_context=moderation_context,
    )
