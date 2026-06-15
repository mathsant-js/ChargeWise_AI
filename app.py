from chatbot import GoodWeChatbot

bot = GoodWeChatbot()

print("=" * 60)
print("GoodWe EV ChargeOps Assistant")
print("=" * 60)

while True:

    pergunta = input("\nVocê: ")

    if pergunta.lower() in [
        "sair",
        "exit",
        "quit"
    ]:
        break

    resposta = bot.responder(pergunta)

    print("\nAssistente:")
    print(resposta)