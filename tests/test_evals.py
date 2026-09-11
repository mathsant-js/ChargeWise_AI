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
        self.assertGreaterEqual(result["latency_ms"], 0)

    def test_plain_text_is_rejected(self):
        with self.assertRaises(TypeError):
            structured_output("potencia: resposta livre")


if __name__ == "__main__":
    unittest.main()
