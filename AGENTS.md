# AGENTS.md – Quick reference for OpenCode sessions

## Setup & execution
- The legacy baseline is run with:
  ```bash
  python3 evals/run_evals.py
  ```
  (no `OLLAMA_API_KEY` needed; the LCEL builder falls back to a deterministic model.)
- Main entry point for the chatbot is `src/main.py`, executed with `python3 -m src.main`; it creates `GoodWeChatbot` from `src/chatbot.py`.
- `config.py` loads `OLLAMA_API_KEY`; without it on the default cloud host, the LCEL builder selects `DeterministicChatModel`.

## Architecture highlights
- **Flow**: user input → `src/guardrails/scope_validator.py` → LCEL chain in `src/chain/builder.py` → `ChatOllama` or deterministic mock → Pydantic v2 parser (`src/schemas/consulta_recarga.py`).
- **Memory**: `RunnableWithMessageHistory` + `SessionMemoryStore` keep a per-`session_id` history; token limit is configurable in the builder.
- **Structured output**: `ConsultaRecarga` schema defines `intencao`, `resposta`, optional `estado_carregador`, `potencia_kw`, `valor_estimado`, `requer_profissional`, and `confianca` (validated to be 0‑1).  Validators also reject negative power, invalid monetary values, unknown charger states, empty answers, and fabricated specifications.

## Guardrails
- **Pre‑model** (`src/guardrails/scope_validator.py`):
  - Blocks requests outside GoodWe domain, jailbreak attempts, prompts to reveal system prompt, and queries about legal/financial/electrical safety.
  - Returns a standardized safe refusal.
- **Post‑model** (`src/guardrails/moderation.py`):
  - Ensures LLM output conforms to `ConsultaRecarga` schema.
  - Detects invented facts or prohibited specifications.
  - Falls back to a safe refusal when validation fails.

## Prompt versioning
- System prompts live in `prompts/` as `system_prompt_v1.md` and `system_prompt_v2.md`.
- The README in `prompts/` contains a table of versions, changes, motivations, and expected evaluation evidence.
- Tags are XML‑based (e.g., `<identidade>`, `<escopo>`, `<seguranca>`) to make parsing deterministic.

## Evaluation pipeline
- Test cases are defined in `evals/eval_dataset.json` (session_id, input, expected_intent).
- `evals/run_evals.py`:
  1. Adds the repository root to `PYTHONPATH`.
  2. Instantiates `GoodWeChatbot`.
  3. Calls `responder` for each case.
  4. Measures latency (seconds) and token usage via `tiktoken` (`cl100k_base`).
  5. Checks if the expected intent substring appears in the response.
  6. Writes detailed results to `evals/legacy_results.json`.
- This baseline is required before refactoring to LCEL so that gains can be measured.

## Common pitfalls
- **Missing API key** – on the default cloud host, the LCEL chain uses `DeterministicChatModel`. This technical mock does not represent final real-model output.
- **PYTHONPATH** – when executing scripts from sub‑directories (e.g., `evals/`), prepend the repo root to `PYTHONPATH` (the script already does this).
- **Token limits** – the chain builder respects a configurable `max_tokens`; exceeding it will truncate the model output.
- **Intent detection in eval** – current script uses a simple substring check; more robust validation will be added later.

## Quick commands
- `python3 evals/run_evals.py` – run baseline evaluation.
- `pytest -q tests/` – run unit tests (once added).
- `git status` – verify no unintended changes before committing.
- `git add <files> && git commit -m "<message>"` – standard commit workflow.
