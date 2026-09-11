import unittest
import json
from src.chain.builder import create_chain_wrapper
from src.schemas.consulta_recarga import ConsultaRecarga

class TestLCELChain(unittest.TestCase):
    def setUp(self):
        self.chain = create_chain_wrapper()

    def test_basic_intent_detection(self):
        # The mock client returns "Resposta simulada para: <input>"
        input_text = "Qual é a potência do carregador?"
        result = self.chain.invoke(input_text)
        # Should be parsed as fora_do_escopo (fallback) because mock returns plain text
        self.assertEqual(result["intencao"], "fora_do_escopo")
        self.assertIn(input_text, result["resposta"])  # raw text included
        self.assertGreaterEqual(result["confianca"], 0)

    def test_schema_validation_success(self):
        # Simulate a JSON response that matches the schema
        from src.chain.builder import robust_parse_and_moderate
        raw_json = json.dumps({
            "intencao": "potencia",
            "resposta": "O carregador tem 22 kW.",
            "potencia_kw": 22,
            "confianca": 0.9
        })
        # Mock the AIMessage object since robust_parse_and_moderate expects one
        class MockMessage:
            def __init__(self, content): self.content = content
        
        parsed = robust_parse_and_moderate(MockMessage(raw_json))
        self.assertEqual(parsed["intencao"], "potencia")
        self.assertEqual(parsed["potencia_kw"], 22)
        self.assertAlmostEqual(parsed["confianca"], 0.9)

    def test_invalid_json_fallback(self):
        from src.chain.builder import robust_parse_and_moderate
        # Missing required fields – should fallback to fora_do_escopo
        raw_bad = "{\"not_valid\": true}"
        # Mock the AIMessage object since robust_parse_and_moderate expects one
        class MockMessage:
            def __init__(self, content): self.content = content
        
        parsed = robust_parse_and_moderate(MockMessage(raw_bad))
        self.assertEqual(parsed["intencao"], "fora_do_escopo")
        self.assertIn("not_valid", parsed["resposta"])  # raw kept in resposta

if __name__ == "__main__":
    unittest.main()
