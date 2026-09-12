import inspect
import json
import unittest
from typing import ClassVar

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.runnables.history import RunnableWithMessageHistory

from src.chain import builder
from src.chatbot import GoodWeChatbot
from src.guardrails.moderation import ModerationContext


def valid_response(answer="Resposta de teste.", intent="status_carregador"):
    return json.dumps(
        {"intencao": intent, "resposta": answer, "confianca": 0.9},
        ensure_ascii=False,
    )


class RecordingFakeChatModel(FakeListChatModel):
    recorded_calls: ClassVar[list] = []

    def invoke(self, input, config=None, **kwargs):
        messages = input.to_messages() if hasattr(input, "to_messages") else input
        self.recorded_calls.append(list(messages))
        return super().invoke(input, config=config, **kwargs)

    @classmethod
    def reset_calls(cls):
        cls.recorded_calls = []


def build_with_fake(fake, history_limit=None):
    """Adapt to the final factory while keeping injection a tested contract."""
    factory = builder.create_chain_wrapper
    parameters = inspect.signature(factory).parameters
    kwargs = {}
    for name in ("model", "llm", "chat_model"):
        if name in parameters:
            kwargs[name] = fake
            break
    else:
        raise AssertionError("create_chain_wrapper deve aceitar um modelo injetável")

    if history_limit is not None:
        for name in ("history_limit", "max_history_messages", "max_messages"):
            if name in parameters:
                kwargs[name] = history_limit
                break
        else:
            raise AssertionError("o builder deve expor um limite de histórico configurável")
    return factory(**kwargs)


def invoke(chain, text, thread_id):
    """Support wrapper-style and Runnable-style final APIs."""
    parameters = inspect.signature(chain.invoke).parameters
    if "thread_id" in parameters:
        return chain.invoke(text, thread_id=thread_id)
    if "session_id" in parameters:
        return chain.invoke(text, session_id=thread_id)
    payloads = ({"input": text}, {"messages": [("user", text)]})
    config = {"configurable": {"thread_id": thread_id}}
    errors = []
    for payload in payloads:
        try:
            return chain.invoke(payload, config=config)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(exc)
    raise AssertionError(f"API de invoke incompatível com thread_id: {errors[-1]}")


