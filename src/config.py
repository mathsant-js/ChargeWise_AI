import os
from ollama import Client
from dotenv import load_dotenv

load_dotenv()

MODELO_IA = "gemma4:31b"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

# Define headers for cloud authentication
OLLAMA_HEADERS = {
    "Authorization": f"Bearer {OLLAMA_API_KEY}"
}

class MockClient:
    def chat(self, *_, **__):
        msgs = __.get("messages", [])
        if msgs:
            user_msg = msgs[-1]["content"]
        else:
            user_msg = _[1]["content"] if len(_)>1 else ""
        return {"message": {"content": f"Resposta simulada para: {user_msg}"}}

# For unit tests and CI we always use the deterministic mock client.
client = MockClient()
if OLLAMA_API_KEY:
    try:
        # Use the centralized OLLAMA_HOST and headers
        client = Client(host=OLLAMA_HOST, headers=OLLAMA_HEADERS)
    except Exception:  # pragma: no cover
        client = MockClient()
else:
    client = MockClient()

