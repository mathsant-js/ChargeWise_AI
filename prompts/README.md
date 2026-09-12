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
| v4 | `system_prompt_v4.md` | Política para contexto condominial delimitado, precedência de simulações e separação de fontes GoodWe. | Ver avaliação suplementar | Ver avaliação suplementar | 100% | Ver avaliação suplementar | 1579,30* | 52,22 ms* |

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
PROMPT_VERSION=v1 PYTHONPATH=. USE_MOCK_MODEL=1 python3 -m src.main
PROMPT_VERSION=v2 PYTHONPATH=. USE_MOCK_MODEL=1 python3 -m src.main
PROMPT_VERSION=v3 PYTHONPATH=. USE_MOCK_MODEL=1 python3 -m src.main
PROMPT_VERSION=v4 PYTHONPATH=. USE_MOCK_MODEL=1 python3 -m src.main
```

A avaliação canônica antes/depois usa v1 no adaptador legado e v3 no LCEL conforme
`evals/README.md`. A comparação histórica v1/v2/v3 permanece em
`evals/prompt_comparison_results.json`.

Na ausência de `PROMPT_VERSION`, o v4 é selecionado automaticamente e carrega
`data/conhecimento_condominio_v2.md`. A base fornece tarifa de R$ 0,92/kWh, quatro
carregadores, potência média de 7 kW, pico entre 18h e 21h, reservas de até quatro horas
e prioridade para a primeira reserva em caso de conflito.

## Resultado suplementar do v4

Em 12/09/2026, o v3 sem a base e o v4 com a base v2 foram executados sobre os mesmos 10
casos de `evals/condominium_eval_dataset.json`, usando o modelo determinístico offline:

| Configuração | Acertos | Structured output | Tokens totais | Latência média |
|---|---:|---:|---:|---:|
| v3 sem base | 2/10 (20%) | 100% | 12.802 | 38,62 ms |
| v4 com base v2 | 10/10 (100%) | 100% | 15.793 | 52,22 ms |

O v4 aumentou o consumo estimado em 2.991 tokens, ou 23,36%. O asterisco na tabela de
versões identifica métricas desse dataset suplementar, que não são diretamente
comparáveis aos 35 casos históricos de v1, v2 e v3. Intenção, qualidade e recusas do v4
permanecem sem medição no dataset canônico para evitar sobrescrever o baseline.

No benchmark offline de memória longa, o v4 teve 1.930 tokens efetivos de histórico,
contra 2.261 do v3, e perdeu a âncora em 8 turnos, contra 12 no v3. Ao equalizar o
orçamento para 2.261 tokens, ambos perderam a âncora em 12 turnos. O resultado atribui a
diferença aos 331 tokens adicionais do contexto v4. Consulte `evals/README.md` para o
protocolo e as limitações.

Alterações de comportamento devem criar uma nova versão, preservando v1, v2 e v3 para
reprodução histórica, e atualizar esta tabela com uma nova execução controlada.
