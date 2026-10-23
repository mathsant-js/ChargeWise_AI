# Plano de desenvolvimento — Sprint 4

**Projeto:** ChargeWise AI  
**Disciplina:** Prompt and Artificial Intelligence — FIAP 2026.2  
**Entrega prevista no enunciado:** 23/10/2026  
**Objetivo:** evoluir o chatbot conversacional da Sprint 3 para um RAG persistente, avaliado, seguro e acessível por interface web.

## 1. Estado atual do projeto

A análise considera o repositório existente, seus relatórios e o enunciado oficial no PDF `EV_Challenge_2026_GoodWe_Sprints_3_4.pdf`.

| Área | Situação encontrada | Implicação para a Sprint 4 |
|---|---|---|
| Aplicação | `GoodWeChatbot` e cadeia LCEL já implementados em `src/chatbot.py` e `src/chain/builder.py`. Há saída Pydantic estruturada e memória por sessão. | Reaproveitar o chatbot e preservar o fluxo conversacional; integrar RAG sem duplicar regras de saída e segurança. |
| Prompts | Prompts conversacionais v1–v4 em `prompts/`, com histórico de versões em `prompts/README.md`. | Criar prompt RAG versionado separado, com tabela de mudanças e scores por iteração. |
| Conhecimento | `data/conhecimento_condominio_v1.md` e `v2.md`; contexto é inserido diretamente no prompt v4. | Criar corpus expandido em `data/knowledge_base/`, com documentos rastreáveis e metadados de fonte/seção. |
| Segurança | Guardrails de entrada em `src/guardrails/scope_validator.py` e validação/moderação de saída em `src/guardrails/moderation.py`; prompt v4 separa fatos GoodWe do cenário simulado. | Adaptar para perguntas respondíveis pelo corpus, recusa sem evidência, citações e conteúdo recuperado tratado como dado não confiável. |
| Avaliações | Datasets e relatórios conversacionais em `evals/`, incluindo comparações de prompt, modelo, memória e condomínio. Avaliações offline usam modelo determinístico e não representam qualidade de LLM real. | Acrescentar dataset RAG e avaliação específica de faithfulness e answer_relevancy; não misturar os números legados com os novos scores. |
| Modelos | `docs/relatorio_modelos.md` já registra comparação de `gpt-oss:120b` e `gpt-oss:20b`; `qwen3:8b` não estava disponível na medição registrada. | Reaproveitar como histórico e complementar com comparação controlada no fluxo RAG, documentando parâmetros e disponibilidade real. |
| Dependências e interface | `requirements.txt` não inclui ChromaDB, integração de embeddings nomic, PyMuPDF, RAGAS ou framework de UI. Não há pasta `app/` nem `src/rag/`. | Implementar e fixar dependências compatíveis; escolher Streamlit para acelerar a interface da entrega, salvo restrição técnica descoberta na implementação. |
| Relatórios | Há relatório da Sprint 3 em PDF e HTML, além de documentação de arquitetura e modelos. | Gerar relatório específico da Sprint 4, limitado a cinco páginas, com tabela obrigatória antes/depois. |

### Lacunas prioritárias

1. Ausência completa de pipeline RAG e armazenamento vetorial persistente.
2. Base atual pequena e carregada como texto fixo, sem chunking, embeddings ou busca semântica.
3. Avaliações existentes medem intenção, schema, memória e guardrails; não medem recuperação, faithfulness ou answer relevancy.
4. Não há interface web para consultar o sistema e ver fontes.
5. O relatório de modelos existente é conversacional e precisa ser complementado para o uso do RAG e seus parâmetros.

## 2. Resultado esperado e critérios de aceite

Ao final, uma pessoa deve conseguir iniciar a aplicação, fazer uma pergunta sobre carregamento GoodWe ou operação condominial, receber resposta baseada somente em trechos recuperados, ver citações de documento/seção e receber recusa segura quando a base não sustenta a resposta.

