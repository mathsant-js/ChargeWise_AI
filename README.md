# Sprint1_Jorge
# ChargeWise AI  
Chatbot Inteligente para Orquestração de Recarga de Veículos Elétricos em Condomínios

------------------------------------------------------------------------------------------------------------------------------------------

##  Integrantes

- Bruno — RM: 572648  
- Marcos — RM: 573857
- Bernardo — RM: 568808
- Gabriel — RM: 571735
- Guilherme — RM: 571951

------------------------------------------------------------------------------------------------------------------------------------------

##  Problema

O crescimento acelerado da adoção de veículos elétricos impõe novos desafios à infraestrutura de recarga em ambientes compartilhados, como condomínios residenciais.

Atualmente, há uma ausência de mecanismos inteligentes capazes de:

- Realizar a **orquestração eficiente da potência energética** entre múltiplos usuários  
- Monitorar e registrar o consumo individual de forma precisa  
- Garantir a **distribuição justa dos custos de energia (kWh)**  
- Organizar o uso dos eletropostos de forma escalável  
- Fornecer comunicação clara entre moradores e administração  

Esse cenário resulta em ineficiência energética, conflitos entre usuários e dificuldade de gestão.

O problema está diretamente alinhado ao desafio proposto pela GoodWe, especialmente no contexto de **EV ChargeOps**, que aborda a gestão inteligente de recarga em ambientes compartilhados.

------------------------------------------------------------------------------------------------------------------------------------------

##  Proposta do Chatbot

O **ChargeWise AI** é um chatbot inteligente projetado como uma ferramenta operacional para apoiar a gestão de recarga de veículos elétricos em condomínios.

A solução atua como uma interface conversacional baseada em IA, permitindo:

- Consulta de consumo energético individual (kWh)  
- Estimativa e explicação de custos de recarga  
- Suporte à **tomada de decisão baseada em dados**  
- Orientação sobre regras de uso e agendamento de carregadores  
- Respostas técnicas sobre tempo de recarga, potência e capacidade de bateria  

O chatbot será direcionado principalmente a síndicos e moradores, funcionando como um sistema de apoio à gestão, promovendo:

- Transparência no uso de energia  
- Eficiência operacional  
- Redução de conflitos  
- Melhor experiência do usuário  

------------------------------------------------------------------------------------------------------------------------------------------

##  Tecnologias Selecionadas

- Python → Desenvolvimento da lógica do sistema e backend  
- Modelo Open-Source (Qwen) → Processamento de linguagem natural e geração de respostas  
- Ollama → Execução local do modelo de IA  
- LangChain → Orquestração de contexto e fluxo de interação com o modelo  
- GitHub → Versionamento, documentação e colaboração  

------------------------------------------------------------------------------------------------------------------------------------------

##  Justificativa Técnica

A adoção de modelos de linguagem de grande escala (LLMs) permite a construção de interfaces conversacionais capazes de interpretar linguagem natural e fornecer respostas contextualizadas, o que é essencial em cenários de suporte operacional.

A API da OpenAI foi selecionada por sua capacidade de gerar respostas coerentes, adaptativas e com alto nível de compreensão semântica.

O uso do LangChain possibilita a **injeção de contexto estruturado**, garantindo que o modelo responda de acordo com regras específicas do domínio, como consumo energético, tarifação e uso compartilhado.

A escolha do Python se justifica pela sua ampla adoção em soluções de inteligência artificial e facilidade de integração com APIs e bibliotecas especializadas.

A arquitetura proposta é modular, escalável e orientada à integração futura com sistemas reais de monitoramento energético, permitindo evolução para um ambiente de **gestão inteligente de infraestrutura de recarga (smart charging)**.

Além disso, a solução proposta se alinha ao conceito de **orquestração energética inteligente**, permitindo uma gestão eficiente e equilibrada da infraestrutura de recarga em ambientes compartilhados.

Essa abordagem possibilita a otimização do uso dos recursos energéticos disponíveis, reduzindo riscos de sobrecarga, melhorando a previsibilidade de consumo e garantindo uma experiência mais justa e transparente para todos os usuários do sistema.
