from config import client, MODELO_IA
from escopo import dentro_do_escopo

def carregar_system_prompt():

    with open(
        "system_prompt.txt",
        "r",
        encoding="utf-8"
    ) as arquivo:

        return arquivo.read()


def carregar_conhecimento():

    try:
        with open(
            "data/conhecimento_condominio.txt",
            "r",
            encoding="utf-8"
        ) as arquivo:

            return arquivo.read()

    except FileNotFoundError:
        return ""


class GoodWeChatbot:

    def __init__(self):

        contexto_extra = carregar_conhecimento()

        self.historico = [
            {
                "role": "system",
                "content":
                    carregar_system_prompt()
                    + "\n\n"
                    + contexto_extra
            }
        ]

    def responder(
        self,
        pergunta,
        temperatura=0.3,
        max_tokens=800
    ):
        if not dentro_do_escopo(pergunta):

            return (
                "Essa pergunta está fora do escopo "
                "do assistente GoodWe EV ChargeOps. "
                "Posso auxiliar apenas com gestão "
                "de recarga de veículos elétricos "
                "em condomínios."
            )

        self.historico.append(
            {
                "role": "user",
                "content": pergunta
            }
        )

        resposta = client.chat(
            model=MODELO_IA,
            messages=self.historico,
            options={
                "temperature": temperatura,
                "num_predict": max_tokens
            },
            stream=False
        )

        texto = resposta["message"]["content"]

        self.historico.append(
            {
                "role": "assistant",
                "content": texto
            }
        )

        return texto