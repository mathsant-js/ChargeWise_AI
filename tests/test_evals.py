import unittest

from evals.run_evals import comparison_for, evaluate_case, structured_output
from src.chain.builder import available_prompt_versions, create_chain_wrapper


class StructuredRunner:
    def __init__(self):
        self.sessions = []

    def invoke(self, text, session_id="default"):
        self.sessions.append(session_id)
        return {
            "intencao": "potencia",
            "resposta": "Potência consultada.",
            "potencia_kw": 7.4,
            "confianca": 0.95,
        }


class InvalidRunner:
    def invoke(self, text, session_id="default"):
        return "resposta sem JSON"


class SafeFallbackRunner:
    def invoke(self, text, session_id="default"):
        return {
            "intencao": "fora_do_escopo",
            "resposta": "Não posso atender a essa solicitação.",
            "confianca": 0.0,
        }

    def structured_output_valid(self, session_id):
        return False


class TestSprint3Evaluation(unittest.TestCase):
    def test_prompt_versions_are_discovered_and_selectable(self):
        self.assertEqual(list(available_prompt_versions()), ["v1", "v2", "v3"])
        runner = create_chain_wrapper(prompt_version="v1")
        self.assertEqual(runner.prompt_version, "v1")
        self.assertIn("SYSTEM PROMPT V1", runner.system_prompt)

    def test_invalid_prompt_version_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Versão de prompt inválida"):
            create_chain_wrapper(prompt_version="v99")

    def test_case_uses_structured_intent_session_and_metrics(self):
        runner = StructuredRunner()
        result = evaluate_case(
            {
                "session_id": "eval-thread",
                "input": "Qual a potência do carregador?",
                "expected_intent": "potencia",
                "category": "potencia",
            },
            runner,
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["output"]["potencia_kw"], 7.4)
        self.assertEqual(runner.sessions, ["eval-thread"])
        self.assertGreater(result["input_tokens"], 0)
        self.assertGreater(result["output_tokens"], 0)
        self.assertEqual(result["history_tokens"], 0)
        self.assertGreaterEqual(result["latency_ms"], 0)

    def test_plain_text_is_rejected(self):
        with self.assertRaises(TypeError):
            structured_output("potencia: resposta livre")

    def test_invalid_output_fails_case_without_aborting_evaluation(self):
        result = evaluate_case(
            {
                "session_id": "invalid-output",
                "input": "Qual a potência do carregador?",
                "expected_intent": "potencia",
                "category": "potencia",
            },
            InvalidRunner(),
        )

        self.assertFalse(result["passed"])
        self.assertFalse(result["schema_valid"])
        self.assertIsNone(result["output"])
        self.assertIn("saída estruturada", result["parser_error"])

    def test_safe_fallback_does_not_hide_parser_failure(self):
        result = evaluate_case(
            {
                "session_id": "fallback",
                "input": "Qual a potência do carregador?",
                "expected_intent": "fora_do_escopo",
                "category": "adversarial",
            },
            SafeFallbackRunner(),
        )

        self.assertFalse(result["schema_valid"])
        self.assertFalse(result["passed"])
        self.assertFalse(result["correct_refusal"])

    def test_comparison_records_regressions_against_v1(self):
        def report(quality, tokens, latency):
            return {"summary": {
                "quality_score": quality,
                "intent_accuracy": quality,
                "structured_accuracy": quality,
                "correct_refusal_rate": quality,
                "average_tokens_per_case": tokens,
                "average_latency_ms": latency,
            }}

        comparison = comparison_for({
            "v1": report(0.8, 100, 10),
            "v2": report(0.9, 120, 9),
            "v3": report(0.7, 90, 12),
        })
        self.assertEqual(comparison["v2"]["regressions_vs_v1"], ["average_tokens_per_case"])
        self.assertIn("quality_score", comparison["v3"]["regressions_vs_v1"])
        self.assertIn("average_latency_ms", comparison["v3"]["regressions_vs_v1"])


if __name__ == "__main__":
    unittest.main()
