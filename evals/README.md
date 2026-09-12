# Avaliação antes/depois

`eval_dataset.json` é o único dataset canônico. O runner executa os mesmos 35 casos,
na mesma ordem, no adaptador legado e na implementação LCEL.

## Execução final real

```bash
PYTHONPATH=. python3 evals/run_evals.py --target both --mode real --overwrite
python3 evals/generate_comparison.py
```

O modo real exige `OLLAMA_API_KEY`. O runner falha antes de alterar os resultados se a
credencial estiver ausente. `--overwrite` é obrigatório quando os artefatos já existem.

## Teste técnico offline

```bash
PYTHONPATH=. python3 evals/run_evals.py --target both --mode offline --overwrite
```

Resultados offline são marcados com `technical_mock_only=true` e não devem substituir
a evidência final real. Após um teste offline, reexecute obrigatoriamente o modo real.

## Artefatos

- `legacy_results.json`: prompt v1 e fluxo livre anterior ao LCEL.
- `sprint3_results.json`: prompt v3, guardrails, memória e saída estruturada LCEL.
- `before_after.md`: tabela gerada diretamente dos dois relatórios.
- `compare_models.py`: comparação controlada de dois modelos reais, com no mínimo duas repetições.
- `model_comparison_results.json`: evidência detalhada das quatro execuções da Fase 8.
- `../docs/relatorio_modelos.md`: análise, custos, limitações e decisão do modelo principal.

Cada JSON registra timestamp UTC, Git SHA, hash do dataset, modelo, prompt, parâmetros,
modo, tokens, latência, metadados seguros do provedor e falhas individuais. Contagens do
provedor são usadas quando disponíveis; caso contrário, o relatório identifica a
estimativa `cl100k_base`.

## Resultado real atual

| Métrica | Legado | LCEL |
|---|---:|---:|
| Qualidade | 7,09/10 | 8,97/10 |
| Happy paths | 86,67% | 80,00% |
| Structured output | 0,00% | 94,29% |
| Recusas corretas | 66,67% | 100,00% |
| Encaminhamento profissional | 40,00% | 100,00% |
| Memória contextual | 66,67% | 33,33% |

O LCEL apresentou regressão em happy paths, memória e latência real do modelo. As saídas
brutas e falhas de schema que explicam esses resultados permanecem nos artefatos por
caso, sem interromper a avaliação.

## Comparação de modelos

```bash
PYTHONPATH=. .venv/bin/python evals/compare_models.py --overwrite
```

Os padrões são `gpt-oss:120b` e `gpt-oss:20b`, pois `qwen3:8b` não estava
disponível no endpoint durante a execução final. Use `--models MODELO_A MODELO_B`
para comparar outro par acessível. O comando valida a disponibilidade e exige no
mínimo duas repetições.