class TestStructuredParser(unittest.TestCase):
    class Message:
        def __init__(self, content):
            self.content = content

    def test_valid_json_is_parsed(self):
        raw = valid_response("Potência nominal informada: 22 kW.", "potencia")
        parsed = builder.robust_parse_and_moderate(self.Message(raw))
        self.assertEqual(parsed["intencao"], "potencia")
        self.assertEqual(parsed["confianca"], 0.9)

    def test_invalid_json_uses_safe_fallback(self):
        parsed = builder.robust_parse_and_moderate(self.Message('{"potencia_kw": -1}'))
        self.assertEqual(parsed["intencao"], "fora_do_escopo")
        self.assertEqual(parsed["confianca"], 0.0)
        self.assertFalse(parsed.schema_valid)

    def test_markdown_fence_is_rejected(self):
        parsed = builder.robust_parse_and_moderate(
            self.Message(f"```json\n{valid_response()}\n```")
        )

        self.assertFalse(parsed.schema_valid)
        self.assertEqual(parsed["intencao"], "fora_do_escopo")

    def test_extra_fields_are_rejected(self):
        raw = json.dumps(
            {
                "intencao": "potencia",
                "resposta": "Resposta válida.",
                "confianca": 0.8,
                "campo_nao_autorizado": "não deve passar",
            }
        )

        parsed = builder.robust_parse_and_moderate(self.Message(raw))

        self.assertFalse(parsed.schema_valid)
        self.assertNotIn("campo_nao_autorizado", parsed)

    def test_incorrect_numeric_types_are_rejected(self):
        for field, value in (
            ("confianca", "0.8"),
            ("potencia_kw", "22"),
            ("valor_estimado", True),
        ):
            data = {
                "intencao": "faturamento" if field == "valor_estimado" else "potencia",
                "resposta": "Resposta válida.",
                "confianca": 0.8,
                field: value,
            }
            parsed = builder.robust_parse_and_moderate(
                self.Message(json.dumps(data))
            )
            self.assertFalse(parsed.schema_valid, field)

    def test_provenance_is_supplied_outside_model_output(self):
        claim = json.dumps(
            {
                "intencao": "potencia",
                "resposta": "Segundo o manual oficial da GoodWe, a potência é 22 kW.",
                "potencia_kw": 22.0,
                "confianca": 0.8,
            },
            ensure_ascii=False,
        )

        without_source = builder.robust_parse_and_moderate(self.Message(claim))
        with_source = builder.robust_parse_and_moderate(
            self.Message(claim),
            ModerationContext(official_sources=("manual-goodwe-gw22.pdf",)),
        )

        self.assertEqual(without_source["intencao"], "fora_do_escopo")
        self.assertTrue(without_source.schema_valid)
        self.assertEqual(with_source["potencia_kw"], 22.0)
        self.assertTrue(with_source.schema_valid)

    def test_model_cannot_self_declare_provenance(self):
        data = json.loads(valid_response())
        data["fonte_oficial"] = "fonte inventada pelo modelo"

        parsed = builder.robust_parse_and_moderate(
            self.Message(json.dumps(data, ensure_ascii=False))
        )

        self.assertFalse(parsed.schema_valid)

    def test_domain_constraints_and_intent_coherence_are_enforced(self):
        invalid_outputs = (
            {
                "intencao": "potencia",
                "resposta": "Resposta válida.",
                "confianca": 1.1,
            },
            {
                "intencao": "potencia",
                "resposta": "Resposta válida.",
                "potencia_kw": -0.1,
                "confianca": 0.8,
            },
            {
                "intencao": "faturamento",
                "resposta": "Resposta válida.",
                "valor_estimado": -1.0,
                "confianca": 0.8,
            },
            {
                "intencao": "status_carregador",
                "resposta": "Resposta válida.",
                "estado_carregador": "desconhecido",
                "confianca": 0.8,
            },
            {
                "intencao": "potencia",
                "resposta": "   ",
                "confianca": 0.8,
            },
            {
                "intencao": "potencia",
                "resposta": "Resposta válida.",
                "estado_carregador": "online",
                "confianca": 0.8,
            },
            {
                "intencao": "status_carregador",
                "resposta": "Resposta válida.",
                "valor_estimado": 10.0,
                "confianca": 0.8,
            },
        )

        for output in invalid_outputs:
            parsed = builder.robust_parse_and_moderate(
                self.Message(json.dumps(output, ensure_ascii=False))
            )
            self.assertFalse(parsed.schema_valid, output)

    def test_non_finite_json_numbers_are_rejected(self):
        for field in ("confianca", "potencia_kw", "valor_estimado"):
            intent = "faturamento" if field == "valor_estimado" else "potencia"
            raw = (
                '{"intencao":"%s","resposta":"válida",'
                '"confianca":0.8,"%s":NaN}' % (intent, field)
            )
            parsed = builder.robust_parse_and_moderate(self.Message(raw))
            self.assertFalse(parsed.schema_valid, field)


