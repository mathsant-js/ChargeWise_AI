# ChargeWise AI

Assistente Inteligente para Gestão de Recarga de Veículos Elétricos em Condomínios

<br>

# 👥 Integrantes

| Nomes Completos                   | RM's   |
|-----------------------------------|--------|
| Bernardo Zauza Amorim             | 568808 |
| Bruno Almeida de Oliveira         | 572648 |
| Gabriel Góes Nunes Pereira        | 571735 |
| Guilherme Vinciguerra Carvalho    | 571951 |
| Marcos Peterson Martins Pereira   | 573857 |
| Matheus Jorge Santana             | 574166 |

<br>

# 📖 Visão Geral

O ChargeWise AI é um chatbot especializado em gestão de recarga de veículos elétricos em condomínios residenciais.

A solução utiliza Inteligência Artificial Generativa para responder dúvidas relacionadas ao uso compartilhado de carregadores, custos de energia, tempo de recarga, regras de agendamento e informações operacionais do condomínio.

O sistema foi desenvolvido como uma prova de conceito acadêmica alinhada ao desafio GoodWe EV ChargeOps. A base condominial e o modo offline são simulações e não representam telemetria ou uma operação real da GoodWe.

<br>

# 🎯 Problema

O crescimento da adoção de veículos elétricos aumenta a demanda por pontos de recarga em condomínios residenciais.

Nesse cenário surgem desafios como:

* Compartilhamento de carregadores entre moradores
* Controle de horários de utilização
* Distribuição justa dos custos de energia
* Gestão de conflitos de agendamento
* Transparência no consumo energético
* Suporte operacional para síndicos e administradores

A ausência de mecanismos inteligentes para apoiar essas atividades pode gerar conflitos, ineficiência operacional e dificuldade de gerenciamento.

<br>

# 💡 Solução Proposta

O ChargeWise AI atua como um assistente conversacional especializado em gestão de recarga de veículos elétricos.

Entre suas capacidades estão:

* Cálculo de custos de recarga
* Estimativa de tempo de carregamento
* Consulta de regras operacionais
* Suporte ao uso compartilhado dos carregadores
* Resolução de conflitos de agendamento
* Respostas contextualizadas utilizando informações do condomínio

<br>

# 🏢 Justificativa do Contexto Condominial

O contexto de condomínios residenciais foi escolhido por representar um dos cenários mais aderentes ao desafio GoodWe EV ChargeOps.

Além da proximidade com o problema proposto, existem razões operacionais relevantes:

### Crescimento da infraestrutura residencial

A expansão do mercado de veículos elétricos tem impulsionado a instalação de carregadores em condomínios residenciais, tornando a gestão compartilhada da infraestrutura um desafio crescente.

### Perfil do cliente-alvo

Síndicos, administradoras condominiais e moradores representam um público diretamente impactado pela necessidade de organizar o uso dos carregadores, controlar custos e evitar conflitos operacionais.

### Escalabilidade operacional

Condomínios podem possuir múltiplos carregadores e dezenas de usuários compartilhando a mesma infraestrutura, criando um ambiente adequado para aplicação de soluções inteligentes de gestão energética.

### Alinhamento com o ecossistema GoodWe

A GoodWe atua em soluções de energia distribuída, armazenamento e carregamento de veículos elétricos. A gestão eficiente de recarga compartilhada é um cenário compatível com a evolução de plataformas como o EV ChargeOps.

<br>

# 🛠 Tecnologias Utilizadas

* Python 3.10+
* Ollama Python SDK
* Ollama Cloud API
* GPT-OSS 120B
* Python Dotenv

Bibliotecas principais:

```bash
ollama
python-dotenv
langchain
langchain-ollama
pydantic
tiktoken
```

<br>

# 🤖 Modelo e modos de execução

No modo real, o modelo padrão configurado em `src/config.py` é:

**gpt-oss:120b**

A chain instancia `ChatOllama` com `OLLAMA_HOST`, `OLLAMA_MODEL` e, quando presente, `OLLAMA_API_KEY`. O modelo pode ser alterado pela variável `OLLAMA_MODEL`.

Configuração principal:

Sem `OLLAMA_API_KEY` no host padrão, ou com `USE_MOCK_MODEL=true`, a aplicação usa `DeterministicChatModel`. Esse modo mock é um fallback local previsível para testes técnicos: não chama o modelo de linguagem, não mede a qualidade do `gpt-oss:120b` e não representa o resultado final da solução em modo real.

<br>


# 📊 Comparação Técnica de Modelos

O comparativo executado usou `gpt-oss:120b` e `gpt-oss:20b`; `qwen3:8b` não estava disponível no endpoint consultado. Método, resultados brutos, limitações e data da medição estão em `docs/relatorio_modelos.md` e `evals/model_comparison_results.json`. As conclusões se restringem a esse dataset e a essas execuções.

