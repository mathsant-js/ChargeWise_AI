import os
from typing import Any, Dict

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.output_parsers import PydanticOutputParser

from src.config import MODELO_IA
from src.schemas.consulta_recarga import ConsultaRecarga
from src.guardrails.scope_validator import validate_scope
from src.guardrails.moderation import moderate_output

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

# Store for session histories
store = {}

def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

def create_chain():
    """
    Creates a real LCEL chain: prompt | llm | parser.
    Integrated with RunnableWithMessageHistory for per-session memory.
    """
    system_prompt = _load_system_prompt()
    
    # 1. Define the prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ])

    # 2. Initialize the model
    # Use the centralized MODELO_IA, OLLAMA_HOST and OLLAMA_HEADERS from config.py
    from src.config import MODELO_IA, OLLAMA_HOST, OLLAMA_HEADERS
    llm = ChatOllama(
        model=MODELO_IA, 
        base_url=OLLAMA_HOST, 
        headers=OLLAMA_HEADERS,
        temperature=0.2
    )

    # 3. Structured output parser
    parser = PydanticOutputParser(pydantic_object=ConsultaRecarga)
    
    # We instruct the model to output JSON by adding formatting instructions to the prompt
    prompt = prompt.partial(format_instructions=parser.get_format_instructions())
    # Add format instructions to the system message for better compliance
    # (Simplified here; in production, we'd merge them into the system prompt)
    
    # 4. Build the LCEL chain
    # Instead of a direct pipe to the parser which can crash on invalid JSON,
    # we create a robust parsing and moderation function.
    
    def robust_parse_and_moderate(llm_output):
        """
        Tries to parse the LLM output as JSON using the Pydantic parser.
        If parsing fails, it treats the output as plain text and passes it to moderation.
        """
        # llm_output is a BaseMessage (from ChatOllama)
        raw_text = llm_output.content
        
        try:
            # Attempt to parse as structured JSON
            parsed_obj = parser.parse(raw_text)
            # If successful, we validate via moderation
            return moderate_output(parsed_obj.model_dump())
        except Exception:
            # If parsing fails (plain text or bad JSON), we treat it as a raw response
            # and let the moderation guardrail handle it.
            return moderate_output({"resposta": raw_text})

    from langchain_core.runnables import RunnableLambda
    # Final Chain: Prompt -> LLM -> Robust Parsing & Moderation
    full_chain = prompt | llm | RunnableLambda(robust_parse_and_moderate)

    # 5. Add Message History
    return RunnableWithMessageHistory(
        full_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="history",
    )

class LCELChainWrapper:
    """
    A wrapper to maintain the .invoke() interface for the application,
    including the pre-model scope validation.
    """
    def __init__(self):
        self.chain = create_chain()

    def invoke(self, user_input: str, session_id: str = "default") -> Dict[str, Any]:
        # Guardrails: verify input scope
        if not validate_scope(user_input):
            return {
                "intencao": "fora_do_escopo",
                "resposta": "Não posso atender a essa solicitação.",
                "confianca": 0.0,
            }
        
        # Invoke the LangChain LCEL chain
        return self.chain.invoke(
            {"input": user_input},
            config={"configurable": {"session_id": session_id}}
        )

def create_chain_wrapper():
    return LCELChainWrapper()

