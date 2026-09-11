import os

from dotenv import load_dotenv
from ollama import Client

load_dotenv()

MODELO_IA = os.getenv("OLLAMA_MODEL", "gemma4:31b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "https://ollama.com")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.2"))
TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.9"))
MAX_OUTPUT_TOKENS = int(os.getenv("OLLAMA_MAX_OUTPUT_TOKENS", "500"))
MESSAGE_TOKEN_LIMIT = int(os.getenv("MESSAGE_TOKEN_LIMIT", "4096"))
USE_MOCK_MODEL = os.getenv("USE_MOCK_MODEL", "").lower() in {"1", "true", "yes"} or (
    not OLLAMA_API_KEY and OLLAMA_HOST.rstrip("/") == "https://ollama.com"
)

OLLAMA_HEADERS = (
    {"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else {}
)


class MockClient:
    def chat(self, *args: object, **kwargs: object) -> dict[str, dict[str, str]]:
        messages = kwargs.get("messages", [])
        if isinstance(messages, list) and messages:
            user_message = messages[-1]["content"]
        else:
            user_message = ""
        return {"message": {"content": f"Resposta simulada para: {user_message}"}}


client: Client | MockClient = MockClient()
if OLLAMA_API_KEY:
    try:
        client = Client(host=OLLAMA_HOST, headers=OLLAMA_HEADERS)
    except Exception:  # pragma: no cover
        client = MockClient()
