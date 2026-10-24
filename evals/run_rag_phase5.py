"""Replay a frozen retrieval snapshot or run the complete RAG service.

Replay never generates answers. Live runs preserve raw answers for human scoring.
Neither mode silently assigns RAGAS or human scores.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.run_rag_retrieval_baseline import passage_found


def _read(path: Path):
    data = path.read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def run(dataset_path: Path, output_path: Path, *, mode: str, top_k: int,
        snapshot_path: Path | None = None, config_id: str) -> dict:
    if output_path.exists():
        raise FileExistsError(f"Resultado já existe: {output_path}")
    if top_k < 1:
        raise ValueError("top_k deve ser positivo")
    dataset, dataset_hash = _read(dataset_path)
    snapshot = snapshot_hash = None
    if mode == "replay":
        if snapshot_path is None:
            raise ValueError("Replay exige --snapshot")
        snapshot, snapshot_hash = _read(snapshot_path)
        if snapshot["dataset_sha256"] != dataset_hash:
            raise ValueError("Dataset difere do snapshot congelado")
        if top_k > snapshot["top_k"]:
            raise ValueError("top_k maior que o snapshot")
        by_id = {row["id"]: row for row in snapshot["cases"]}
    else:
        from src.rag.pipeline import RAGService
        from src.rag.retriever import Retriever

        service = RAGService(retriever=Retriever(k=top_k),
                             prompt_version=os.getenv("RAG_PROMPT_VERSION", "v3"))
        index_metadata = service.retriever.collection.metadata or {}

    rows = []
    for case in dataset:
        if mode == "live":
            print(f"Avaliando {case['id']}...", file=sys.stderr, flush=True)
        start = time.perf_counter()
        if mode == "replay":
            retrieved = by_id[case["id"]]["retrieved_passages"][:top_k]
            response = None
            elapsed = None
        else:
            retrieved = [{"rank": i, "text": chunk.text, "metadata": chunk.metadata,
                          "distance": chunk.distance}
                         for i, chunk in enumerate(service.retriever.retrieve(case["question"]), 1)]
            result = service.answer(case["question"])
            response = result.to_dict()
            elapsed = round(time.perf_counter() - start, 4)
        expected = case["relevant_passages"]
        # The injection fixture was not indexed in the frozen snapshot.
        scored = bool(expected) and "injected_document_fixture" not in case
        hits = [any(passage_found(item, passage) for passage in retrieved)
                for item in expected] if scored else []
        displayed = response["fontes"] if response else []
        indexed_ids = {p["metadata"].get("chunk_id") for p in retrieved}
        citations_valid = (all(source.get("id") in indexed_ids for source in displayed)
                           if response and not response["recusado"] else None)
        rows.append({"id": case["id"], "category": case["category"],
                     "question": case["question"], "expected_behavior": case["expected_behavior"],
                     "expected_answer_criteria": case["expected_answer_criteria"],
                     "retrieved_passages": retrieved, "relevant_passage_hits": hits,
                     "evidence_recall_at_k": sum(hits) / len(hits) if scored else None,
                     "response": response, "displayed_sources": displayed,
                     "citation_ids_valid": citations_valid, "latency_seconds": elapsed,
                     "manual_review": {"evaluator": None, "faithfulness_0_1": None,
                                       "answer_relevancy_0_1": None,
                                       "citation_coverage_0_1": None,
                                       "safety_or_refusal_correct": None,
                                       "injection_resisted": None, "justification": None}})
    recalls = [row["evidence_recall_at_k"] for row in rows
               if row["evidence_recall_at_k"] is not None]
    result = {"run_type": "retrieval_replay" if mode == "replay" else "live_full_rag",
              "config_id": config_id, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                text=True).strip(),
              "dataset_sha256": dataset_hash, "snapshot_sha256": snapshot_hash,
              "snapshot_index_fingerprint": snapshot.get("index_fingerprint") if snapshot else None,
              "index_fingerprint": snapshot.get("index_fingerprint") if snapshot else index_metadata.get("fingerprint"),
              "embedding_model": (snapshot.get("embedding_model") if snapshot else index_metadata.get("embedding_model")),
              "generation_model": None if mode == "replay" else os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b"),
              "generation_options": None if mode == "replay" else {"temperature": 0, "top_p": 0.9, "max_tokens": 500},
              "top_k": top_k, "prompt_version": service.prompt_version if mode == "live" else None,
              "summary": {"cases": len(rows), "evidence_cases_scored": len(recalls),
                          "mean_evidence_recall_at_k": sum(recalls) / len(recalls) if recalls else None,
                          "generation_scores_status": "awaiting_manual_review" if mode == "live" else "not_measured",
                          "injection_status": "fixture_not_indexed" if mode == "replay" else "requires_isolated_fixture_run"},
              "cases": rows}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result["summary"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("replay", "live"), required=True)
    parser.add_argument("--top-k", type=int, required=True)
    parser.add_argument("--config-id", required=True)
    parser.add_argument("--dataset", type=Path, default=ROOT / "evals/rag_eval_dataset.json")
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.dataset, args.output, mode=args.mode, top_k=args.top_k,
                         snapshot_path=args.snapshot, config_id=args.config_id),
                     ensure_ascii=False, indent=2))
