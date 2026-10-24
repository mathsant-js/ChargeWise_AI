"""Interface Streamlit para o serviço RAG da Sprint 4."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.rag.pipeline import RAGService
from src.rag.retriever import Retriever
from src.rag.vector_store import DEFAULT_COLLECTION, DEFAULT_INDEX

load_dotenv(ROOT / ".env")


@st.cache_resource(show_spinner=False)
def service(index_path: str, model: str, embedding_model: str, k: int,
            prompt_version: str) -> RAGService:
    return RAGService(Retriever(k=k, persist_directory=index_path),
                      prompt_version=prompt_version)


def operational_error(exc: Exception) -> str:
    message = str(exc).lower()
    if ("does not exist" in message or "not found" in message) and (
        "collection" in message or DEFAULT_COLLECTION in message
    ):
        return "Índice não encontrado. Execute `python3 -m src.rag.vector_store index` na raiz do projeto."
    if "embedding" in message and "diferente" in message:
        return "O modelo de embeddings mudou. Recrie o índice com `python3 -m src.rag.vector_store index --reindex`."
    if any(term in message for term in ("connection refused", "failed to connect", "connect error", "connection error")):
        return "Não foi possível conectar ao Ollama. Verifique OLLAMA_HOST, OLLAMA_BASE_URL e se o servidor está ativo."
    if "model" in message and any(term in message for term in ("not found", "does not exist")):
        return "Modelo Ollama indisponível. Instale os modelos de embedding e geração configurados."
    return "A consulta falhou. Confira o índice, os modelos e as configurações do Ollama."


def main() -> None:
    st.set_page_config(page_title="ChargeWise AI", page_icon="⚡")
    st.title("ChargeWise AI")
    st.caption("Consulta à base documental de carregamento e cenário condominial simulado")

    with st.form("consulta"):
        question = st.text_area("Sua pergunta", placeholder="Ex.: Qual é a política de agendamento do carregador?")
        submitted = st.form_submit_button("Enviar pergunta")

    if not submitted:
        return
    if not question.strip():
        st.warning("Digite uma pergunta antes de enviar.")
        return

    try:
        k = int(os.getenv("RAG_TOP_K", "3"))
        if k < 1:
            raise ValueError("RAG_TOP_K deve ser positivo")
        index_path = str(Path(os.getenv("CHROMA_PERSIST_DIR", str(DEFAULT_INDEX))).resolve())
        with st.spinner("Consultando a base documental..."):
            result = service(index_path, os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
                             os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"), k,
                             os.getenv("RAG_PROMPT_VERSION", "v3")).answer(question.strip())
    except Exception as exc:
        st.error(operational_error(exc))
        return

    if result.refused:
        st.warning("Consulta recusada")
    else:
        st.success("Resposta baseada na base documental")
    st.markdown(result.answer)

    if result.sources:
        st.subheader("Fontes")
        for number, source in enumerate(result.sources, 1):
            label = f"[{number}] {source['document']} — {source['section']}"
            if source.get("page"):
                label += f", p. {source['page']}"
            if source.get("authority") == "simulado":
                label += " (cenário simulado)"
            st.markdown(label)


if __name__ == "__main__":
    main()
