"""Embeddings Ollama para o índice RAG."""

from __future__ import annotations

import os

from langchain_ollama import OllamaEmbeddings


DEFAULT_MODEL = "nomic-embed-text"


def create_embeddings(model: str | None = None, base_url: str | None = None) -> OllamaEmbeddings:
    """Usa OLLAMA_BASE_URL; omiti-lo usa o endpoint local padrão do Ollama."""
    settings = {"model": model or os.getenv("OLLAMA_EMBED_MODEL", DEFAULT_MODEL)}
    url = base_url or os.getenv("OLLAMA_BASE_URL")
    if url:
        settings["base_url"] = url
    return OllamaEmbeddings(**settings)