<br>

# 🧠 Técnicas de Prompt Engineering Utilizadas

## System Prompt

O comportamento atual do assistente é controlado por
`prompts/system_prompt_v4.md`. O v4 separa as instruções em blocos XML de identidade,
escopo, segurança, conhecimento, precisão e saída estruturada.

O prompt define:

* Escopo do domínio
* Regras de segurança
* Restrições de privacidade
* Formato das respostas
* Uso do contexto do condomínio

Além das proteções já existentes, o v4 define que o conhecimento condominial é apenas
uma fonte de dados operacionais, não documentação oficial GoodWe. Valores fornecidos
pelo usuário em simulações têm precedência somente naquele cenário e não alteram a base.
O modelo deve responder exclusivamente com JSON compatível com `ConsultaRecarga`.


## Few-Shot Prompting

O System Prompt contém exemplos de perguntas e respostas para orientar o comportamento esperado do modelo.

Exemplos incluídos:

* Cálculo de custo
* Tempo de recarga
* Conflitos de uso
* Horário de pico
* Perguntas fora de escopo
* Solicitações adversariais


## Memória Conversacional

O histórico da conversa é armazenado e reenviado ao modelo a cada interação.

Isso permite responder perguntas dependentes de contexto.

Cada conversa é isolada por `session_id`. O histórico recente é mantido em pares completos e, quando o limite de tokens é atingido, os turnos antigos são convertidos em um resumo determinístico e extrativo, sem chamada adicional ao modelo.

A implementação usa `RunnableWithMessageHistory` com a chave de entrada `input` e a chave de histórico `history`. Um `SessionMemoryStore` isola o histórico por sessão e aplica o orçamento definido por `MESSAGE_TOKEN_LIMIT` (padrão: 4096), reservando espaço para o system prompt, a base condominial e `OLLAMA_MAX_OUTPUT_TOKENS`. A contabilização local usa o tokenizador `cl100k_base`.

Quando o orçamento é excedido, fatos dos turnos antigos são preservados em um resumo extrativo e os turnos recentes permanecem completos. Uma mensagem individual maior que o orçamento é truncada antes de chegar ao modelo; esse trade-off impede estouro de contexto, mas pode descartar o fim da mensagem. A memória é mantida apenas em processo para esta Sprint: reiniciar a aplicação apaga todas as sessões. Persistência entre reinícios exigiria um armazenamento externo.

Exemplo:

```text
Usuário:
Quanto custa carregar 30 kWh?

Assistente:
R$ 27,60

Usuário:
E metade disso?

Assistente:
R$ 13,80
```


## Contexto Externo

O sistema utiliza `data/conhecimento_condominio_v2.md` como base versionada de
conhecimento específico do condomínio.

Exemplo:

```text
Tarifa padrão: R$0,92/kWh
Quantidade de carregadores: 4
Potência média: 7 kW
Horário de pico: 18h às 21h
Reservas de até 4 horas por morador
Prioridade para quem reservou primeiro
```

Essas informações são incorporadas como uma mensagem de sistema delimitada durante a
inicialização. A base é tratada como dado operacional do condomínio, não como fonte
oficial de especificações GoodWe, e seus tokens fazem parte do limite total da conversa.

### Base condominial v2

O arquivo `data/conhecimento_condominio_v2.md` contém os seguintes dados versionados:

| Informação | Valor |
|---|---|
| Tarifa padrão | R$ 0,92/kWh |
| Quantidade de carregadores | 4 |
| Potência média | 7 kW |
| Horário de pico | 18h às 21h |
| Limite de reserva | Até 4 horas por morador |
| Critério de conflito | Prioridade para quem reservou primeiro |

A base é carregada apenas com o prompt v4. As versões v1, v2 e v3 permanecem isoladas
desse conteúdo para preservar a reprodução histórica das avaliações.

<br>

# ✨ Funcionalidades

* Cálculo de custos de recarga
* Estimativa de tempo de carregamento
* Consulta de regras operacionais
* Uso de conhecimento contextual
* Memória conversacional
* Proteção contra solicitações adversariais
* Respostas especializadas para o domínio GoodWe EV ChargeOps

<br>

# 📁 Estrutura do Projeto

```text
ChargeWise_AI/
│
├── data/
│   ├── conhecimento_condominio_v1.md
│   └── conhecimento_condominio_v2.md
├── tests/
│   └── resultados_testes.md
│
├── prompts/
├── src/
│   ├── chain/
│   │   ├── builder.py
│   │   └── memoria.py
│   ├── chatbot.py
│   ├── config.py
│   └── main.py
├── requirements.txt
├── .env.example
└── README.md
```

