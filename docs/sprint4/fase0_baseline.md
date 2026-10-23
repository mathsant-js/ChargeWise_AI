# Fase 0 — baseline e preparação

- Branch de partida: `sprint4_rag`.
- Commit de partida: `0ce14f915ee28b7033ef89668e6dc427737f9209` (2026-09-12).
- O plano em `docs/sprint4/plano_desenvolvimento_sprint4.md` já estava presente
  como arquivo não rastreado; foi preservado.
- Artefatos da Sprint 3 existentes: `evals/eval_dataset.json`,
  `evals/legacy_results.json`, `evals/sprint3_results.json`,
  `evals/condominium_results.json` e prompts v1–v4.

Tentativa de reprodução: `python3 -m pytest -q tests/` parou na coleta porque
`tiktoken` precisa obter `cl100k_base.tiktoken` de
`openaipublic.blob.core.windows.net` e o ambiente não conseguiu resolver esse
host. A mesma dependência é importada por `evals/run_evals.py`, impedindo a
execução offline neste ambiente. Nenhum resultado histórico foi sobrescrito.

O dataset RAG fixo e o protocolo estão em `evals/rag_eval_dataset.json` e
`evals/rag_eval_protocol.md`. A configuração `rag-baseline-v0` foi pré-registrada
em `evals/rag_baseline_config.json` com chunk de 900 caracteres, overlap de 135 e
top-k 3. Ainda não existe pipeline RAG para medir recuperação ou geração; por isso
não há métricas RAG capturadas nem alegação de ganho nesta fase.
