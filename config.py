import os
from ollama import Client
from dotenv import load_dotenv

load_dotenv()

MODELO_IA = "gpt-oss:120b"

# ALWAYS use a deterministic mock client for development and tests.
# This avoids external API calls and guarantees reproducible responses.
class MockClient:
    def chat(self, *_, **__):
        # The caller passes a list of messages; the last entry is the user input.
        # Retrieve the content of that last user message.
        msgs = __.get("messages", [])
        if msgs:
            user_msg = msgs[-1]["content"]
        else:
            # Fallback when messages are passed positionally (unlikely in our code)
            user_msg = _[1]["content"] if len(_)>1 else ""
        return {"message": {"content": f"Resposta simulada para: {user_msg}"}}

# If OLLAMA_API_KEY is present, instantiate a real Ollama client;
# otherwise fall back to the deterministic mock client.
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
if OLLAMA_API_KEY:
    try:
        client = Client()
    except Exception:  # pragma: no cover
        client = MockClient()
else:
    client = MockClient()

api = None