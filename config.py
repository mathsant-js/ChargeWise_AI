import os
from ollama import Client
from dotenv import load_dotenv

load_dotenv()

client = Client(
    host="https://ollama.com",
    headers={"Authorization": "Bearer " + os.environ.get("OLLAMA_API_KEY")},
)
api = os.environ.get("OLLAMA_API_KEY")

print("API KEY carregada: ", "OK" if api else "FALTANDO")


def llm(prompt, max_tokens=800, temperature=0.3):
    """Envia prompt ao gpt-oss:120b via Ollama Cloud e retorna texto."""
    try:
        return client.chat(
            model="gpt-oss:120b",
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": max_tokens, "temperature": temperature},
            stream=False,
        )["message"]["content"].strip()
    except Exception as e:
        return f"⚠️ Erro ao consultar IA: {e}"