import argparse
import inspect
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chain.builder import available_prompt_versions, create_chain_wrapper, parser
from src.config import MODELO_IA, TEMPERATURE, TOP_P, USE_MOCK_MODEL
from src.guardrails.scope_validator import BlockCategory, refusal_for
from src.schemas.consulta_recarga import ConsultaRecarga

try:
    from tiktoken import get_encoding
except ImportError:  # Evaluation remains usable in minimal CI environments.
    get_encoding = None


ENCODING = get_encoding("cl100k_base") if get_encoding else None

REFUSAL_CATEGORIES = {
    "jailbreak": BlockCategory.JAILBREAK,
    "seguranca": BlockCategory.ELECTRICAL_SAFETY,
    "legal": BlockCategory.LEGAL,
    "financeiro": BlockCategory.FINANCIAL,
    "fraude": BlockCategory.FRAUD,
    "dominio": BlockCategory.OUT_OF_SCOPE,
}


def count_tokens(value):
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return len(ENCODING.encode(text)) if ENCODING else len(text.split())


def load_cases(path):
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def invoke_with_thread(runner, text, thread_id):
    parameters = inspect.signature(runner.invoke).parameters
    if "thread_id" in parameters:
        return runner.invoke(text, thread_id=thread_id)
    if "session_id" in parameters:
        return runner.invoke(text, session_id=thread_id)
    return runner.invoke(
        {"input": text}, config={"configurable": {"thread_id": thread_id}}
    )


