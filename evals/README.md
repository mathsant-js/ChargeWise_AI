# Avaliação antes/depois

`eval_dataset.json` é o único dataset canônico. O runner executa os mesmos 35 casos,
na mesma ordem, no adaptador legado e na implementação LCEL.

O comando `python3 evals/run_evals.py` verifica os dois fluxos em modo offline sem
sobrescrever os artefatos versionados. Os modos abaixo devem ser usados quando a intenção
for atualizar resultados.

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
- `condominium_eval_dataset.json`: casos suplementares da base condominial, fora do baseline canônico.
- `condominium_results.json`: resultado técnico offline do prompt v4 com a base v2.
- `condominium_v3_results.json`: controle offline do prompt v3 sem a base condominial.
- `memory_v3_v4_comparison.json`: comparação pareada de conversas longas em produção e com memória equalizada.

Os relatórios canônicos registram timestamp UTC, Git SHA, hash do dataset, modelo,
prompt, parâmetros, tokens, latência e metadados seguros do provedor. A avaliação
suplementar também registra hashes do contexto completo, da base e da implementação,
além de indicar quando foi executada sobre uma árvore de trabalho ainda não commitada.

## Avaliação suplementar do condomínio

Esta avaliação não altera os 35 casos nem os resultados históricos da Sprint 3:

```bash
PYTHONPATH=. python3 evals/run_condominium_evals.py --mode offline --prompt-version v3 --overwrite
PYTHONPATH=. python3 evals/run_condominium_evals.py --mode offline --prompt-version v4 --overwrite
```

Ela valida fatos, cálculo com tarifa padrão, precedência de simulação, structured output
e proteção contra alteração da base. O resultado é técnico e usa o modelo determinístico;
não substitui uma execução real com o endpoint Ollama.

O v4 avaliado é `prompts/system_prompt_v4.md`, carregado junto de
`data/conhecimento_condominio_v2.md`. A base contém tarifa de R$ 0,92/kWh, quatro
carregadores, potência média de 7 kW, pico das 18h às 21h, reservas de até quatro horas
por morador e prioridade para a primeira reserva em conflitos.

No controle offline atual, o v3 sem conhecimento acertou 2/10 casos e o v4 com a base
acertou 10/10. O v4 consumiu 15.793 tokens estimados contra 12.802 do v3, aumento de
23,36%, considerando entrada e saída. A latência offline é apenas diagnóstica e não deve
ser extrapolada para o modelo real.

| Métrica | v3 sem base | v4 com base v2 |
|---|---:|---:|
| Casos aprovados | 2/10 | 10/10 |
| Taxa de sucesso | 20% | 100% |
| Structured output válido | 100% | 100% |
| Tokens de entrada | 12.242 | 15.221 |
| Tokens de saída | 560 | 572 |
| Tokens totais | 12.802 | 15.793 |
| Latência média offline | 38,62 ms | 52,22 ms |

Para repetir com o modelo configurado em `OLLAMA_MODEL`, use `--mode real`. A execução
falha antes de escrever o relatório quando `OLLAMA_API_KEY` não está disponível.

## Comparação de memória longa

```bash
PYTHONPATH=. python3 evals/compare_memory_versions.py
```

O benchmark repete exatamente a mesma conversa para v3 e v4, com probes após 4, 8,
12, 16 e 24 turnos de preenchimento. No regime de produção, ambos usam janela total de
4096 tokens. No regime equalizado, o v4 usa 4427 tokens totais para compensar os 331
tokens fixos adicionais do prompt e da base.

| Regime | Versão | Memória efetiva | Recall transmitido | Recall da resposta | Primeira perda da âncora |
|---|---|---:|---:|---:|---:|
| Produção | v3 | 2261 | 55% | 40% | 12 turnos |
| Produção | v4 | 1930 | 40% | 20% | 8 turnos |
| Equalizado | v3 | 2261 | 55% | 40% | 12 turnos |
| Equalizado | v4 | 2261 | 55% | 40% | 12 turnos |

O v4 piora a retenção longa sob a janela atual porque reduz o orçamento de memória em
14,64%. Com orçamento efetivo igual, não há diferença observada. Esses resultados usam
o modelo determinístico e medem o mecanismo local; uma comparação com o modelo real
continua necessária para avaliar recuperação semântica em produção.

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
