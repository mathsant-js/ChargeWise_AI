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

O sistema foi desenvolvido como uma prova de conceito alinhada ao desafio GoodWe EV ChargeOps, simulando um ambiente real de operação de infraestrutura de recarga compartilhada.

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
```

<br>

# 🤖 Modelo de IA Utilizado

O projeto utiliza o modelo:

**gpt-oss:120b**

A comunicação ocorre através da Ollama Cloud API utilizando autenticação por API Key.

Configuração principal:

```python
client.chat(
    model="gpt-oss:120b",
    messages=mensagens
)
```

<br>


# 📊 Comparação Técnica de Modelos

Durante a fase de arquitetura foram avaliadas diferentes alternativas de modelos.

| Critério                       | GPT-OSS 120B | Qwen 2.5   |
| ------------------------------ | ------------ | ---------- |
| Qualidade em PT-BR             | Alta         | Boa        |
| Capacidade de instrução        | Alta         | Média/Alta |
| Contexto longo                 | Superior     | Boa        |
| Precisão em respostas técnicas | Alta         | Boa        |
| Latência                       | Moderada     | Menor      |
| Consumo computacional local    | Muito alto   | Médio      |
| Execução em nuvem              | Sim          | Sim        |
| Execução local                 | Limitada     | Fácil      |

### Justificativa da escolha

O GPT-OSS 120B foi selecionado por apresentar melhor aderência ao cenário de assistência técnica especializada, principalmente em:

* Seguimento de instruções complexas
* Uso consistente de contexto
* Melhor compreensão de português brasileiro
* Maior qualidade em respostas especializadas

Embora o Qwen apresente menor custo computacional e menor latência quando executado localmente, o GPT-OSS demonstrou melhor desempenho para o domínio do projeto.

<br>

# 🧠 Técnicas de Prompt Engineering Utilizadas

## System Prompt

O comportamento do assistente é controlado por um System Prompt especializado.

O prompt define:

* Escopo do domínio
* Regras de segurança
* Restrições de privacidade
* Formato das respostas
* Uso do contexto do condomínio


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

O sistema utiliza um arquivo de conhecimento específico do condomínio.

Exemplo:

```text
Tarifa padrão: R$0,92/kWh
Quantidade de carregadores: 4
Potência média: 7 kW
Horário de pico: 18h às 21h
```

Essas informações são incorporadas ao contexto do modelo durante a inicialização.

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
│   └── conhecimento_condominio.txt
├── tests/
│   └── resultados_testes.md
│
├── system_prompt.txt
├── config.py
├── chatbot.py
├── app.py
├── requirements.txt
├── .env.example
└── README.md
```

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
```

<br>

# ▶️ Executando o Projeto

```bash
python app.py
```

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

Resultado geral:

```text
Total de testes: 6
Aprovados: 6
Taxa de sucesso: 100%
```

<br>

# 🎥 Vídeo demonstrativo

🎥 Assistir no YouTube:
> https://youtu.be/SE9UwafTqJU

<br>

# 🎓 Projeto Acadêmico

Projeto desenvolvido para a disciplina de Prompt Engineering and AI.

Global Solution 2026.1 — FIAP

Desafio GoodWe EV ChargeOps.
