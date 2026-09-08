# src/main.py
"""Entry point for the ChargeGrid‑Intelligence application.
It mirrors the behaviour of the original ``app.py`` but lives inside the
``src`` package, matching the architecture described in
``docs/arquitetura_plano_sprint3.md``.
"""

from src.chatbot import GoodWeChatbot

if __name__ == "__main__":
    bot = GoodWeChatbot()
    print("=" * 60)
    print("GoodWe EV ChargeOps Assistant")
    print("=" * 60)
    print("Olá! Sou seu assistente de gestão de recarga de veículos elétricos em condomínios.")
    print("Posso ajudar com custos, tempo de recarga e uso compartilhado dos carregadores.")
    print("Qual a sua dúvida?")
    while True:
        pergunta = input("\nVocê: ")
        if pergunta.lower() in ["sair", "exit", "quit"]:
            break
        resposta = bot.responder(pergunta)
        print("\nAssistente:")
        print(resposta)
