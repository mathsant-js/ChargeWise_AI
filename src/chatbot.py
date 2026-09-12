from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from src.chain.builder import LCELChainWrapper, create_chain_wrapper


class GoodWeChatbot:
    def __init__(
        self,
        model: BaseChatModel | None = None,
        knowledge_content: str | None = None,
        prompt_version: str | None = None,
    ) -> None:
        self.chain: LCELChainWrapper = create_chain_wrapper(
            model=model,
            knowledge_content=knowledge_content,
            prompt_version=prompt_version,
        )
        self.ultima_resposta_estruturada: dict[str, Any] | None = None

    def responder_estruturado(
        self, pergunta: str, session_id: str = "default"
    ) -> dict[str, Any]:
        result = self.chain.invoke(pergunta, session_id=session_id)
        self.ultima_resposta_estruturada = result
        return result

    def responder(self, pergunta: str, session_id: str = "default") -> str:
        result = self.responder_estruturado(pergunta, session_id=session_id)
        return str(result.get("resposta", "Não consegui processar sua solicitação."))

    def limpar_sessao(self, session_id: str = "default") -> None:
        self.chain.clear_session(session_id)
