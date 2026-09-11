import inspect
import json
import unittest
from typing import ClassVar

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.runnables.history import RunnableWithMessageHistory

from src.chain import builder


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


class TestLCELMemoryContract(unittest.TestCase):
    def test_chain_uses_runnable_with_message_history(self):
        fake = RecordingFakeChatModel(responses=[valid_response()])
        chain = builder.create_chain(fake)

        self.assertIsInstance(chain.first, RunnableWithMessageHistory)

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


if __name__ == "__main__":
    unittest.main()
