import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from langchain_ollama import ChatOllama

from evals.run_evals import LCELAdapter, _git_sha, _sha256, build_report, load_cases
from src.config import (
    MAX_OUTPUT_TOKENS,
    OLLAMA_API_KEY,
    OLLAMA_HOST,
    TEMPERATURE,
    TOP_P,
    client,
)


DEFAULT_MODELS = ("gpt-oss:120b", "gpt-oss:20b")
REQUESTED_COMPARATIVE = "qwen3:8b"
OUTPUT_PATH = ROOT / "evals" / "model_comparison_results.json"


def available_models() -> list[str]:
    response = client.list()
    return sorted(model.model for model in response.models if model.model)


def create_model(model_name: str) -> ChatOllama:
    return ChatOllama(
        model=model_name,
        base_url=OLLAMA_HOST,
        client_kwargs={"headers": {"Authorization": f"Bearer {OLLAMA_API_KEY}"}},
        temperature=TEMPERATURE,
        top_p=TOP_P,
        num_predict=MAX_OUTPUT_TOKENS,
    )


def _mean(values: list[float]) -> float:
    return round(statistics.mean(values), 4)


def aggregate(reports: list[dict[str, Any]]) -> dict[str, Any]:
    summaries = [report["summary"] for report in reports]
    scalar_metrics = (
        "quality_0_10",
        "happy_path_success_rate",
        "intent_accuracy",
        "structured_output_rate",
        "refusal_rate",
        "professional_referral_rate",
        "memory_success_rate",
        "tokens_total",
        "tokens_average_per_model_call",
    )
    result = {
        metric: _mean([float(summary[metric]) for summary in summaries])
        for metric in scalar_metrics
    }
    result["latency_model_average_ms"] = _mean([
        float(summary["latency_model_calls"]["average_ms"]) for summary in summaries
    ])
    result["latency_end_to_end_average_ms"] = _mean([
        float(summary["latency_end_to_end"]["average_ms"]) for summary in summaries
    ])
    result["failed_cases_total"] = sum(summary["failed_cases"] for summary in summaries)
    return result


def run_comparison(models: list[str], repetitions: int) -> dict[str, Any]:
    if not OLLAMA_API_KEY:
        raise RuntimeError("A comparação real exige OLLAMA_API_KEY.")
    endpoint_models = available_models()
    unavailable = [model for model in models if model not in endpoint_models]
    if unavailable:
        raise ValueError(f"Modelos indisponíveis no endpoint: {', '.join(unavailable)}")

    cases = load_cases()
    model_reports = {}
    for model_name in models:
        repetitions_data = []
        for repetition in range(1, repetitions + 1):
            adapter = LCELAdapter(create_model(model_name))
            report = build_report(adapter, cases, mode="real")
            report["run"]["model"] = model_name
            report["run"]["repetition"] = repetition
            repetitions_data.append(report)
            print(
                f"{model_name} repetição {repetition}/{repetitions}: "
                f"qualidade {report['summary']['quality_0_10']}/10"
            )
        model_reports[model_name] = {
            "aggregate": aggregate(repetitions_data),
            "repetitions": repetitions_data,
        }

    prompt_hashes = {
        report["run"]["prompt_sha256"]
        for data in model_reports.values()
        for report in data["repetitions"]
    }
    if len(prompt_hashes) != 1:
        raise RuntimeError("As execuções não usaram exatamente o mesmo prompt.")
    return {
        "report_schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha(),
        "provider": "ollama",
        "host": OLLAMA_HOST,
        "requested_models": ["gpt-oss:120b", REQUESTED_COMPARATIVE],
        "executed_models": models,
        "unavailable_requested_models": [
            model for model in (REQUESTED_COMPARATIVE,) if model not in endpoint_models
        ],
        "available_models_snapshot": endpoint_models,
        "parameters": {
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "repetitions": repetitions,
        },
        "dataset": "evals/eval_dataset.json",
        "dataset_sha256": _sha256(ROOT / "evals" / "eval_dataset.json"),
        "prompt": "prompts/system_prompt_v3.md + Pydantic format instructions",
        "prompt_sha256": prompt_hashes.pop(),
        "models": model_reports,
    }


def main() -> None:
    cli = argparse.ArgumentParser(description="Compare two real Ollama models with controlled inputs.")
    cli.add_argument("--models", nargs=2, default=list(DEFAULT_MODELS))
    cli.add_argument("--repetitions", type=int, default=2)
    cli.add_argument("--output", type=Path, default=OUTPUT_PATH)
    cli.add_argument("--overwrite", action="store_true")
    args = cli.parse_args()
    if args.repetitions < 2:
        cli.error("--repetitions deve ser pelo menos 2")
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(f"{args.output} já existe; use --overwrite para substituir.")
    report = run_comparison(args.models, args.repetitions)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Resultado salvo em {args.output}")


if __name__ == "__main__":
    main()
