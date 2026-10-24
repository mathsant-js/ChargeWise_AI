"""Indexação explícita e inspeção de uma coleção Chroma persistente."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from src.rag.chunking import chunk_documents
from src.rag.embeddings import create_embeddings
from src.rag.loader import DEFAULT_MANIFEST, load_corpus

DEFAULT_INDEX = Path(__file__).resolve().parents[2] / "data/chroma"
DEFAULT_COLLECTION = "chargewise_knowledge"


def corpus_fingerprint(chunks, model: str, chunk_size: int, chunk_overlap: int) -> str:
    # Inclui exatamente os metadados gravados: correções de fonte/seção também
    # invalidam o índice, mesmo quando o texto do chunk permanece igual.
    payload = [(d.metadata["chunk_id"], d.page_content, _metadata(d.metadata)) for d in chunks]
    return hashlib.sha256(json.dumps(
        [model, chunk_size, chunk_overlap, payload], ensure_ascii=False, sort_keys=True
    ).encode()).hexdigest()


def _metadata(metadata: dict) -> dict:
    # Chroma aceita escalares, mas não valores nulos.
    values = {key: value for key, value in metadata.items() if isinstance(value, (str, int, float, bool))}
    values["page"] = metadata.get("page") or 0  # 0 = documento sem paginação (Markdown).
    return values


def index_corpus(manifest_path=DEFAULT_MANIFEST, persist_directory=DEFAULT_INDEX,
                 collection_name=DEFAULT_COLLECTION, reindex=False, embeddings=None,
                 chunk_size=900, chunk_overlap=135):
    import chromadb

    chunks = chunk_documents(load_corpus(manifest_path), chunk_size, chunk_overlap)
    if not chunks:
        raise ValueError("Corpus vazio: nenhum trecho para indexar")
    embeddings = embeddings or create_embeddings()
    model = getattr(embeddings, "model", "custom")
    fingerprint = corpus_fingerprint(chunks, model, chunk_size, chunk_overlap)
    client = chromadb.PersistentClient(path=str(Path(persist_directory).resolve()))
    existing = None
    try:
        existing = client.get_collection(collection_name)
    except (ValueError, chromadb.errors.NotFoundError):
        pass
    if existing is not None:
        current = existing.metadata or {}
        if not reindex and current.get("fingerprint") == fingerprint and existing.count() == len(chunks):
            return {"status": "unchanged", "chunks": len(chunks), "fingerprint": fingerprint}
        if not reindex:
            raise ValueError("Índice diferente do corpus/configuração atual; execute com --reindex")

    # Gera embeddings antes de alterar a coleção existente.
    vectors = embeddings.embed_documents([d.page_content for d in chunks])
    if len(vectors) != len(chunks):
        raise ValueError("Ollama retornou uma quantidade inesperada de embeddings")
    if existing is not None:
        client.delete_collection(collection_name)
    collection = client.create_collection(collection_name, metadata={
        "fingerprint": fingerprint, "embedding_model": model,
        "chunk_size": chunk_size, "chunk_overlap": chunk_overlap,
    })
    for start in range(0, len(chunks), 100):
        batch = chunks[start:start + 100]
        collection.add(
            ids=[d.metadata["chunk_id"] for d in batch],
            documents=[d.page_content for d in batch],
            metadatas=[_metadata(d.metadata) for d in batch],
            embeddings=vectors[start:start + 100],
        )
    return {"status": "indexed", "chunks": collection.count(), "fingerprint": fingerprint}


def inspect_index(persist_directory=DEFAULT_INDEX, collection_name=DEFAULT_COLLECTION, limit=10):
    import chromadb

    collection = chromadb.PersistentClient(path=str(Path(persist_directory).resolve())).get_collection(collection_name)
    records = collection.get(limit=limit, include=["documents", "metadatas"])
    return {"count": collection.count(), "version": collection.metadata, "chunks": [
        {"id": id_, "text": text, "metadata": metadata}
        for id_, text, metadata in zip(records["ids"], records["documents"], records["metadatas"])
    ]}


def main():
    parser = argparse.ArgumentParser(description="Indexa ou inspeciona o corpus RAG")
    parser.add_argument("action", choices=["index", "inspect"])
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--persist-directory", default=os.getenv("CHROMA_PERSIST_DIR", str(DEFAULT_INDEX)))
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--reindex", action="store_true")
    parser.add_argument("--chunk-size", type=int, default=900)
    parser.add_argument("--chunk-overlap", type=int, default=135)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    if args.action == "index":
        result = index_corpus(args.manifest, args.persist_directory, args.collection,
                              args.reindex, chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap)
    else:
        result = inspect_index(args.persist_directory, args.collection, args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
