from src.chain.builder import create_chain_wrapper

class GoodWeChatbot:
    def __init__(self):
        # Use the new LCEL Chain Wrapper instead of legacy manual logic
        self.chain = create_chain_wrapper()

    def responder(self, pergunta, session_id="default"):
        # The chain now handles:
        # 1. Scope Validation (Pre-model)
        # 2. History/Memory (via RunnableWithMessageHistory)
        # 3. LCEL Chain (Prompt | LLM | Parser)
        # 4. Moderation (Post-model)
        
        result = self.chain.invoke(pergunta, session_id=session_id)
        
        # The architecture plan asks for a structured output, 
        # but the main.py expects a string for the final print.
        return result.get("resposta", "Não consegui processar sua solicitação.")
