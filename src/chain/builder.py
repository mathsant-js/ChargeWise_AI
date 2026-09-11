import os
from typing import Any, Dict, List

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
    # In a real scenario, we'd use the ChatOllama class.
    # To maintain the 'Mock' capability from config.py, one would typically
    # mock the ChatOllama object in tests.
    llm = ChatOllama(model=MODELO_IA, temperature=0.2)

    # 3. Structured output parser
    parser = PydanticOutputParser(pydantic_object=ConsultaRecarga)
    
    # We instruct the model to output JSON by adding formatting instructions to the prompt
    prompt = prompt.partial(format_instructions=parser.get_format_instructions())
    # Add format instructions to the system message for better compliance
    # (Simplified here; in production, we'd merge them into the system prompt)
    
    # 4. Build the LCEL chain
    # chain = prompt | llm | parser
    # However, since we need post-model moderation, we wrap it.
    
    def moderation_wrapper(output):
        # If parser succeeded, output is a ConsultaRecarga object. 
        # We convert it to dict and run moderation.
        if isinstance(output, ConsultaRecarga):
            return moderate_output(output.model_dump())
        
        # If parser failed (returning raw string), moderation handles it.
        return moderate_output({"resposta": str(output)})

    # Full chain construction
    chain = prompt | llm | parser
    
    # We use a functional approach to add moderation at the end of the chain
    # In LCEL: chain = chain | moderation_wrapper (using a RunnableLambda)
    from langchain_core.runnables import RunnableLambda
    full_chain = chain | RunnableLambda(moderation_wrapper)

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

