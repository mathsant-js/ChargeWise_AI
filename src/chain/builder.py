import os
import re
import json
import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
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
    PROMPT_VERSION,
    TEMPERATURE,
    TOP_P,
    USE_MOCK_MODEL,
)
from src.guardrails.moderation import ModerationContext, moderate_output
from src.guardrails.scope_validator import validate_scope
from src.knowledge import format_condominium_context, load_condominium_knowledge
from src.schemas.consulta_recarga import ConsultaRecarga
from src.chain.memoria import (
    MEMORY_HISTORY_KEY,
    MEMORY_INPUT_KEY,
    SessionMemoryStore,
    count_message_tokens,
    count_messages_tokens,
    count_text_tokens,
    trim_history,
    truncate_text,
)


def available_prompt_versions() -> dict[str, str]:
    """Return prompt versions discovered from versioned filenames."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    prompts_dir = os.path.join(base_dir, "prompts")
    discovered: dict[str, str] = {}
    if not os.path.isdir(prompts_dir):
        return discovered
    for filename in os.listdir(prompts_dir):
        match = re.fullmatch(r"system_prompt_v(\d+)\.md", filename)
        if match:
            discovered[f"v{int(match.group(1))}"] = os.path.join(prompts_dir, filename)
    return dict(sorted(discovered.items(), key=lambda item: int(item[0][1:])))


def _load_system_prompt(version: str | None = None) -> tuple[str, str]:
    """Load an explicit prompt version or automatically select the highest one."""
    prompts = available_prompt_versions()
    if not prompts:
        raise FileNotFoundError("Nenhum system prompt versionado foi encontrado.")
    selected = (version or PROMPT_VERSION or max(prompts, key=lambda item: int(item[1:]))).lower()
    if selected not in prompts:
        available = ", ".join(prompts)
        raise ValueError(f"Versão de prompt inválida: {selected}. Disponíveis: {available}.")
    path = prompts[selected]
    with open(path, "r", encoding="utf-8") as prompt_file:
        return prompt_file.read(), selected


parser = PydanticOutputParser(pydantic_object=ConsultaRecarga)


class ValidatedOutput(dict[str, Any]):
    """Public response data carrying non-serialized parser diagnostics."""

    def __init__(
        self,
        data: dict[str, Any],
        schema_valid: bool,
        diagnostics: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(data)
        self.schema_valid = schema_valid
        self.diagnostics = diagnostics or {}


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
        asks_contextual_cost = bool(re.search(r"\bquanto\b.{0,30}\bcusta\b", normalized))
        current_consumption_matches = re.findall(
            r"(\d+(?:[.,]\d+)?)\s*kwh\b", normalized
        )
        historical_consumption_matches = re.findall(
            r"(\d+(?:[.,]\d+)?)\s*kwh\b", user_context
        )
        current_tariff_matches = re.findall(
            r"tarifa\s+(?:de\s+)?r\$\s*(\d+(?:[.,]\d+)?)", normalized
        )
        historical_tariff_matches = re.findall(
            r"tarifa\s+(?:de\s+)?r\$\s*(\d+(?:[.,]\d+)?)", user_context
        )
        condominium_tariffs = re.findall(
            r"tarifa\s+padr[aã]o:\s*r\$\s*(\d+(?:[.,]\d+)?)", context, re.I
        )
        estimated_value = None
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
        elif asks_contextual_cost and (
            current_consumption_matches or historical_consumption_matches
        ) and (current_tariff_matches or historical_tariff_matches or condominium_tariffs):
            current_scenario = bool(current_consumption_matches)
            consumption_source = (
                current_consumption_matches[-1]
                if current_scenario
                else historical_consumption_matches[-1]
            )
            if current_tariff_matches:
                tariff_source = current_tariff_matches[-1]
            elif current_scenario and condominium_tariffs:
                tariff_source = condominium_tariffs[-1]
            elif historical_tariff_matches:
                tariff_source = historical_tariff_matches[-1]
            else:
                tariff_source = condominium_tariffs[-1]
            consumption = float(consumption_source.replace(",", "."))
            tariff = float(tariff_source.replace(",", "."))
            estimated_value = round(consumption * tariff, 2)
            intent = "faturamento"
            answer = f"A recarga custa aproximadamente R$ {estimated_value:.2f}."
        elif "tarifa" in normalized and condominium_tariffs:
            tariff = float(condominium_tariffs[-1].replace(",", "."))
            intent = "faturamento"
            answer = f"A tarifa padrão do condomínio é R$ {tariff:.2f}/kWh."
        elif re.search(r"quantos?\s+carregadores?", normalized):
            quantities = re.findall(
                r"quantidade\s+de\s+carregadores:\s*(\d+)", context, re.I
            )
            intent = "status_carregador"
            answer = (
                f"O condomínio possui {quantities[-1]} carregadores."
                if quantities
                else "A quantidade de carregadores não está disponível na base."
            )
        elif "potência média" in normalized or "potencia media" in normalized:
            powers = re.findall(r"pot[eê]ncia\s+m[eé]dia:\s*(\d+(?:[.,]\d+)?)\s*kw", context, re.I)
            intent = "potencia"
            answer = (
                f"A potência média dos carregadores do condomínio é {powers[-1]} kW."
                if powers
                else "A potência média não está disponível na base."
            )
        elif "horário de pico" in normalized or "horario de pico" in normalized:
            peaks = re.findall(r"hor[aá]rio\s+de\s+pico:\s*([^\n<]+)", context, re.I)
            intent = "status_carregador"
            answer = (
                f"O horário de pico de carregamento é {peaks[-1].strip()}."
                if peaks
                else "O horário de pico não está disponível na base."
            )
        elif any(term in normalized for term in ("reserv", "agendamento")):
            intent = "status_carregador"
            if any(term in normalized for term in ("prioridade", "conflito", "primeiro")):
                priorities = re.findall(r"prioridade\s+para\s+([^\n<.]+)", context, re.I)
                answer = (
                    f"Em conflitos de horário, a prioridade é para {priorities[-1].strip()}."
                    if priorities
                    else "A prioridade em conflitos não está disponível na base."
                )
            else:
                limits = re.findall(r"reservas?\s+de\s+at[eé]\s+(\d+)\s+horas?", context, re.I)
                answer = (
                    f"A política permite reservas de até {limits[-1]} horas por morador."
                    if limits
                    else "A política de reservas não está disponível na base."
                )
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
            valor_estimado=estimated_value,
            confianca=0.7,
        ).model_dump_json()
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])


def robust_parse_and_moderate(
    llm_output: BaseMessage,
    moderation_context: ModerationContext | None = None,
) -> ValidatedOutput:
    """Parse structured JSON and always apply post-model moderation."""
    raw_text = str(llm_output.content)
    diagnostics = {
        "raw_output": raw_text,
        "usage_metadata": dict(getattr(llm_output, "usage_metadata", None) or {}),
        "response_metadata": dict(getattr(llm_output, "response_metadata", None) or {}),
    }
    try:
        raw_data = json.loads(
            raw_text,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"Constante JSON inválida: {value}")
            ),
        )
        parsed_obj = ConsultaRecarga.model_validate(raw_data)
        moderated = moderate_output(parsed_obj.model_dump(), moderation_context)
        return ValidatedOutput(moderated, schema_valid=True, diagnostics=diagnostics)
    except (json.JSONDecodeError, TypeError, ValueError):
        return ValidatedOutput(
            moderate_output({"resposta": raw_text}),
            schema_valid=False,
            diagnostics=diagnostics,
        )


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
    prompt_version: str | None = None,
    knowledge_content: str | None = None,
    knowledge_source: str | None = None,
):
    """Build the LCEL chain with isolated, token-bounded session history."""
    chat_model = model or _create_model()
    system_prompt, selected_prompt_version = _load_system_prompt(prompt_version)
    if selected_prompt_version != "v4" and knowledge_content is not None:
        raise ValueError("Conhecimento condominial customizado exige prompt v4.")
    condominium_context = None
    if selected_prompt_version == "v4":
        resolved_knowledge = knowledge_content if knowledge_content is not None else load_condominium_knowledge()
        resolved_source = knowledge_source or (
            "injetado" if knowledge_content is not None else "data/conhecimento_condominio_v2.md"
        )
        condominium_context = format_condominium_context(resolved_knowledge, resolved_source)
    format_instructions = parser.get_format_instructions()
    prompt_messages: list[Any] = [
        ("system", system_prompt + "\n\n{format_instructions}"),
    ]
    fixed_messages = [
        SystemMessage(content=system_prompt + "\n\n" + format_instructions),
    ]
    if condominium_context is not None:
        prompt_messages.append(("system", condominium_context))
        fixed_messages.append(SystemMessage(content=condominium_context))
    prompt_messages.extend(
        [MessagesPlaceholder(variable_name=MEMORY_HISTORY_KEY), ("human", "{" + MEMORY_INPUT_KEY + "}")]
    )
    prompt = ChatPromptTemplate.from_messages(prompt_messages).partial(
        format_instructions=format_instructions
    )

    fixed_tokens = count_messages_tokens(fixed_messages)
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
        prompt_version: str | None = None,
        knowledge_content: str | None = None,
        knowledge_source: str | None = None,
    ) -> None:
        chat_model = model or _create_model()
        system_prompt, selected_prompt_version = _load_system_prompt(prompt_version)
        self.prompt_version = selected_prompt_version
        self.system_prompt = system_prompt
        if selected_prompt_version != "v4" and knowledge_content is not None:
            raise ValueError("Conhecimento condominial customizado exige prompt v4.")
        resolved_knowledge = None
        resolved_source = None
        self.condominium_context = None
        if selected_prompt_version == "v4":
            resolved_knowledge = (
                knowledge_content if knowledge_content is not None else load_condominium_knowledge()
            )
            resolved_source = knowledge_source or (
                "injetado" if knowledge_content is not None else "data/conhecimento_condominio_v2.md"
            )
            self.condominium_context = format_condominium_context(
                resolved_knowledge, resolved_source
            )
        format_instructions = parser.get_format_instructions()
        fixed_messages = [SystemMessage(content=system_prompt + "\n\n" + format_instructions)]
        if self.condominium_context is not None:
            fixed_messages.append(SystemMessage(content=self.condominium_context))
        fixed_tokens = count_messages_tokens(fixed_messages)
        memory_limit = history_limit - max_output_tokens - fixed_tokens
        if memory_limit < 1:
            raise ValueError("MESSAGE_TOKEN_LIMIT é insuficiente para o prompt, conhecimento e a saída reservada.")
        self.memory_store = SessionMemoryStore(chat_model, memory_limit)
        self._schema_validity: dict[str, bool] = {}
        self._turn_diagnostics: dict[str, dict[str, Any]] = {}
        self._guardrail_history: dict[str, list[str]] = {}
        self.chain = create_chain(
            model=chat_model,
            history_limit=history_limit,
            max_output_tokens=max_output_tokens,
            memory_store=self.memory_store,
            moderation_context=moderation_context,
            prompt_version=selected_prompt_version,
            knowledge_content=resolved_knowledge,
            knowledge_source=resolved_source,
        )

    def invoke(self, user_input: str, session_id: str = "default") -> dict[str, Any]:
        prior_inputs = self._guardrail_history.get(session_id, [])[-4:]
        decision = validate_scope(user_input, " ".join(prior_inputs))
        self._guardrail_history.setdefault(session_id, []).append(user_input)
        self._guardrail_history[session_id] = self._guardrail_history[session_id][-5:]
        if not decision.allowed:
            self._schema_validity[session_id] = True
            self._turn_diagnostics[session_id] = {
                "model_called": False,
                "blocked_category": decision.category.value if decision.category else None,
                "estimated_input_tokens": 0,
                "estimated_history_tokens": 0,
                "estimated_output_tokens": 0,
                "provider_usage": {},
                "response_metadata": {},
                "raw_model_output": None,
                "model_latency_ms": None,
            }
            return decision.refusal()

        bounded_user_input = truncate_text(user_input, max(1, self.memory_store.token_limit - 4))
        input_message = HumanMessage(content=bounded_user_input)
        available_history = max(
            0,
            self.memory_store.token_limit - count_message_tokens(input_message),
        )
        history = trim_history(
            list(self.memory_store.get_session_history(session_id).messages),
            available_history,
        )
        system_message = SystemMessage(
            content=self.system_prompt + "\n\n" + parser.get_format_instructions()
        )
        knowledge_messages = (
            [SystemMessage(content=self.condominium_context)]
            if self.condominium_context is not None
            else []
        )
        estimated_history_tokens = count_messages_tokens(history)
        estimated_input_tokens = count_messages_tokens(
            [system_message, *knowledge_messages, *history, input_message]
        )
        started = time.perf_counter()
        result = self.chain.invoke(
            {MEMORY_INPUT_KEY: user_input},
            config={"configurable": {"session_id": session_id}},
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        self._schema_validity[session_id] = getattr(result, "schema_valid", False)
        raw_diagnostics = getattr(result, "diagnostics", {})
        response_metadata = raw_diagnostics.get("response_metadata", {})
        provider_duration = response_metadata.get("total_duration")
        provider_latency_ms = (
            provider_duration / 1_000_000
            if isinstance(provider_duration, (int, float))
            else None
        )
        self._turn_diagnostics[session_id] = {
            "model_called": True,
            "blocked_category": None,
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_history_tokens": estimated_history_tokens,
            "estimated_output_tokens": count_text_tokens(raw_diagnostics.get("raw_output", "")),
            "provider_usage": raw_diagnostics.get("usage_metadata", {}),
            "response_metadata": response_metadata,
            "raw_model_output": raw_diagnostics.get("raw_output"),
            "model_latency_ms": provider_latency_ms or round(elapsed_ms, 2),
        }
        return dict(result)

    def clear_session(self, session_id: str) -> None:
        self.memory_store.clear(session_id)
        self._guardrail_history.pop(session_id, None)

    def memory_metrics(self, session_id: str) -> dict[str, Any]:
        return self.memory_store.metrics(session_id)

    def structured_output_valid(self, session_id: str) -> bool:
        return self._schema_validity.get(session_id, False)

    def turn_diagnostics(self, session_id: str) -> dict[str, Any]:
        return dict(self._turn_diagnostics.get(session_id, {}))


def create_chain_wrapper(
    model: BaseChatModel | None = None,
    history_limit: int = MESSAGE_TOKEN_LIMIT,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
    moderation_context: ModerationContext | None = None,
    prompt_version: str | None = None,
    knowledge_content: str | None = None,
    knowledge_source: str | None = None,
) -> LCELChainWrapper:
    return LCELChainWrapper(
        model=model,
        history_limit=history_limit,
        max_output_tokens=max_output_tokens,
        moderation_context=moderation_context,
        prompt_version=prompt_version,
        knowledge_content=knowledge_content,
        knowledge_source=knowledge_source,
    )