# Arquitetura LCEL

O fluxo atual é: entrada do usuário → guardrail de escopo → `LCELChainWrapper` → histórico limitado por tokens → `ChatPromptTemplate` com prompt versionado e contexto condominial → `ChatOllama` ou modelo mock determinístico → parsing Pydantic (`ConsultaRecarga`) → moderação de saída. `RunnableWithMessageHistory` mantém sessões isoladas em memória; reiniciar o processo apaga o histórico. O detalhamento está em `docs/arquitetura_plano_sprint3.md`.

<br>

# 🚀 Como Executar

## 1. Clonar o Repositório

```bash
git clone https://github.com/mathsant-js/ChargeWise_AI.git

cd ChargeWise_AI
```

## 2. Criar Ambiente Virtual

Linux/Mac:

```bash
python -m venv .venv

source .venv/bin/activate
```

Windows:

```bash
python -m venv .venv

.venv\Scripts\activate
```

## 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

<br>

# ⚙️ Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
OLLAMA_API_KEY=sua_chave_aqui
OLLAMA_HOST=https://ollama.com
OLLAMA_MODEL=gpt-oss:120b
```

<br>

# ▶️ Executando o Projeto

```bash
python3 -m src.main
```

Sem credencial, esse comando inicia em modo mock. Para o resultado do modelo configurado, informe uma `OLLAMA_API_KEY` válida e mantenha `USE_MOCK_MODEL=false`.

<br>

# 💬 Exemplos de Uso

### Consulta de custo

```text
Usuário:
Quanto custa carregar 25 kWh?

Assistente:
O custo estimado é de R$23,00.
```

### Tempo de recarga

```text
Usuário:
Quanto tempo leva para carregar uma bateria de 35 kWh?

Assistente:
Aproximadamente 5 horas.
```

### Conflito de agendamento

```text
Usuário:
Dois moradores reservaram o mesmo horário.

Assistente:
A prioridade deve ser dada a quem realizou a reserva primeiro.
```

<br>

# 🧪 Testes Realizados

Foram executados testes para validar:

* Funcionalidade dos cálculos
* Casos de borda (Edge Cases)
* Perguntas fora de escopo
* Resistência a Prompt Injection
* Uso do contexto do condomínio
* Memória conversacional

Execute a suíte para obter o resultado da revisão atual; números registrados em relatórios são snapshots das execuções que os geraram.

## Comandos de validação e entrega

```bash
pytest -q tests/
python3 evals/run_evals.py
python3 -m src.main
```

Sem argumentos, `run_evals.py` verifica os dois fluxos em modo offline sem sobrescrever os relatórios versionados. Use as opções descritas em `evals/README.md` para gerar artefatos offline ou executar o modelo real.

## Avaliação do prompt v4 e da base condominial v2

Uma avaliação suplementar offline comparou o v3 sem a base com o v4 usando
`data/conhecimento_condominio_v2.md`, nos mesmos 10 casos condominiais:

| Configuração | Acertos | Taxa de sucesso | Tokens estimados |
|---|---:|---:|---:|
| v3 sem base condominial | 2/10 | 20% | 12.802 |
| v4 com base condominial v2 | 10/10 | 100% | 15.793 |

O v4 passou nos casos de consulta factual, cálculo com tarifa padrão, tarifa específica
de uma simulação, formato estruturado e proteção contra alteração da base. O ganho de
cobertura teve custo de 2.991 tokens no conjunto, aumento de 23,36%.

Também foi executado um benchmark pareado de memória longa. Com o limite total padrão
de 4.096 tokens, o contexto adicional reduziu o orçamento efetivo de histórico de 2.261
tokens no v3 para 1.930 no v4. A primeira perda da âncora ocorreu após 12 turnos no v3 e
8 no v4. Ao elevar a janela do v4 para 4.427 tokens, equalizando o orçamento efetivo, as
duas versões tiveram o mesmo resultado. Assim, a diferença observada decorre dos 331
tokens adicionais de contexto, e não de uma mudança no algoritmo de memória.

Essas avaliações usam o modelo determinístico local e servem como evidência técnica
reproduzível. Elas não substituem a validação com `gpt-oss:120b`. Os protocolos e
relatórios completos estão em `evals/README.md`, `evals/condominium_results.json` e
`evals/memory_v3_v4_comparison.json`.

<br>

# 🎥 Vídeo demonstrativo

🎥 Assistir no YouTube:
> https://youtu.be/SE9UwafTqJU

<br>

# 🎓 Projeto Acadêmico

Projeto desenvolvido para a disciplina de Prompt Engineering and AI.

Global Solution 2026.1 — FIAP

Desafio GoodWe EV ChargeOps.
