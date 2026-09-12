import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

from langchain_core.messages import BaseMessage, SystemMessage


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.chain.builder import DeterministicChatModel, create_chain_wrapper  # noqa: E402


RESULT_PATH = ROOT / "evals" / "memory_v3_v4_comparison.json"
ANCHOR = (
    "Meu carregador da garagem é o GW-MEM-731, está offline desde terça-feira "
    "e pertence ao apartamento 804."
)
PROBE = "Qual carregador mencionei e qual é o problema dele?"
EXPECTED_FACTS = ("gw-mem-731", "offline", "terça-feira", "804")
ANSWER_EXPECTED_FACTS = ("gw-mem-731", "offline")
DISTANCES = (4, 8, 12, 16, 24)
REGIMES = {
    "producao": {"v3": 4096, "v4": 4096},
    "memoria_equalizada": {"v3": 4096, "v4": 4427},
}


class RecordingDeterministicChatModel(DeterministicChatModel):
    recorded_calls: ClassVar[list[list[BaseMessage]]] = []

    def _generate(self, messages: list[BaseMessage], *args: Any, **kwargs: Any):
        self.recorded_calls.append(list(messages))
        return super()._generate(messages, *args, **kwargs)


def filler(turn: int) -> str:
    detail = " ".join(
        f"análise operacional {turn}-{index} sobre recarga, potência e disponibilidade"
        for index in range(10)
    )
    return f"Turno de acompanhamento {turn} do carregador: {detail}."


def _facts_found(text: str, expected: tuple[str, ...] = EXPECTED_FACTS) -> dict[str, bool]:
    normalized = text.casefold()
    return {fact: fact in normalized for fact in expected}


def run_case(version: str, history_limit: int, distance: int, case_id: str) -> dict[str, Any]:
    RecordingDeterministicChatModel.recorded_calls = []
    model = RecordingDeterministicChatModel()
    chain = create_chain_wrapper(
        model=model,
        prompt_version=version,
        history_limit=history_limit,
    )
    chain.invoke(ANCHOR, session_id=case_id)
    first_summary_turn = None
    for turn in range(1, distance + 1):
        chain.invoke(filler(turn), session_id=case_id)
        if first_summary_turn is None and chain.memory_metrics(case_id)["has_summary"]:
            first_summary_turn = turn

    before_probe = chain.memory_metrics(case_id)
    started = time.perf_counter()
    output = chain.invoke(PROBE, session_id=case_id)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    transmitted = " ".join(
        str(message.content) for message in RecordingDeterministicChatModel.recorded_calls[-1]
    )
    answer = str(output.get("resposta", ""))
    transmitted_facts = _facts_found(transmitted)
    recalled_facts = _facts_found(answer, ANSWER_EXPECTED_FACTS)
    history = chain.memory_store.get_session_history(case_id).messages
    summary = str(history[0].content) if history and isinstance(history[0], SystemMessage) else ""
    diagnostics = chain.turn_diagnostics(case_id)
    return {
        "distance": distance,
        "history_limit": history_limit,
        "effective_memory_budget": chain.memory_store.token_limit,
        "summary_token_limit": chain.memory_store.summary_token_limit,
        "first_summary_after_filler": first_summary_turn,
        "before_probe": before_probe,
        "after_probe": chain.memory_metrics(case_id),
        "anchor_in_summary": "gw-mem-731" in summary.casefold(),
        "transmitted_facts": transmitted_facts,
        "transmission_recall": round(sum(transmitted_facts.values()) / len(EXPECTED_FACTS), 4),
        "recalled_facts": recalled_facts,
        "answer_recall": round(sum(recalled_facts.values()) / len(ANSWER_EXPECTED_FACTS), 4),
        "model_called": diagnostics.get("model_called", False),
        "estimated_input_tokens": diagnostics.get("estimated_input_tokens", 0),
        "estimated_history_tokens": diagnostics.get("estimated_history_tokens", 0),
        "schema_valid": chain.structured_output_valid(case_id),
        "latency_ms": latency_ms,
        "answer": answer,
    }


def summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "cases": len(cases),
        "transmission_recall_average": round(
            sum(case["transmission_recall"] for case in cases) / len(cases), 4
        ),
        "answer_recall_average": round(
            sum(case["answer_recall"] for case in cases) / len(cases), 4
        ),
        "schema_valid_rate": round(
            sum(case["schema_valid"] for case in cases) / len(cases), 4
        ),
        "first_anchor_loss_distance": next(
            (case["distance"] for case in cases if case["transmission_recall"] < 1), None
        ),
        "latency_average_ms": round(
            sum(case["latency_ms"] for case in cases) / len(cases), 2
        ),
    }


def main() -> None:
    conversation_hash = hashlib.sha256(
        json.dumps(
            {"anchor": ANCHOR, "probe": PROBE, "fillers": [filler(i) for i in range(1, 25)]},
            ensure_ascii=False,
            sort_keys=True,
        ).encode()
    ).hexdigest()
    comparisons: dict[str, Any] = {}
    for regime, limits in REGIMES.items():
        comparisons[regime] = {}
        for version in ("v3", "v4"):
            cases = [
                run_case(version, limits[version], distance, f"{regime}-{version}-{distance}")
                for distance in DISTANCES
            ]
            comparisons[regime][version] = {"summary": summarize(cases), "cases": cases}

    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "offline-deterministic",
        "conversation_sha256": conversation_hash,
        "same_conversations": True,
        "expected_facts": list(EXPECTED_FACTS),
        "answer_expected_facts": list(ANSWER_EXPECTED_FACTS),
        "distances": list(DISTANCES),
        "comparisons": comparisons,
    }
    RESULT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for regime, versions in comparisons.items():
        for version, result in versions.items():
            summary = result["summary"]
            print(
                f"{regime} {version}: transmissão={summary['transmission_recall_average']:.0%}, "
                f"resposta={summary['answer_recall_average']:.0%}, "
                f"primeira perda={summary['first_anchor_loss_distance']}"
            )


if __name__ == "__main__":
    main()
