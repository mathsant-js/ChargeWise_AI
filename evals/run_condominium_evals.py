import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.chain.builder import DeterministicChatModel, parser  # noqa: E402
from src.chatbot import GoodWeChatbot  # noqa: E402
from src.config import (  # noqa: E402
    MAX_OUTPUT_TOKENS,
    MESSAGE_TOKEN_LIMIT,
    MODELO_IA,
    OLLAMA_API_KEY,
    OLLAMA_HOST,
    TEMPERATURE,
    TOP_P,
)


DATASET_PATH = ROOT / "evals" / "condominium_eval_dataset.json"
KNOWLEDGE_PATH = ROOT / "data" / "conhecimento_condominio_v2.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return completed.stdout.strip() or "unknown"


def _working_tree_dirty() -> bool:
    completed = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True, capture_output=True, check=False
    )
    return bool(completed.stdout.strip())


def _create_model(mode: str) -> BaseChatModel:
    if mode == "offline":
        return DeterministicChatModel()
    if not OLLAMA_API_KEY:
        raise RuntimeError("Modo real exige OLLAMA_API_KEY; nenhum resultado foi sobrescrito.")
    return ChatOllama(
        model=MODELO_IA,
        base_url=OLLAMA_HOST,
        client_kwargs={"headers": {"Authorization": f"Bearer {OLLAMA_API_KEY}"}},
        temperature=TEMPERATURE,
        top_p=TOP_P,
        num_predict=MAX_OUTPUT_TOKENS,
    )


def main() -> None:
    cli = argparse.ArgumentParser(description="Avalia o contexto condominial sem alterar o baseline canônico.")
    cli.add_argument("--mode", choices=("offline", "real"), default="offline")
    cli.add_argument("--prompt-version", choices=("v3", "v4"), default="v4")
    cli.add_argument("--overwrite", action="store_true")
    args = cli.parse_args()
    suffix = "" if args.prompt_version == "v4" else f"_{args.prompt_version}"
    result_path = ROOT / "evals" / f"condominium{suffix}_results.json"
    if result_path.exists() and not args.overwrite:
        raise FileExistsError(f"{result_path.name} já existe; use --overwrite para substituir.")

    cases = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    chatbot = GoodWeChatbot(
        model=_create_model(args.mode),
        prompt_version=args.prompt_version,
    )
    results = []
    started_run = time.perf_counter()
    for case in cases:
        started = time.perf_counter()
        output = chatbot.responder_estruturado(case["input"], case["session_id"])
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        diagnostics = chatbot.chain.turn_diagnostics(case["session_id"])
        intent_correct = output.get("intencao") == case["expected_intent"]
        text_correct = case["expected_text"].casefold() in str(output.get("resposta", "")).casefold()
        schema_valid = chatbot.chain.structured_output_valid(case["session_id"])
        results.append(
            {
                "id": case["id"],
                "passed": intent_correct and text_correct and schema_valid,
                "intent_correct": intent_correct,
                "text_correct": text_correct,
                "schema_valid": schema_valid,
                "latency_ms": latency_ms,
                "tokens": {
                    "input": diagnostics.get("estimated_input_tokens", 0),
                    "history": diagnostics.get("estimated_history_tokens", 0),
                    "output": diagnostics.get("estimated_output_tokens", 0),
                },
                "output": output,
                "failure": None if intent_correct and text_correct and schema_valid else "Saída diferente do esperado.",
            }
        )

    passed_count = sum(result["passed"] for result in results)
    prompt_path = ROOT / "prompts" / f"system_prompt_{args.prompt_version}.md"
    full_context = chatbot.chain.system_prompt + "\n\n" + parser.get_format_instructions()
    if chatbot.chain.condominium_context is not None:
        full_context += "\n\n" + chatbot.chain.condominium_context
    implementation_paths = (
        ROOT / "src" / "chain" / "builder.py",
        ROOT / "src" / "chatbot.py",
        ROOT / "src" / "guardrails" / "scope_validator.py",
        ROOT / "src" / "knowledge.py",
    )
    implementation_digest = hashlib.sha256()
    for path in implementation_paths:
        implementation_digest.update(path.read_bytes())
    input_tokens = sum(result["tokens"]["input"] for result in results)
    output_tokens = sum(result["tokens"]["output"] for result in results)
    report = {
        "report_schema_version": "2.0",
        "run": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "git_sha": _git_sha(),
            "working_tree_dirty": _working_tree_dirty(),
            "implementation_sha256": implementation_digest.hexdigest(),
            "mode": args.mode,
            "technical_mock_only": args.mode == "offline",
            "provider": "local-deterministic" if args.mode == "offline" else "ollama",
            "model": "chargewise-deterministic" if args.mode == "offline" else MODELO_IA,
            "prompt_version": args.prompt_version,
            "prompt_sha256": _sha256(prompt_path),
            "full_context_sha256": hashlib.sha256(full_context.encode()).hexdigest(),
            "knowledge_enabled": args.prompt_version == "v4",
            "knowledge_source": "data/conhecimento_condominio_v2.md" if args.prompt_version == "v4" else None,
            "knowledge_sha256": _sha256(KNOWLEDGE_PATH) if args.prompt_version == "v4" else None,
            "dataset": "evals/condominium_eval_dataset.json",
            "dataset_sha256": _sha256(DATASET_PATH),
            "parameters": {
                "temperature": TEMPERATURE,
                "top_p": TOP_P,
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "message_token_limit": MESSAGE_TOKEN_LIMIT,
            },
        },
        "summary": {
            "cases": len(results),
            "passed": passed_count,
            "success_rate": round(passed_count / len(results), 4),
            "tokens_input_total": input_tokens,
            "tokens_output_total": output_tokens,
            "latency_total_ms": round((time.perf_counter() - started_run) * 1000, 2),
            "latency_average_ms": round(sum(result["latency_ms"] for result in results) / len(results), 2),
        },
        "results": results,
    }
    result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.prompt_version}: {passed_count}/{len(results)} casos em {args.mode}")
    if args.prompt_version == "v4" and passed_count != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
