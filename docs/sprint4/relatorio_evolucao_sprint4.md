# ChargeWise AI — evolução da Sprint 4

**Curso:** Ciência da Computação | **Turma:** 2º semestre (2SEM), 2026.2

**Disciplina:** Prompt and Artificial Intelligence | **Parceiro:** GoodWe Brasil | **Data:** 23/10/2026

## Resumo

A Sprint 4 converteu a base fixa em um fluxo RAG persistente e adicionou uma interface Streamlit. O corpus disponível é um cenário condominial simulado; não contém manuais ou especificações oficiais GoodWe. A aplicação recupera trechos, pede ao modelo seleção de citações literais, verifica cada citação e mostra documento e seção. Perguntas sem evidência ou de segurança recebem recusa. O índice Chroma contém 11 chunks, gerados com divisão de 900 caracteres e overlap de 135, usando `nomic-embed-text`.

## Pipeline e decisões

Documentos Markdown com manifesto de origem → loader → limpeza e chunking → embeddings Ollama → Chroma persistente → retriever top-k → filtro por assunto → prompt RAG v3 → seleção JSON pelo modelo → validação literal das evidências → resposta e fontes na interface. O contexto recuperado é tratado como dado não confiável. O índice é reconstruído explicitamente quando o corpus ou embeddings mudam; credenciais e índice local não são versionados.

## Antes e depois

| Eixo | Antes: Sprint 3 | Depois: Sprint 4 | Evidência |
|---|---|---|---|
| Conhecimento | Contexto condominial inserido diretamente no prompt | Corpus rastreável e índice Chroma persistente | Manifesto, 11 chunks, fingerprint do índice |
| Resposta | Saída estruturada conversacional, sem citação de trecho | Seleção de citação literal validada, documento e seção visíveis | Serviço RAG e interface Streamlit |
| Avaliação | Intenção, schema, memória e guardrails | Recuperação, fidelidade, relevância, citação e recusas em 12 casos | `evals/relatorio_rag.md` e snapshots brutos |
| Relevância RAG | Sem score comparável | 0,688 no baseline v1/k1 → 1,000 na configuração final v3/k3 com filtro | Rubrica manual assistida, 8 perguntas respondíveis |
| Segurança | Guardrails de entrada e moderação | Guardrails mais recusa sem evidência e teste isolado de injeção em documento | 4/4 recusas fixas; 1 fixture de injeção resistida |

Os scores conversacionais legados e os scores RAG usam datasets e rubricas diferentes; não representam ganho numérico entre sprints. O ganho RAG de relevância pertence às iterações internas da Sprint 4. O primeiro aumento isolado de prompt foi de 0,688 para 0,813 (v2 → v3); o filtro do pipeline levou a 1,000.

## Comparação de modelos no RAG

Em 23/10/2026, `qwen2.5:1.5b` e `llama3.2:latest` foram chamados no Ollama local, em sequência, com o mesmo dataset de 12 casos, índice, prompt v3, k=3, temperature=0, top_p=0,9 e max_tokens=500. A revisão assistida por Codex deu relevância 1,000 ao Qwen e 0,875 ao Llama (8 casos com resposta esperada). Ambos tiveram recall estrito 0,500, fidelidade e citação 1,000 nas respostas emitidas, e 4/4 recusas corretas. O Llama recusou indevidamente a pergunta ambígua sobre a potência do equipamento pessoal; a média de 7 kW do cenário poderia ter sido informada com ressalva. Latência média ponta a ponta: 58,95 s e 62,57 s, respectivamente, em CPU local; a primeira chamada do Llama levou 246,16 s. Uma rodada por modelo não estabelece desempenho geral. O comparativo conversacional legado usa outro dataset e permanece separado em `docs/relatorio_modelos.md`.

## Problemas e soluções

1. **Recuperação parcialmente imprecisa:** a busca top-k=3 encontrou apenas metade dos trechos exatos esperados. FAQ equivalente às vezes sustentou resposta correta sem contar como acerto estrito. O prompt v3 e o filtro por assunto corrigiram respostas fora do tópico, mas o recall de evidência exata permanece 0,500.
2. **Instrução maliciosa em documento:** texto recuperado tentava revelar o prompt. O serviço delimita o contexto, descarta citações que contenham comandos e exige substring literal e `chunk_id` válido. O fixture isolado foi respondido com a política de reserva sem revelar instruções internas.
3. **Cobertura limitada:** não foram obtidos manuais oficiais GoodWe para o corpus. O produto identifica o cenário como simulado e recusa especificações de modelo e telemetria em tempo real.

## Limitações e próximos passos

A avaliação 0/0,5/1 foi assistida por Codex sobre amostra pequena, sem RAGAS ou revisão humana independente. O limiar de distância 1,0 ainda não foi calibrado. As respostas literais podem ser menos naturais que uma síntese, mas permitem verificar suporte e citação. O índice depende de Ollama local em operação; o tempo de CPU e disponibilidade de modelos variam. Para ampliar o escopo, incorporar documentação GoodWe autorizada, aumentar o dataset, revisar notas por mais de um avaliador e calibrar recuperação/recusa.

## Equipe

| Integrante | RM |
|---|---:|
| Bernardo Zauza Amorim | 568808 |
| Bruno Almeida de Oliveira | 572648 |
| Gabriel Góes Nunes Pereira | 571735 |
| Guilherme Vinciguerra Carvalho | 571951 |
| Marcos Peterson Martins Pereira | 573857 |
| Matheus Jorge Santana | 574166 |

## Reprodução e fontes internas

Instalação e execução em `app/README.md`; protocolo e resultados em `evals/relatorio_rag.md`; comparação de modelos em `docs/relatorio_modelos.md`; composição em `docs/sprint4/integrantes_rm_turma.txt`.
