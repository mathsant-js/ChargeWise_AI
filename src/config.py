import os
from ollama import Client
from dotenv import load_dotenv

load_dotenv()

MODELO_IA = "gpt-oss:120b"

# For unit tests and CI we always use the deterministic mock client.
# Uncomment the block below to use a real Ollama client if available.
client = MockClient()
# OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
# if OLLAMA_API_KEY:
#     try:
#         client = Client()
#     except Exception:  # pragma: no cover
#         client = MockClient()
# else:
#     client = MockClient()

api = None

class MockClient:
    def chat(self, *_, **__):
        msgs = __.get("messages", [])
        if msgs:
            user_msg = msgs[-1]["content"]
        else:
            user_msg = _[1]["content"] if len(_)>1 else ""
        return {"message": {"content": f"Resposta simulada para: {user_msg}"}}
