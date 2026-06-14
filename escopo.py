PALAVRAS_CHAVE = [
    "condomínio",
    "morador",
    "síndico",
    "carregador",
    "recarga",
    "energia",
    "kwh",
    "veículo elétrico",
    "goodwe"
]


def dentro_do_escopo(texto):

    texto = texto.lower()

    return any(
        palavra in texto
        for palavra in PALAVRAS_CHAVE
    )