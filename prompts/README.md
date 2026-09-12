# Versionamento de prompts

## Resultados medidos

Experimento controlado executado em 11/09/2026 com os 35 casos de
`evals/eval_dataset.json`, modelo `deterministic-offline`, temperatura `0.2` e `top_p=0.9`.
O relatório completo e os resultados por caso estão em
`evals/prompt_comparison_results.json`.

| Versão | Arquivo | Mudanças | Qualidade | Intenção | Structured output | Recusas corretas | Tokens/caso | Latência média |
|---|---|---|---:|---:|---:|---:|---:|---:|
| v1 | `system_prompt_v1.md` | Baseline textual com regras e exemplos. | 100% | 100% | 100% | 100% | 1848,43 | 15,77 ms |
| v2 | `system_prompt_v2.md` | Estrutura XML, escopo GoodWe/EV e saída JSON. | 100% | 100% | 100% | 100% | 620,43 | 18,24 ms |
| v3 | `system_prompt_v3.md` | Recusas oficiais por categoria e segurança ampliada. | 100% | 100% | 100% | 100% | 924,43 | 16,37 ms |

Qualidade é a média de acurácia de intenção, validade estruturada e recusas corretas.
Contra v1, v2 reduziu 1228 tokens por caso (66,43%) e v3 reduziu 924 (49,99%).
O dataset e o modelo offline não diferenciaram qualidade entre os prompts: todas as
versões atingiram 100%, portanto não há alegação de ganho de qualidade neste ensaio.

## Regressões observadas

- v2 aumentou a latência média em 2,47 ms contra v1.
- v3 aumentou a latência média em 0,60 ms contra v1.
- v3 consumiu 304 tokens adicionais por caso contra v2, embora tenha reduzido a latência em 1,87 ms.
- Nenhum caso individual perdeu acurácia de intenção, validade estruturada ou correção de recusa em v2 ou v3.

Latência pode oscilar entre execuções locais; os valores acima correspondem ao relatório
versionado e devem ser atualizados sempre que o experimento for reexecutado.

## Reprodução

O loader descobre automaticamente arquivos `system_prompt_vN.md` e usa a maior versão.
Uma versão pode ser fixada por `PROMPT_VERSION=v1` ou pelo argumento `prompt_version`
das fábricas em `src.chain.builder`.

```bash
PYTHONPATH=. USE_MOCK_MODEL=1 python3 evals/run_evals.py --prompt-version all
PYTHONPATH=. USE_MOCK_MODEL=1 python3 evals/run_evals.py --prompt-version v1
PROMPT_VERSION=v2 PYTHONPATH=. USE_MOCK_MODEL=1 python3 app.py
```

Alterações de comportamento devem criar uma nova versão, preservando v1, v2 e v3 para
reprodução histórica, e atualizar esta tabela com uma nova execução controlada.
