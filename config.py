import os
from ollama import Client
from dotenv import load_dotenv

load_dotenv()

MODELO_IA = "gpt-oss:120b"

# Fallback to a mock client when OLLAMA_API_KEY is not set (e.g., during local evals)
api_key = os.environ.get("OLLAMA_API_KEY")
if api_key:
    client = Client(
        host="https://ollama.com",
        headers={"Authorization": "Bearer " + api_key},
    )
else:
    class MockClient:
        def chat(self, *_, **__):
            # Simple deterministic response: echo the last user message with a prefix
            # The caller passes messages list; last entry is user input
            user_msg = _[1] if len(_)>1 else None
            if isinstance(user_msg, list):
                # fallback: assume messages param named "messages" in kwargs
                msgs = __.get("messages", [])
                if msgs:
                    user_msg = msgs[-1]["content"]
            else:
                user_msg = __.get("messages", [])[-1]["content"] if __.get("messages") else ""
            return {"message": {"content": f"Resposta simulada para: {user_msg}"}}
    client = MockClient()
api = api_key