def structured_output(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if isinstance(value, dict) and "output" in value:
        value = value["output"]
        if hasattr(value, "model_dump"):
            value = value.model_dump()
    if not isinstance(value, dict):
        raise TypeError("A avaliação Sprint 03 exige saída estruturada ConsultaRecarga")
    return ConsultaRecarga.model_validate(value).model_dump()


def evaluate_case(case, runner):
    started = time.perf_counter()
    expected = case["expected_intent"]
    error = None
    try:
        raw_output = invoke_with_thread(runner, case["input"], case["session_id"])
        output = structured_output(raw_output)
        schema_valid = (
            runner.structured_output_valid(case["session_id"])
            if hasattr(runner, "structured_output_valid")
            else True
        )
    except (TypeError, ValueError) as exc:
        output = None
        schema_valid = False
        error = str(exc)
    elapsed = time.perf_counter() - started
    memory_metrics = (
        runner.memory_metrics(case["session_id"])
        if hasattr(runner, "memory_metrics")
        else {}
    )
    expected_refusal = REFUSAL_CATEGORIES.get(case.get("category"))
    correct_refusal = False
    if schema_valid and output:
        if expected_refusal is not None:
            official = refusal_for(expected_refusal)
            correct_refusal = all(
                output.get(field) == official[field]
                for field in ("intencao", "resposta", "requer_profissional")
            )
        else:
            correct_refusal = output["intencao"] != "fora_do_escopo"
    prompt_tokens = count_tokens(runner.system_prompt) if hasattr(runner, "system_prompt") else 0
    return {
        **case,
        "output": output,
        "passed": bool(schema_valid and output and output["intencao"] == expected),
        "schema_valid": schema_valid,
        "parser_error": error,
        "correct_refusal": correct_refusal,
        "latency_ms": round(elapsed * 1000, 2),
        "prompt_tokens": prompt_tokens,
        "input_tokens": count_tokens(case["input"]),
        "output_tokens": count_tokens(output) if output is not None else 0,
        "history_tokens": memory_metrics.get("history_tokens", 0),
        "history_has_summary": memory_metrics.get("has_summary", False),
    }


def run_evaluation(cases, prompt_version):
    runner = create_chain_wrapper(prompt_version=prompt_version)
    results = [evaluate_case(case, runner) for case in cases]
    passed = sum(result["passed"] for result in results)
    memory_results = [result for result in results if result.get("category") == "memoria"]
    intent_accuracy = passed / len(results) if results else 0
    structured_accuracy = sum(r["schema_valid"] for r in results) / len(results) if results else 0
    refusal_accuracy = sum(r["correct_refusal"] for r in results) / len(results) if results else 0
    return {
        "summary": {
            "model": "deterministic-offline" if USE_MOCK_MODEL else MODELO_IA,
            "evaluation_mode": "offline" if USE_MOCK_MODEL else "ollama",
            "prompt_version": runner.prompt_version,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "cases": len(results),
            "passed": passed,
            "quality_score": round((intent_accuracy + structured_accuracy + refusal_accuracy) / 3, 4),
            "intent_accuracy": round(intent_accuracy, 4),
            "pass_rate": round(intent_accuracy, 4),
            "prompt_tokens": count_tokens(runner.system_prompt),
            "total_tokens": sum(r["prompt_tokens"] + r["input_tokens"] + r["output_tokens"] for r in results),
            "average_tokens_per_case": round(
                sum(r["prompt_tokens"] + r["input_tokens"] + r["output_tokens"] for r in results) / len(results), 2
            ) if results else 0,
            "structured_accuracy": round(structured_accuracy, 4),
            "correct_refusal_rate": round(refusal_accuracy, 4),
            "memory_cases": len(memory_results),
            "memory_success_rate": round(
                sum(result["passed"] for result in memory_results) / len(memory_results), 4
            ) if memory_results else 0,
            "average_latency_ms": round(
                sum(r["latency_ms"] for r in results) / len(results), 2
            ) if results else 0,
        },
        "results": results,
    }


def comparison_for(reports):
    baseline = reports["v1"]["summary"]
    metrics = (
        "quality_score", "intent_accuracy", "structured_accuracy",
        "correct_refusal_rate", "average_tokens_per_case", "average_latency_ms",
    )
    comparison = {}
    previous = None
    for version, report in reports.items():
        summary = report["summary"]
        deltas = {metric: round(summary[metric] - baseline[metric], 4) for metric in metrics}
        regressions = [
            metric for metric in metrics
            if (metric in {"average_tokens_per_case", "average_latency_ms"} and deltas[metric] > 0)
            or (metric not in {"average_tokens_per_case", "average_latency_ms"} and deltas[metric] < 0)
        ]
        entry = {"vs_v1": deltas, "regressions_vs_v1": regressions}
        if previous is not None:
            previous_summary = reports[previous]["summary"]
            previous_deltas = {
                metric: round(summary[metric] - previous_summary[metric], 4)
                for metric in metrics
            }
            entry["vs_previous"] = previous_deltas
            entry["regressions_vs_previous"] = [
                metric for metric in metrics
                if (metric in {"average_tokens_per_case", "average_latency_ms"} and previous_deltas[metric] > 0)
                or (metric not in {"average_tokens_per_case", "average_latency_ms"} and previous_deltas[metric] < 0)
            ]
        comparison[version] = entry
        previous = version
    return comparison


def main():
    cli = argparse.ArgumentParser(description="Compare prompt versions with a controlled dataset.")
    cli.add_argument(
        "--prompt-version",
        choices=["all", *available_prompt_versions()],
        default="all",
        help="Version to evaluate; defaults to every discovered version.",
    )
    args = cli.parse_args()
    directory = Path(__file__).resolve().parent
    cases = load_cases(directory / "eval_dataset.json")
    versions = list(available_prompt_versions()) if args.prompt_version == "all" else [args.prompt_version]
    reports = {version: run_evaluation(cases, version) for version in versions}
    payload = {
        "controlled_parameters": {
            "dataset": "eval_dataset.json",
            "model": "deterministic-offline" if USE_MOCK_MODEL else MODELO_IA,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
        },
        "versions": reports,
    }
    if "v1" in reports:
        payload["comparison"] = comparison_for(reports)
    output_path = directory / (
        "prompt_comparison_results.json" if args.prompt_version == "all"
        else f"prompt_{args.prompt_version}_results.json"
    )
    with open(output_path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
    summaries = ", ".join(
        f"{version}: {report['summary']['passed']}/{report['summary']['cases']}"
        for version, report in reports.items()
    )
    print(f"Prompts avaliados ({summaries}); resultado em {output_path.name}")


if __name__ == "__main__":
    main()
