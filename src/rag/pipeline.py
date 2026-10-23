"""Serviço RAG independente de CLI e interface."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from src.guardrails.scope_validator import validate_scope
from src.rag.prompt_rag import PROMPT_VERSION, build_messages
from src.rag.retriever import RetrievedChunk, Retriever

NO_EVIDENCE = "Não encontrei evidência suficiente na base para responder com segurança."
_LIVE_OR_SPEC = re.compile(r"\b(?:agora|tempo real|neste momento|vaga\s*\d+|pot[eê]ncia nominal|modelo\s+GW-[\w-]+)\b", re.I)
_INJECTION = re.compile(r"(?:ignore|desconsidere|revele|mostre|imprima|system prompt|prompt de sistema|instru[cç][aã]o ao assistente|<\s*system)\b", re.I)


@dataclass(frozen=True)
class RAGResponse:
    answer: str
    refused: bool
    sources: list[dict] = field(default_factory=list)
    reason: str | None = None
    prompt_version: str = PROMPT_VERSION

    def to_dict(self) -> dict:
        return {"resposta": self.answer, "recusado": self.refused,
                "fontes": self.sources, "motivo": self.reason,
                "prompt_version": self.prompt_version}


def _model_select(messages: list[dict]) -> dict:
    from ollama import Client

    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    key = os.getenv("OLLAMA_API_KEY", "")
    client = Client(host=host, headers={"Authorization": f"Bearer {key}"} if key else None)
    response = client.chat(model=os.getenv("OLLAMA_MODEL", "gpt-oss:20b"), messages=messages,
                           format="json", options={"temperature": 0, "top_p": 0.9, "num_predict": 500})
    return json.loads(response.message.content)


class RAGService:
    def __init__(self, retriever: Retriever | None = None, selector=None,
                 max_distance: float = 1.0, prompt_version: str = PROMPT_VERSION):
        self.retriever = retriever or Retriever(k=int(os.getenv("RAG_TOP_K", "4")))
        self.selector = selector or _model_select
        self.max_distance = max_distance
        self.prompt_version = prompt_version

    def answer(self, question: str) -> RAGResponse:
        decision = validate_scope(question)
        if not decision.allowed:
            return RAGResponse(decision.refusal()["resposta"], True, reason=decision.reason,
                               prompt_version=self.prompt_version)
        if _LIVE_OR_SPEC.search(question):
            return RAGResponse(NO_EVIDENCE, True, reason="dado_especifico_ausente",
                               prompt_version=self.prompt_version)
        chunks = [chunk for chunk in self.retriever.retrieve(question)
                  if chunk.distance <= self.max_distance and all(
                      chunk.metadata.get(key) for key in ("chunk_id", "document", "section", "source"))]
        if not chunks:
            return RAGResponse(NO_EVIDENCE, True, reason="sem_trechos_relevantes",
                               prompt_version=self.prompt_version)
        selected = self.selector(build_messages(question, chunks, self.prompt_version))
        candidates = selected.get("evidence", []) if isinstance(selected, dict) else []
        by_id = {chunk.metadata["chunk_id"]: chunk for chunk in chunks}
        evidence: list[tuple[RetrievedChunk, str]] = []
        if not isinstance(candidates, list):
            candidates = []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            chunk = by_id.get(item.get("id"))
            quote = item.get("quote")
            if chunk and isinstance(quote, str) and quote.strip() and quote in chunk.text and not _INJECTION.search(quote):
                evidence.append((chunk, quote.strip()))
        if not evidence:
            return RAGResponse(NO_EVIDENCE, True, reason="evidencia_nao_validada",
                               prompt_version=self.prompt_version)
        sources = [{"id": chunk.metadata["chunk_id"], "document": chunk.metadata["document"],
                    "section": chunk.metadata["section"], "page": chunk.metadata.get("page") or None,
                    "source": chunk.metadata["source"], "authority": chunk.metadata.get("authority"),
                    "distance": chunk.distance} for chunk, _ in evidence]
        lines = [f"{quote} [{index}]" for index, (_, quote) in enumerate(evidence, 1)]
        if any(source["authority"] == "simulado" for source in sources):
            lines.insert(0, "No cenário condominial simulado documentado:")
        lines.extend(f"[{index}] {chunk.citation}" for index, (chunk, _) in enumerate(evidence, 1))
        return RAGResponse("\n".join(lines), False, sources=sources,
                           prompt_version=self.prompt_version)
