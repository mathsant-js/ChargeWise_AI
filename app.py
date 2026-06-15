from chatbot import GoodWeChatbot

bot = GoodWeChatbot()

print("=" * 60)
print("GoodWe EV ChargeOps Assistant")
print("=" * 60)

print("Olá! Sou seu assistente de gestão de recarga de veículos elétricos em condomínios.")
print("Posso ajudar com custos, tempo de recarga e uso compartilhado dos carregadores.")
print("Qual a sua dúvida?")


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