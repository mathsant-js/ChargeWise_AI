# Fase 0 — baseline e preparação

- Branch de partida: `sprint4_rag`.
- Commit de partida: `0ce14f915ee28b7033ef89668e6dc427737f9209` (2026-09-12).
- O plano em `docs/sprint4/plano_desenvolvimento_sprint4.md` já estava presente
  como arquivo não rastreado; foi preservado.
- Artefatos da Sprint 3 existentes: `evals/eval_dataset.json`,
  `evals/legacy_results.json`, `evals/sprint3_results.json`,
  `evals/condominium_results.json` e prompts v1–v4.

Reprodução executada em 2026-10-23 no commit
`f3a3e2b2aff19442e9b80ce58b671ed83336e63b`. O vocabulário público
`cl100k_base.tiktoken` foi obtido para um cache local temporário do `tiktoken`.
Com `TIKTOKEN_CACHE_DIR` apontando para esse cache, `python3 -m pytest -q tests/`
passou (53 testes) e `python3 evals/run_evals.py` concluiu os 35 casos tanto
no fluxo legado (4,63/10) quanto no LCEL (9,26/10), em modo offline com modelo
determinístico. Resultados completos, incluindo hash do dataset e parâmetros,
estão em `evals/phase0_sprint3_reproduction_legacy.json` e
`evals/phase0_sprint3_reproduction_lcel.json`. Os arquivos históricos não foram
sobrescritos. Eles foram gerados em modo real com outro commit; as notas e
latências não são diretamente comparáveis às desta reprodução offline.

O dataset RAG fixo e o protocolo estão em `evals/rag_eval_dataset.json` e
`evals/rag_eval_protocol.md`. A configuração `rag-baseline-v0` foi pré-registrada
em `evals/rag_baseline_config.json` com chunk de 900 caracteres, overlap de 135 e
top-k 3. Após as fases 1–2, a recuperação foi executada em 2026-10-23 com
`nomic-embed-text` local e ChromaDB persistente, sem ajustar os parâmetros.
O resultado bruto está em `evals/rag_retrieval_baseline_v0.json`, produzido por
`python3 evals/run_rag_retrieval_baseline.py`. Ele registra commit, hashes do
dataset e configuração, fingerprint do índice, trechos recuperados, posição,
distância e correspondência com cada trecho esperado. O índice continha 11
chunks. A média do recall de evidência nos sete casos avaliáveis foi **0,50**.
A correspondência exige fonte, seção e citação literal; uma FAQ parafraseada
não conta como acerto do trecho original. Casos sem evidência esperada não
entram na média. O caso `rag-12` fica fora porque sua fixture de injeção ainda
não foi indexada em corpus isolado.

O resultado mede somente recuperação. Houve falhas de evidência em tarifa
(`rag-01`, `rag-08`) e duração de reserva (`rag-03`); `rag-05` encontrou uma
das duas evidências. Resposta gerada, faithfulness, answer_relevancy, citações
exibidas e recusas dependem do serviço da fase 3. O status
`pre_registered_not_executed` no arquivo de configuração registra o estado
original do pré-registro e foi preservado para manter o hash do experimento.
