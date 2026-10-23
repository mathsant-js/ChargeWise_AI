"""Mede apenas recuperação do baseline RAG; geração pertence à fase 3."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rag.chunking import chunk_documents
from src.rag.embeddings import create_embeddings
from src.rag.loader import load_corpus
from src.rag.vector_store import DEFAULT_COLLECTION, DEFAULT_INDEX, corpus_fingerprint


def passage_found(expected: dict, retrieved: dict) -> bool:
    metadata = retrieved["metadata"]
    return (
        metadata.get("source") == expected["source"]
        and metadata.get("section", "").endswith(expected["section"])
        and expected["quote"].casefold() in retrieved["text"].casefold()
    )


def run(config_path: Path, output_path: Path, index_path: Path) -> dict:
    import chromadb

    config_bytes = config_path.read_bytes()
    config = json.loads(config_bytes)
    dataset_path = ROOT / config["dataset"]
    dataset_bytes = dataset_path.read_bytes()
    cases = json.loads(dataset_bytes)
    size = config["chunking"]["chunk_size_characters"]
    overlap = config["chunking"]["chunk_overlap_characters"]
    model = config["embedding_model"]
    embeddings = create_embeddings(model=model)
    collection = chromadb.PersistentClient(path=str(index_path.resolve())).get_collection(DEFAULT_COLLECTION)
    chunks = chunk_documents(load_corpus(), size, overlap)
    fingerprint = corpus_fingerprint(chunks, model, size, overlap)
    if collection.metadata.get("fingerprint") != fingerprint or collection.count() != len(chunks):
        raise ValueError("Índice desatualizado; execute python3 -m src.rag.vector_store index --reindex")

    rows = []
    for case in cases:
        query_vector = embeddings.embed_query(case["question"])
        result = collection.query(
            query_embeddings=[query_vector], n_results=config["retrieval"]["top_k"],
            include=["documents", "metadatas", "distances"],
        )
        passages = [{
            "rank": rank, "chunk_id": chunk_id, "text": text,
            "metadata": metadata, "distance": distance,
        } for rank, (chunk_id, text, metadata, distance) in enumerate(zip(
            result["ids"][0], result["documents"][0],
            result["metadatas"][0], result["distances"][0],
        ), start=1)]
        expected = case["relevant_passages"]
        hits = [any(passage_found(e, p) for p in passages) for e in expected]
        injection = "injected_document_fixture" in case
        rows.append({
            "id": case["id"], "category": case["category"], "question": case["question"],
            "expected_behavior": case["expected_behavior"],
            "retrieved_passages": passages,
            "relevant_passage_hits": hits,
            "evidence_recall_at_k": sum(hits) / len(hits) if hits and not injection else None,
            "evaluation_note": "Fixture de injeção ainda não inserida; teste adversarial pendente da fase 3"
            if injection else "Somente recuperação medida; resposta e segurança dependem da fase 3",
        })

    measured = [row["evidence_recall_at_k"] for row in rows if row["evidence_recall_at_k"] is not None]
    result = {
        "run_type": "retrieval_only_baseline", "config_id": config["id"],
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "index_fingerprint": fingerprint, "embedding_model": model,
        "chunk_size_characters": size, "chunk_overlap_characters": overlap,
        "top_k": config["retrieval"]["top_k"], "indexed_chunks": len(chunks),
        "summary": {
            "cases": len(rows), "evidence_cases_scored": len(measured),
            "mean_evidence_recall_at_k": sum(measured) / len(measured) if measured else None,
            "generation_metrics_status": "pending_phase_3",
            "prompt_injection_status": "fixture_not_indexed",
        },
        "cases": rows,
    }
    if output_path.exists():
        raise FileExistsError(f"Resultado já existe: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result["summary"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "evals/rag_baseline_config.json")
    parser.add_argument("--output", type=Path, default=ROOT / "evals/rag_retrieval_baseline_v0.json")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.output, args.index), ensure_ascii=False, indent=2))
