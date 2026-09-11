import os
from typing import Annotated, Any, TypedDict

import tiktoken
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, HumanMessage, RemoveMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES, add_messages
from langgraph.graph.state import CompiledStateGraph

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


class GraphState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    structured_output: dict[str, Any]


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


def _trim_messages(
    messages: list[AnyMessage],
    fixed_prompt_tokens: int,
    message_token_limit: int,
    max_output_tokens: int,
) -> list[AnyMessage]:
    budget = max(1, message_token_limit - max_output_tokens - fixed_prompt_tokens)
    selected: list[AnyMessage] = []
    used = 0
    for message in reversed(messages):
        token_count = _message_tokens(message)
        if not selected and token_count > budget:
            tokens = _tokenizer.encode(str(message.content))[-max(1, budget - 4) :]
            selected.append(message.model_copy(update={"content": _tokenizer.decode(tokens)}))
            break
        if selected and used + token_count > budget:
            break
        selected.append(message)
        used += token_count
    return list(reversed(selected))


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


def create_graph(
    model: BaseChatModel | None = None,
    checkpointer: InMemorySaver | None = None,
    history_limit: int = MESSAGE_TOKEN_LIMIT,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
) -> CompiledStateGraph:
    """Build the checkpointed LangGraph conversation core."""
    chat_model = model or _create_model()
    system_prompt = _load_system_prompt()
    format_instructions = parser.get_format_instructions()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt + "\n\n{format_instructions}"),
            MessagesPlaceholder(variable_name="messages"),
        ]
    ).partial(format_instructions=format_instructions)
    fixed_tokens = len(_tokenizer.encode(system_prompt + format_instructions))

    def call_model(state: GraphState) -> GraphState:
        messages = _trim_messages(
            state.get("messages", []), fixed_tokens, history_limit, max_output_tokens
        )
        llm_output = chat_model.invoke(prompt.invoke({"messages": messages}))
        return {
            "messages": [
                RemoveMessage(id=REMOVE_ALL_MESSAGES),
                *messages,
                llm_output,
            ],
            "structured_output": robust_parse_and_moderate(llm_output),
        }

    graph = StateGraph(GraphState)
    graph.add_node("model", call_model)
    graph.add_edge(START, "model")
    graph.add_edge("model", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())


def create_chain(
    model: BaseChatModel | None = None,
    history_limit: int = MESSAGE_TOKEN_LIMIT,
) -> CompiledStateGraph:
    """Compatibility alias for callers that previously created the LCEL chain."""
    return create_graph(model=model, history_limit=history_limit)


class LangGraphChainWrapper:
    def __init__(
        self,
        model: BaseChatModel | None = None,
        history_limit: int = MESSAGE_TOKEN_LIMIT,
    ) -> None:
        self.graph = create_graph(model=model, history_limit=history_limit)
        self.chain = self.graph

    def invoke(self, user_input: str, session_id: str = "default") -> dict[str, Any]:
        if not validate_scope(user_input):
            return {
                "intencao": "fora_do_escopo",
                "resposta": "Não posso atender a essa solicitação.",
                "confianca": 0.0,
            }

        state = self.graph.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config={"configurable": {"thread_id": session_id}},
        )
        return state["structured_output"]


LCELChainWrapper = LangGraphChainWrapper


def create_chain_wrapper(
    model: BaseChatModel | None = None,
    history_limit: int = MESSAGE_TOKEN_LIMIT,
) -> LangGraphChainWrapper:
    return LangGraphChainWrapper(model=model, history_limit=history_limit)