A entrega será considerada pronta quando:

- documentos autorizados e relevantes estiverem organizados em `data/knowledge_base/`, com fonte, versão e seção identificáveis;
- ingestão, chunking, embeddings `nomic-embed-text` via Ollama e gravação/consulta em ChromaDB persistente funcionarem de forma reproduzível;
- o pipeline cobrir carregamento, recuperação, geração, validação de grounding e citação;
- perguntas sem evidência e tentativas de injeção contidas nos documentos forem recusadas/ignoradas;
- a interface web consumir o pipeline e apresentar resposta, fontes e mensagem de recusa;
- houver dataset fixo e pelo menos duas iterações comparáveis, registradas com scores e evidência de ganho;
- faithfulness e answer_relevancy forem avaliadas por RAGAS ou por rubrica manual 0–1 documentada, aplicada ao mesmo conjunto em cada iteração;
- prompt RAG estiver versionado, com alteração e ganho medido registrados;
- `docs/relatorio_modelos.md` documentar pelo menos dois modelos, quando disponíveis, além de temperature, top-k, top_p e max_tokens;
- existir relatório da evolução em PDF com no máximo cinco páginas e a tabela antes/depois pedida no enunciado;
- instruções de instalação e execução da interface estiverem em `app/README.md`, sem credenciais no Git.

## 3. Arquitetura proposta

```text
Documentos em data/knowledge_base/
  → loader (PDF e Markdown)
  → limpeza e divisão em chunks
  → embeddings nomic-embed-text
  → ChromaDB persistente

Pergunta
  → guardrails de entrada
  → retriever (top-k configurável)
  → prompt RAG versionado + modelo
  → validação de evidência e citação
  → resposta e fontes na interface
  → registro no conjunto de avaliação
```

A chamada principal deve ficar encapsulada em um serviço reutilizável por CLI, avaliação e interface. Isso evita que a interface implemente regras próprias. O caminho conversacional atual pode permanecer disponível; quando houver consulta RAG, fatos específicos devem vir dos documentos recuperados, sem incorporar fatos não suportados pelo contexto.

## 4. Plano de execução por fases

### Fase 0 — Baseline e preparação

- Registrar branch/commit de partida e confirmar que os artefatos da Sprint 3 permanecem reproduzíveis.
- Selecionar perguntas do projeto atual e criar um conjunto RAG fixo, com perguntas respondíveis, não respondíveis, ambíguas, segurança e prompt injection em documento.
- Definir estrutura de registro por caso: pergunta, resposta esperada ou critérios, trechos relevantes, resposta gerada, fontes, scores e versão de prompt/configuração.
- Capturar métricas de baseline do RAG inicial (por exemplo, chunking e top-k iniciais) antes de alterar parâmetros.

**Saída:** `evals/rag_eval_dataset.json` e configuração de baseline identificada.

### Fase 1 — Corpus e ingestão

- Criar `data/knowledge_base/` e inventariar os documentos disponíveis.
- Incluir materiais GoodWe pertinentes (manuais ChargeGrid/EV ChargeOps somente quando obtidos de fonte legítima), FAQs de carregamento, regras condominiais e tarifas claramente identificadas como simuladas ou locais.
- Não criar especificações de produto para preencher lacunas. Registrar origem, data/versão, tipo de documento e seção.
- Implementar `src/rag/loader.py` com `PyMuPDFLoader` para PDF e suporte adequado a Markdown.
- Remover ruído de extração e preservar cabeçalhos/seções úteis para recuperação e citação.

**Saída:** corpus versionado e manifesto de fontes, com procedimento de ingestão repetível.

### Fase 2 — Chunking, embeddings e ChromaDB

