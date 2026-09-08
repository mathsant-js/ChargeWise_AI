import os
from ollama import Client
from dotenv import load_dotenv

load_dotenv()

MODELO_IA = "gpt-oss:120b"

class MockClient:
    def chat(self, *_, **__):
        msgs = __.get("messages", [])
        if msgs:
            user_msg = msgs[-1]["content"]
        else:
            user_msg = _[1]["content"] if len(_)>1 else ""
        return {"message": {"content": f"Resposta simulada para: {user_msg}"}}

# Real execution: if OLLAMA_API_KEY is present, use the Ollama client; otherwise fall back to mock.
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
if OLLAMA_API_KEY:
    try:
        client = Client()
    except Exception:  # pragma: no cover
        client = MockClient()
else:
    client = MockClient()

api = None
