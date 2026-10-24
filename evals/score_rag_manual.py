"""Validate a human review and aggregate full RAG metrics without guessing scores."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SCORE_FIELDS = ("faithfulness_0_1", "answer_relevancy_0_1", "citation_coverage_0_1")


def score(raw_path: Path, review_path: Path, output_path: Path) -> dict:
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    if raw["run_type"] != "live_full_rag":
        raise ValueError("Somente respostas geradas podem receber notas de geração")
    cases = {case["id"]: case for case in raw["cases"]}
    if set(review) != set(cases):
        raise ValueError("A revisão deve cobrir exatamente os casos da execução")
    for case_id, marks in review.items():
        if not marks.get("evaluator") or not marks.get("justification"):
            raise ValueError(f"Revisão sem avaliador ou justificativa: {case_id}")
        for field in SCORE_FIELDS:
            value = marks.get(field)
            if value is not None and value not in (0, 0.5, 1):
                raise ValueError(f"Nota inválida: {case_id} {field}")
        cases[case_id]["manual_review"] = marks
    summary = dict(raw["summary"])
    for field in SCORE_FIELDS:
        values = [case["manual_review"][field] for case in cases.values()
                  if case["manual_review"].get(field) is not None]
        summary[f"mean_{field}"] = sum(values) / len(values) if values else None
        summary[f"n_{field}"] = len(values)
    for field in ("safety_or_refusal_correct", "injection_resisted"):
        values = [case["manual_review"][field] for case in cases.values()
                  if case["manual_review"].get(field) is not None]
        summary[f"mean_{field}"] = sum(values) / len(values) if values else None
        summary[f"n_{field}"] = len(values)
    summary["generation_scores_status"] = "manual_review_complete"
    raw["summary"] = summary
    if output_path.exists():
        raise FileExistsError(output_path)
    output_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("review", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(score(args.raw, args.review, args.output), ensure_ascii=False, indent=2))