- Implementar `src/rag/chunking.py` usando `RecursiveCharacterTextSplitter`.
- Iniciar experimento com tamanho aproximado de 800–1.000 caracteres e overlap de 120–150; tratar como hipótese inicial e ajustar pelos resultados, registrando o tamanho efetivo em tokens/caracteres.
- Preservar `source`, `document`, `section`, `page` e `chunk_id` nos metadados de cada trecho.
- Implementar `src/rag/embeddings.py` com `nomic-embed-text` através do endpoint Ollama configurado por ambiente.
- Implementar `src/rag/vector_store.py` com coleção persistente ChromaDB e rotina explícita de reindexação/versionamento do corpus, evitando duplicatas em ingestões repetidas.
- Não armazenar credenciais nem índices transitórios no controle de versão; definir política de persistência e instruções para reconstruir o índice.

**Saída:** índice persistente reproduzível e inspeção de trechos/metadados.

### Fase 3 — Retriever e pipeline RAG

- Implementar `src/rag/retriever.py` com `k` configurável e retorno dos trechos e metadados usados.
- Implementar `src/rag/prompt_rag.py` com prompt versionado, instruções explícitas de grounding, citação e recusa quando a evidência for insuficiente.
- Delimitar contexto como dado; instruções dentro de documentos nunca podem substituir as instruções do sistema ou do usuário.
- Implementar serviço end-to-end: recuperação → geração → validação de fontes → resposta estruturada.
- A resposta deve citar documento e seção (e página quando aplicável). Cada afirmação factual específica deve ser apoiada por pelo menos uma fonte exibida.
- Definir limiar/critério de recusa com base em relevância recuperada e testes de perguntas fora do corpus; não inventar especificações GoodWe.
- Reaproveitar guardrails da Sprint 3 para escopo, segurança elétrica, aconselhamento jurídico/financeiro e jailbreak, ajustando os casos permitidos ao conteúdo da base.

**Saída:** serviço RAG independente da UI e exemplos verificáveis com fontes.

### Fase 4 — Interface web

- Criar `app/` com Streamlit como opção inicial de menor atrito para a equipe.
- Disponibilizar campo de pergunta, botão de envio, resposta, fontes/seções, estado de recusa e mensagens de erro operacional claras.
- Manter credenciais exclusivamente em variáveis de ambiente ou `.env` gitignored; fornecer `.env.example` sem segredos.
- Criar `app/README.md` com instalação, indexação, configuração e comando de execução.
- Testar inicialização limpa e fluxo de consulta usando o pipeline real do projeto.

**Saída:** interface executável localmente, com citação visível.

### Fase 5 — Avaliação e duas iterações

- Preferir RAGAS para `faithfulness` e `answer_relevancy` se o ambiente/modelo de avaliação permitir.
- Se RAGAS não for viável, documentar em `evals/` rubrica manual 0–1, exemplos de nota e critérios para ambos os eixos; aplicar no mesmo eval set em todas as iterações.
- Avaliar separadamente recuperação/contexto, fidelidade, relevância, cobertura de citações e segurança/recusas. Explicitar limitações da avaliação manual e de modelos determinísticos.
- Executar no mínimo duas iterações. Exemplo: Iteração 1 baseline (chunks/top-k/prompt inicial); Iteração 2 ajuste baseado nas falhas (chunking, top-k, filtro ou prompt). Alterar uma variável principal por vez quando possível.
- Versionar prompts, congelar dataset e configurações por execução, salvar resultado bruto e resumo agregado. Não alegar ganho se as métricas não mostrarem melhora; diagnosticar e iterar novamente.
- Registrar ganho por versão do prompt na tabela em `src/rag/prompt_rag.py` ou `prompts/README.md` específico do RAG.

**Saída:** pelo menos dois snapshots comparáveis com ganho demonstrado e relatório `evals/relatorio_rag.md` (ou `docs/relatorio_rag.md`, mantendo um caminho canônico).

### Fase 6 — Modelos, integração e entrega

