import unittest

from evals.run_evals import evaluate_case, structured_output


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


if __name__ == "__main__":
    unittest.main()
