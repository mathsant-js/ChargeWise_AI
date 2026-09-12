import unittest

from langchain.memory import ConversationTokenBufferMemory
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.chain.memoria import SessionMemoryStore


class TestSessionMemoryStore(unittest.TestCase):
    def setUp(self):
        self.model = FakeListChatModel(responses=["ok"])

    def test_uses_conversation_token_buffer_memory(self):
        store = SessionMemoryStore(self.model, token_limit=256)

        self.assertIsInstance(
            store.get_memory("memory-contract"),
            ConversationTokenBufferMemory,
        )

    def test_sessions_are_isolated_and_can_be_cleared(self):
        store = SessionMemoryStore(self.model, token_limit=256)
        alpha = store.get_session_history("alpha")
        beta = store.get_session_history("beta")
        alpha.add_user_message("carregador alfa")
        beta.add_user_message("carregador beta")

        self.assertNotEqual(alpha.messages, beta.messages)
        store.clear("alpha")
        self.assertEqual(store.get_session_history("alpha").messages, [])
        self.assertEqual(beta.messages[0].content, "carregador beta")

    def test_old_turns_become_deterministic_summary(self):
        store = SessionMemoryStore(self.model, token_limit=150, summary_ratio=0.4)
        history = store.get_session_history("summary")
        history.add_messages(
            [
                HumanMessage(content="O carregador da garagem é o GW-22 com potência de 22 kW. " * 5),
                AIMessage(content="Registrei o carregador GW-22 da garagem."),
                HumanMessage(content="A tarifa informada é R$ 0,92 por kWh. " * 5),
                AIMessage(content="Registrei a tarifa de R$ 0,92 por kWh."),
                HumanMessage(content="Qual é o status dele agora?"),
                AIMessage(content="Preciso da telemetria para consultar o status."),
            ]
        )

        self.assertIsInstance(history.messages[0], SystemMessage)
        summary = str(history.messages[0].content)
        self.assertIn("Resumo determinístico", summary)
        self.assertTrue("GW-22" in summary or "R$ 0,92" in summary)
        self.assertLessEqual(store.metrics("summary")["history_tokens"], 150)

    def test_recent_messages_remain_as_complete_turns(self):
        store = SessionMemoryStore(self.model, token_limit=120, summary_ratio=0.3)
        history = store.get_session_history("turns")
        for index in range(5):
            history.add_messages(
                [
                    HumanMessage(content=f"Pergunta {index} sobre o carregador " * 3),
                    AIMessage(content=f"Resposta {index} sobre o carregador " * 3),
                ]
            )

        recent = history.messages[1:] if isinstance(history.messages[0], SystemMessage) else history.messages
        self.assertEqual(len(recent) % 2, 0)
        for index in range(0, len(recent), 2):
            self.assertIsInstance(recent[index], HumanMessage)
            self.assertIsInstance(recent[index + 1], AIMessage)

    def test_empty_session_id_is_rejected(self):
        store = SessionMemoryStore(self.model, token_limit=256)

        with self.assertRaisesRegex(ValueError, "session_id"):
            store.get_session_history("")


if __name__ == "__main__":
    unittest.main()