- Comparar dois ou mais modelos no mesmo dataset e configuração RAG, quando acessíveis. Registrar modelo, provider, data, disponibilidade, temperatura (recomendado 0), `k`, `top_p`, `max_tokens`, latência, custo/limitações quando conhecidos e scores.
- O relatório atual em `docs/relatorio_modelos.md` serve como ponto de partida, mas precisa diferenciar resultado legado do novo benchmark RAG.
- Implementar multi-provider somente depois do caminho obrigatório estar estável; como bônus, a chamada deve realmente consultar mais de um modelo e mais de um prompt, documentando a comparação.
- Consolidar limitações, problemas e decisões para o PDF de evolução (máximo cinco páginas), com equipe e divisão de trabalho.
- Revisar histórico Git, arquivos `.env`, artefatos grandes e permissões do repositório público; criar o `.txt` de integrantes, RM e turma para a entrega.

**Saída:** interface, avaliações, relatórios e repositório prontos para submissão.

## 5. Estrutura de arquivos alvo

```text
data/knowledge_base/
  README.md                 # inventário, fontes e licenças
  ...                       # PDFs/Markdown autorizados
src/rag/
  __init__.py
  loader.py
  chunking.py
  embeddings.py
  vector_store.py
  retriever.py
  prompt_rag.py             # versões explícitas
  pipeline.py               # integração reutilizável
app/
  app.py                    # interface Streamlit
  README.md
 evals/
  rag_eval_dataset.json
  ragas/ ou manual/         # resultados por iteração
  relatorio_rag.md
```

Ajustar nomes ao padrão do repositório, mantendo as pastas solicitadas. O relatório de modelos pode permanecer em `docs/relatorio_modelos.md`; o PDF e o Markdown de evolução devem ficar em `docs/` ou `docs/sprint4/`, conforme a organização final.

## 6. Avaliação: protocolo e métricas

| Dimensão | Evidência mínima | Como comparar |
|---|---|---|
| Recuperação | trechos relevantes entre os top-k; fonte e seção corretas | revisão por caso e taxa de recuperação de evidência relevante |
| Faithfulness | afirmações da resposta apoiadas pelo contexto recuperado | RAGAS ou rubrica manual 0–1; média e exemplos de falha |
| Answer relevancy | resposta aborda a pergunta sem desviar | RAGAS ou rubrica manual 0–1; média por mesmo dataset |
| Citação | presença, validade e correspondência da fonte citada | taxa de respostas sustentadas com citação verificável |
| Segurança | recusas de perguntas sem evidência e resistência à injeção | casos adversariais fixos e inspeção da resposta/contexto |
| Operação | persistência e inicialização repetida do índice/interface | reiniciar o processo e confirmar consulta sem reingestão acidental |

**Rubrica manual sugerida:** `0` = não atende; `0,5` = atende parcialmente, com omissão ou suporte insuficiente; `1` = atende integralmente. Para faithfulness, comparar cada afirmação factual com os trechos recuperados. Para answer relevancy, avaliar aderência, cobertura dos pontos pedidos e ausência de conteúdo irrelevante. Registrar avaliador, justificativa curta por caso e adjudicação de divergências. Essa rubrica é uma aproximação documentada, não deve ser apresentada como score RAGAS.

## 7. Riscos e decisões

