"""Consulta o índice persistente e devolve evidências com proveniência."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.rag.embeddings import create_embeddings
from src.rag.vector_store import DEFAULT_COLLECTION, DEFAULT_INDEX


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    metadata: dict
    distance: float

    @property
    def citation(self) -> str:
        name = self.metadata.get("document") or self.metadata.get("source")
        section = self.metadata.get("section") or "Seção não informada"
        page = self.metadata.get("page")
        return f"{name} — {section}" + (f", p. {page}" if page else "")


class Retriever:
    def __init__(self, k: int = 4, persist_directory: str | Path = DEFAULT_INDEX,
                 collection_name: str = DEFAULT_COLLECTION, embeddings=None, collection=None):
        if k < 1:
            raise ValueError("k deve ser positivo")
        self.k = k
        self.embeddings = embeddings or create_embeddings()
        if collection is None:
            import chromadb
            collection = chromadb.PersistentClient(path=str(Path(persist_directory).resolve())).get_collection(collection_name)
        self.collection = collection
        indexed_model = (collection.metadata or {}).get("embedding_model")
        active_model = getattr(self.embeddings, "model", None)
        if indexed_model and active_model and indexed_model != active_model:
            raise ValueError("Modelo de embedding diferente do índice; reindexe o corpus")

    def retrieve(self, question: str, k: int | None = None) -> list[RetrievedChunk]:
        limit = self.k if k is None else k
        if limit < 1 or not question.strip():
            raise ValueError("Pergunta e k devem ser válidos")
        result = self.collection.query(query_embeddings=[self.embeddings.embed_query(question)],
                                       n_results=limit, include=["documents", "metadatas", "distances"])
        return [RetrievedChunk(text, metadata or {}, float(distance))
                for text, metadata, distance in zip(result["documents"][0],
                                                     result["metadatas"][0], result["distances"][0])]
