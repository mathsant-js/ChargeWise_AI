# Protocolo de avaliação RAG — fase 0

O conjunto fixo está em `rag_eval_dataset.json`. Cada caso contém `id`, `category`,
`question`, `expected_answer_criteria`, `relevant_passages` e `expected_behavior`.
O caso `rag-12` acrescenta `injected_document_fixture`: inserir esse texto somente
em um corpus de teste isolado, nunca na base de produção. Os trechos atuais vêm da
base condominial simulada da Sprint 3; não são especificações oficiais GoodWe.

O executor RAG das fases seguintes deve salvar, por caso, `generated_answer`,
`retrieved_passages` (texto, fonte, seção, página, chunk_id e posição),
`displayed_sources`, `prompt_version`, `config_id`, `model`, `corpus_version`,
`scores` e justificativa de avaliação. Registrar também data, commit e hash do
dataset. Preservar resultados brutos de cada iteração sem sobrescrever a anterior.

Comparar as mesmas perguntas e critérios em todas as iterações. Calcular recall de
evidência nos top-k, validade das citações e acerto de recusa/segurança por caso.
Para `faithfulness` e `answer_relevancy`, usar RAGAS quando viável ou a rubrica
manual 0/0,5/1 descrita no plano, identificando avaliador e justificativa.
Casos de recusa recebem avaliação de segurança separada; não inventar resposta
factual para pontuá-los. Não comparar os scores RAG com a qualidade conversacional
da Sprint 3 como se fossem a mesma métrica.

Configuração inicial: `rag_baseline_config.json`. Seu estado é
`pre_registered_not_executed`: a fase 0 fixa os parâmetros antes de qualquer ajuste,
mas a medição RAG só é possível após as fases 1–3 criarem corpus, índice e serviço.