| Risco | Resposta planejada |
|---|---|
| Manuais GoodWe ou endpoint Ollama indisponíveis | Priorizar fontes legítimas disponíveis e registrar lacunas; não simular fatos de produto. Separar claramente conteúdo condominial de documentação oficial. |
| RAGAS não roda por incompatibilidade ou falta de modelo avaliador | Usar fallback manual com rubrica 0–1 no mesmo conjunto em todas as iterações e justificar equivalência/limitações. |
| Ollama Cloud ou `nomic-embed-text` indisponível | Registrar erro e alternativa aprovada tecnicamente; manter a integração exigida como caminho documentado e não reportar mock como medição real. |
| Citações apontam para chunks sem seção/página | Preservar metadados no loader/chunker e validar renderização da fonte já na primeira fase do pipeline. |
| Prompt injection em PDF/documento | Tratar texto recuperado como dado não confiável; testar instruções maliciosas inseridas no corpus; nunca executar comandos ou mudar política a partir do documento. |
| Índice persistente fica desatualizado ou duplica chunks | Usar identificador de corpus/versão, rotina explícita de limpeza/recriação e documentação da reindexação. |
| Scores não melhoram nas duas iterações | Inspecionar falhas de recuperação/geração, alterar uma hipótese por vez e executar nova rodada; manter resultados negativos no histórico. |
| Memória conversacional contamina respostas RAG | Definir claramente quando histórico pode resolver referências pronominais e exigir que fatos do domínio venham do contexto recuperado para aquela pergunta. |

## 8. Entregáveis e responsáveis

As responsabilidades individuais devem ser atribuídas pelo grupo; os nomes e RMs abaixo são a composição atualmente registrada no README.

| Integrante | RM | Frente principal proposta |
|---|---:|---|
| Bernardo Zauza Amorim | 568808 | Curadoria do corpus e registro das fontes |
| Bruno Almeida de Oliveira | 572648 | Loader, limpeza e chunking |
| Gabriel Góes Nunes Pereira | 571735 | Embeddings, ChromaDB e recuperação |
| Guilherme Vinciguerra Carvalho | 571951 | Pipeline, prompt RAG e segurança |
| Marcos Peterson Martins Pereira | 573857 | Dataset, avaliação RAGAS/fallback e comparação de modelos |
| Matheus Jorge Santana | 574166 | Interface web, integração e relatório de evolução |

A proposta serve para distribuir as frentes iniciais; o grupo deve refletir a divisão efetivamente realizada no relatório final. Todos devem contribuir com integração, revisão e commits regulares.

## 9. Checklist final de entrega

- [ ] `data/knowledge_base/` expandida, fontes e limites documentados.
- [ ] `src/rag/` com loader, chunking, embeddings, ChromaDB, retriever, prompt versionado e pipeline.
- [ ] ChromaDB persistente e rotina de ingestão/reindexação reproduzível.
- [ ] Grounding estrito, citação documento/seção e recusa sem contexto suficiente.
- [ ] Testes de prompt injection via documentos e perguntas fora de escopo/contexto.
- [ ] Interface web local funcional e fontes visíveis.
- [ ] Avaliação RAGAS ou fallback manual 0–1 em duas ou mais iterações no mesmo dataset.
- [ ] Duas iterações com ganho de score registrado; resultados e critérios preservados em `evals/`.
- [ ] Prompt RAG versionado com tabela de mudanças e ganho medido.
- [ ] Relatório de modelos/parâmetros com 2+ modelos, temperature, `k`, `top_p` e `max_tokens`.
- [ ] Relatório de evolução em PDF de até cinco páginas, com resumo, pipeline/chunking, tabela antes/depois, dois problemas e soluções, equipe e divisão.
- [ ] README da interface e instruções gerais atualizados.
- [ ] `.env` e chaves fora do histórico; repositório público acessível ao professor.
- [ ] Arquivo `.txt` com nome, RM e turma dos integrantes.

## 10. Referências locais

- Enunciado oficial: `EV_Challenge_2026_GoodWe_Sprints_3_4.pdf` (material fornecido pelo grupo).
- Estado do produto: `README.md`, `src/chatbot.py`, `src/chain/builder.py`, `src/guardrails/`, `prompts/`, `data/`.
- Histórico de avaliações: `evals/README.md`, `evals/before_after.md`, `evals/condominium_results.json`, `evals/model_comparison_results.json`.
- Relatórios existentes: `docs/relatorio_modelos.md`, `docs/arquitetura_plano_sprint3.md`, `docs/relatorio_evolucao_sprint3.pdf`.
