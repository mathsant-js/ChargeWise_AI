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
top-k 3. Ainda não existe pipeline RAG para medir recuperação ou geração; por isso
não há métricas RAG capturadas nem alegação de ganho nesta fase. A medição
continua pendente até a implementação do corpus/indexação e serviço RAG das
fases 1–3. Antes de ajustar chunking, top-k ou prompt, executar o dataset fixo
com `rag-baseline-v0` e salvar os resultados brutos segundo
`evals/rag_eval_protocol.md`.
