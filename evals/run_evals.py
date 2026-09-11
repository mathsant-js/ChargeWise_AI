import inspect
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.chain.builder import create_chain_wrapper
from src.config import MODELO_IA, USE_MOCK_MODEL
from src.schemas.consulta_recarga import ConsultaRecarga

try:
    from tiktoken import get_encoding
except ImportError:  # Evaluation remains usable in minimal CI environments.
    get_encoding = None


ENCODING = get_encoding("cl100k_base") if get_encoding else None


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
    output = structured_output(
        invoke_with_thread(runner, case["input"], case["session_id"])
    )
    elapsed = time.perf_counter() - started
    expected = case["expected_intent"]
    return {
        **case,
        "output": output,
        "passed": output["intencao"] == expected,
        "schema_valid": True,
        "correct_refusal": (
            output["intencao"] == "fora_do_escopo"
        ) == (expected == "fora_do_escopo"),
        "latency_ms": round(elapsed * 1000, 2),
        "input_tokens": count_tokens(case["input"]),
        "output_tokens": count_tokens(output),
    }


def main():
    directory = Path(__file__).resolve().parent
    cases = load_cases(directory / "eval_dataset.json")
    runner = create_chain_wrapper()
    results = [evaluate_case(case, runner) for case in cases]
    passed = sum(result["passed"] for result in results)
    report = {
        "summary": {
            "model": "deterministic-offline" if USE_MOCK_MODEL else MODELO_IA,
            "evaluation_mode": "offline" if USE_MOCK_MODEL else "ollama",
            "cases": len(results),
            "passed": passed,
            "pass_rate": round(passed / len(results), 4) if results else 0,
            "total_tokens": sum(r["input_tokens"] + r["output_tokens"] for r in results),
            "average_tokens_per_case": round(
                sum(r["input_tokens"] + r["output_tokens"] for r in results) / len(results), 2
            ) if results else 0,
            "structured_accuracy": round(
                sum(r["schema_valid"] for r in results) / len(results), 4
            ) if results else 0,
            "correct_refusal_rate": round(
                sum(r["correct_refusal"] for r in results) / len(results), 4
            ) if results else 0,
            "average_latency_ms": round(
                sum(r["latency_ms"] for r in results) / len(results), 2
            ) if results else 0,
        },
        "results": results,
    }
    output_path = directory / "sprint3_results.json"
    with open(output_path, "w", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(f"Sprint 03: {passed}/{len(results)} casos aprovados; resultado em {output_path.name}")


if __name__ == "__main__":
    main()