class TestLCELMemoryContract(unittest.TestCase):
    def test_chain_uses_runnable_with_message_history(self):
        fake = RecordingFakeChatModel(responses=[valid_response()])
        chain = builder.create_chain(fake)

        self.assertIsInstance(chain.first, RunnableWithMessageHistory)

    def test_condominium_context_is_a_system_message_and_not_history(self):
        RecordingFakeChatModel.reset_calls()
        fake = RecordingFakeChatModel(responses=[valid_response()] * 2)
        chain = builder.create_chain_wrapper(
            model=fake,
            knowledge_content="Tarifa padrão: R$0,77/kWh",
        )

        invoke(chain, "Qual é a tarifa da recarga?", "knowledge-context")
        invoke(chain, "E quanto custa?", "knowledge-context")

        latest = fake.recorded_calls[-1]
        knowledge_messages = [
            message
            for message in latest
            if "<conhecimento_condominio" in str(message.content)
        ]
        self.assertEqual(len(knowledge_messages), 1)
        self.assertEqual(knowledge_messages[0].type, "system")
        self.assertIn("R$0,77/kWh", str(knowledge_messages[0].content))

    def test_prompt_v3_remains_without_condominium_context(self):
        RecordingFakeChatModel.reset_calls()
        fake = RecordingFakeChatModel(responses=[valid_response()])
        chain = builder.create_chain_wrapper(model=fake, prompt_version="v3")

        invoke(chain, "Qual é a tarifa da recarga?", "reproducible-v3")

        content = " ".join(str(message.content) for message in fake.recorded_calls[-1])
        self.assertNotIn("<conhecimento_condominio", content)
        self.assertIsNone(chain.condominium_context)

    def test_old_prompt_rejects_custom_condominium_context(self):
        fake = RecordingFakeChatModel(responses=[valid_response()])

        with self.assertRaises(ValueError):
            builder.create_chain_wrapper(
                model=fake,
                prompt_version="v3",
                knowledge_content="Tarifa padrão: R$0,77/kWh",
            )

    def test_knowledge_tokens_reduce_only_the_history_budget(self):
        fake = RecordingFakeChatModel(responses=[valid_response()] * 2)
        short = builder.create_chain_wrapper(model=fake, knowledge_content="Tarifa: 1")
        long = builder.create_chain_wrapper(
            model=fake,
            knowledge_content="Regra operacional de recarga. " * 100,
        )

        self.assertLess(long.memory_store.token_limit, short.memory_store.token_limit)

    def test_three_turns_are_available_to_the_model(self):
        RecordingFakeChatModel.reset_calls()
        fake = RecordingFakeChatModel(responses=[valid_response()] * 3)
        chain = build_with_fake(fake)
        for turn in (
            "primeiro turno sobre o carregador",
            "segundo turno sobre a recarga",
            "terceiro turno sobre o carregador",
        ):
            invoke(chain, turn, "memory-three-turns")

        content = " ".join(str(message.content) for message in fake.recorded_calls[-1])
        self.assertIn("primeiro turno", content)
        self.assertIn("segundo turno", content)
        self.assertIn("terceiro turno", content)

    def test_sessions_are_isolated(self):
        RecordingFakeChatModel.reset_calls()
        fake = RecordingFakeChatModel(responses=[valid_response()] * 3)
        chain = build_with_fake(fake)
        invoke(chain, "segredo da sessão alfa sobre o carregador", "alpha")
        invoke(chain, "conteúdo da sessão beta sobre a recarga", "beta")

        beta_messages = " ".join(str(message.content) for message in fake.recorded_calls[-1])
        self.assertIn("conteúdo da sessão beta", beta_messages)
        self.assertNotIn("segredo da sessão alfa", beta_messages)

    def test_history_limit_discards_oldest_turn(self):
        RecordingFakeChatModel.reset_calls()
        fake = RecordingFakeChatModel(responses=[valid_response()] * 4)
        chain = build_with_fake(fake)
        old_turn = "turno antigo do carregador " + ("conteúdo " * 5000)
        for turn in (
            old_turn,
            "turno intermediário da recarga",
            "turno recente do carregador",
        ):
            invoke(chain, turn, "bounded-history")

        latest = " ".join(str(message.content) for message in fake.recorded_calls[-1])
        self.assertIn("turno recente", latest)
        self.assertNotIn("turno antigo", latest)

    def test_default_model_recovers_first_turn_semantically(self):
        chatbot = GoodWeChatbot(model=builder.DeterministicChatModel())
        chatbot.responder("Meu carregador é o GW-123.")
        chatbot.responder("Ele está offline desde ontem.")

        answer = chatbot.responder(
            "Qual carregador mencionei e qual é o problema?"
        )

        self.assertIn("GW-123", answer)
        self.assertIn("offline desde ontem", answer)

    def test_default_model_resolves_pronoun_only_followups(self):
        chatbot = GoodWeChatbot(model=builder.DeterministicChatModel())
        chatbot.responder(
            "Meu carregador é o GW-123 e está offline desde ontem.",
            session_id="pronoun-status",
        )
        status = chatbot.responder(
            "E qual é o problema dele?",
            session_id="pronoun-status",
        )

        chatbot.responder(
            "Use tarifa de R$ 0,80/kWh para minha recarga de 10 kWh.",
            session_id="pronoun-cost",
        )
        cost = chatbot.responder("Quanto ela custa?", session_id="pronoun-cost")

        self.assertIn("offline", status)
        self.assertIn("8", cost)

    def test_default_model_uses_condominium_knowledge_without_hardcoded_values(self):
        knowledge = """# Condomínio de teste
Tarifa padrão: R$0,77/kWh
Quantidade de carregadores: 6
Potência média: 11 kW
Horário de pico: 17h às 20h
Reservas de até 3 horas por morador.
Prioridade para quem reservou primeiro.
"""
        chatbot = GoodWeChatbot(
            model=builder.DeterministicChatModel(),
            knowledge_content=knowledge,
        )
        cases = (
            ("Qual é a tarifa padrão da recarga?", "0.77"),
            ("Quanto custa consumir 10 kWh?", "7.70"),
            ("Quantos carregadores existem?", "6"),
            ("Qual é a potência média?", "11"),
            ("Qual é o horário de pico da recarga?", "17h às 20h"),
            ("Qual é a política de agendamento do carregador?", "3 horas"),
            ("Quem tem prioridade na reserva do carregador?", "reservou primeiro"),
        )

        for question, expected in cases:
            with self.subTest(question=question):
                answer = chatbot.responder(question, session_id=question)
                self.assertIn(expected, answer)

    def test_explicit_simulation_tariff_overrides_only_that_scenario(self):
        chatbot = GoodWeChatbot(model=builder.DeterministicChatModel())

        simulated = chatbot.responder(
            "Quanto custa 10 kWh com tarifa de R$ 0,80?",
            session_id="same-session",
        )
        standard = chatbot.responder(
            "Quanto custa consumir 10 kWh?",
            session_id="same-session",
        )

        self.assertIn("8.00", simulated)
        self.assertIn("9.20", standard)

    def test_default_and_custom_session_ids_are_isolated(self):
        RecordingFakeChatModel.reset_calls()
        fake = RecordingFakeChatModel(responses=[valid_response()] * 3)
        chain = build_with_fake(fake)
        chain.invoke("carregador exclusivo da sessão padrão")
        chain.invoke("carregador exclusivo da sessão customizada", session_id="custom")
        chain.invoke("consulta customizada", session_id="custom")

        latest = " ".join(str(message.content) for message in fake.recorded_calls[-1])
        self.assertIn("sessão customizada", latest)
        self.assertNotIn("sessão padrão", latest)

    def test_single_message_larger_than_budget_is_bounded(self):
        RecordingFakeChatModel.reset_calls()
        fake = RecordingFakeChatModel(responses=[valid_response()] * 2)
        chain = build_with_fake(fake)
        chain.invoke("carregador " * 10000, session_id="oversized")
        chain.invoke("status recente do carregador", session_id="oversized")

        latest = " ".join(str(message.content) for message in fake.recorded_calls[-1])
        self.assertIn("status recente do carregador", latest)
        self.assertLessEqual(
            chain.memory_metrics("oversized")["history_tokens"],
            chain.memory_store.token_limit,
        )


if __name__ == "__main__":
    unittest.main()
