import tempfile
import unittest
from pathlib import Path

from evals.run_evals import (
    DATASET_PATH,
    _normalize,
    evaluate_case,
    load_cases,
    structured_output,
    summarize,
    write_report,
)
from evals.generate_comparison import comparison_markdown


class StubAdapter:
    name = "lcel"
    structured = True

    def __init__(self, responses=None, error=None):
        self.responses = responses or {}
        self.error = error

    def invoke(self, text, session_id):
        if self.error:
            raise self.error
        return self.responses.get(session_id, {
            "intencao": "potencia",
            "resposta": "A potência depende do modelo do carregador.",
            "confianca": 0.8,
        })

    def schema_valid(self, session_id):
        return True

    def diagnostics(self, session_id):
        return {
            "model_called": True,
            "estimated_input_tokens": 100,
            "estimated_history_tokens": 20,
            "estimated_output_tokens": 10,
            "model_latency_ms": 12.0,
            "provider_usage": {},
            "response_metadata": {},
        }


class TestBeforeAfterEvaluation(unittest.TestCase):
    def test_canonical_dataset_has_required_composition(self):
        cases = load_cases(DATASET_PATH)
        counts = {}
        for case in cases:
            counts[case["category"]] = counts.get(case["category"], 0) + 1

        self.assertEqual(len(cases), 35)
        self.assertEqual(counts, {
            "happy_path": 10,
            "memory_context": 5,
            "edge_case": 5,
            "out_of_scope": 5,
            "jailbreak": 5,
            "safety_advice": 5,
        })

    def test_structured_output_validates_schema(self):
        result = structured_output({
            "intencao": "potencia",
            "resposta": "Potência consultada.",
            "potencia_kw": 7.4,
            "confianca": 0.95,
        })
        self.assertEqual(result["potencia_kw"], 7.4)
        with self.assertRaises(TypeError):
            structured_output("resposta livre")

    def test_individual_failure_is_captured(self):
        case = load_cases()[0]
        result = evaluate_case(case, StubAdapter(error=RuntimeError("provider down")))
        self.assertFalse(result["schema_valid"])
        self.assertIn("provider down", result["error"])
        self.assertEqual(result["quality_0_10"], 0.0)

    def test_complete_turn_token_metrics_are_preserved(self):
        result = evaluate_case(load_cases()[2], StubAdapter())
        self.assertEqual(result["tokens"]["input"], 100)
        self.assertEqual(result["tokens"]["history_estimated"], 20)
        self.assertEqual(result["tokens"]["output"], 10)
        self.assertEqual(result["tokens"]["total"], 110)

    def test_normalization_canonicalizes_unicode_hyphens_and_spaces(self):
        self.assertEqual(_normalize("GW‑123"), _normalize("GW-123"))
        self.assertEqual(_normalize("R$ 8,00"), _normalize("R$ 8,00"))

    def test_memory_diagnostics_identify_guardrail_block(self):
        class BlockedAdapter(StubAdapter):
            def diagnostics(self, session_id):
                return {
                    "model_called": False,
                    "estimated_history_tokens": 0,
                    "provider_usage": {},
                    "response_metadata": {},
                }

        case = load_cases()[14]
        result = evaluate_case(case, BlockedAdapter(responses={
            case["session_id"]: {
                "intencao": "fora_do_escopo",
                "resposta": "Solicitação recusada.",
                "confianca": 0.0,
            }
        }))

        self.assertFalse(result["memory_model_reached"])
        self.assertFalse(result["memory_context_transmitted"])
        self.assertEqual(result["memory_failure_reason"], "guardrail_block")

    def test_summary_separates_happy_refusal_and_memory(self):
        adapter = StubAdapter()
        cases = [load_cases()[0], load_cases()[10], load_cases()[20]]
        results = [evaluate_case(case, adapter) for case in cases]
        summary = summarize(results)
        self.assertIn("happy_path_success_rate", summary)
        self.assertIn("refusal_rate", summary)
        self.assertIn("memory_success_rate", summary)
        self.assertIn("memory_model_reached_rate", summary)
        self.assertIn("memory_context_transmitted_rate", summary)
        self.assertGreaterEqual(summary["quality_0_10"], 0)
        self.assertLessEqual(summary["quality_0_10"], 10)

    def test_report_is_not_overwritten_without_explicit_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_report(path, {"new": True}, overwrite=False)
            write_report(path, {"new": True}, overwrite=True)
            self.assertIn('"new": true', path.read_text(encoding="utf-8"))

    def test_comparison_requires_the_same_dataset_and_mode(self):
        def report(implementation):
            return {
                "run": {
                    "dataset": "evals/eval_dataset.json",
                    "dataset_sha256": "same",
                    "mode": "real",
                    "model": "model",
                    "prompt": f"{implementation}.md",
                    "timestamp_utc": "2026-09-11T00:00:00+00:00",
                },
                "summary": {
                    "quality_0_10": 8.0,
                    "happy_path_success_rate": 1.0,
                    "structured_output_rate": 1.0,
                    "refusal_rate": 1.0,
                    "professional_referral_rate": 1.0,
                    "memory_success_rate": 0.5,
                    "tokens_average_per_model_call": 100.0,
                    "latency_model_calls": {"average_ms": 20.0},
                },
            }

        markdown = comparison_markdown(report("legacy"), report("lcel"))
        self.assertIn("Avaliação Antes/Depois", markdown)
        mismatched = report("lcel")
        mismatched["run"]["dataset_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "mesmo dataset"):
            comparison_markdown(report("legacy"), mismatched)


if __name__ == "__main__":
    unittest.main()
