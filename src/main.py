# src/main.py
"""Entry point for the ChargeGrid‑Intelligence application.
It mirrors the behaviour of the original ``app.py`` but lives inside the
``src`` package, matching the architecture described in
``docs/arquitetura_plano_sprint3.md``.
"""

import os
# Disable LangChain tracing and telemetry before any other import
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_VERBOSE"] = "false"

import warnings
# Filter only DeprecationWarnings to avoid silencing critical errors
warnings.filterwarnings("ignore", category=DeprecationWarning)

import sys

# Adiciona a raiz do projeto ao sys.path para resolver importações absolutas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.chatbot import GoodWeChatbot

def run_interactive():
    """Inicia o chat interativo no terminal."""
    bot = GoodWeChatbot()
    print("=" * 60)
    print("GoodWe EV ChargeOps Assistant")
    print("=" * 60)
    print("Olá! Sou seu assistente de gestão de recarga de veículos elétricos em condomínios.")
    print("Posso ajudar com custos, tempo de recarga e uso compartilhado dos carregadores.")
    print("Qual a sua dúvida? (Digite 'sair' para encerrar)")
    
    try:
        while True:
            pergunta = input("\nVocê: ")
            if pergunta.lower() in ["sair", "exit", "quit"]:
                print("\nEncerrando assistente. Até logo!")
                break
            resposta = bot.responder(pergunta)
            print("\nAssistente:")
            print(resposta)
    except (EOFError, KeyboardInterrupt):
        print("\n\nSessão encerrada pelo usuário.")
        sys.exit(0)

def run_single_query(query: str):
    """Processa uma única pergunta e encerra a execução."""
    bot = GoodWeChatbot()
    resposta = bot.responder(query)
    print(f"\nPergunta: {query}")
    print(f"Assistente: {resposta}")

if __name__ == "__main__":
    # Modo Não-Interativo: Se houver argumentos, processa a pergunta e sai
    if len(sys.argv) > 1:
        pergunta_direta = " ".join(sys.argv[1:])
        run_single_query(pergunta_direta)
    else:
        # Modo Interativo: Inicia o loop de chat
        run_interactive()
