# Relatório de comparação de modelos

## Resumo executivo

Foram executados dois modelos reais no endpoint Ollama Cloud, com duas repetições completas por modelo e 35 casos por repetição. O `gpt-oss:120b` é o modelo principal recomendado: alcançou qualidade média de **9,52/10**, contra **8,37/10** do `gpt-oss:20b`, e também venceu em acurácia de intenção, saída estruturada, recusas, tokens e latência.

O comparativo originalmente sugerido, `qwen3:8b`, não estava disponível na listagem autenticada do endpoint em 12/09/2026 UTC. Para garantir duas execuções reais, foi usado `gpt-oss:20b`, disponível no mesmo endpoint. O snapshot integral dos modelos acessíveis está preservado em `evals/model_comparison_results.json`.

## Método controlado

| Controle | Valor |
|---|---|
| Provedor/endpoint | Ollama Cloud, `https://ollama.com` |
| Implementação | LCEL com guardrails e memória |
| Dataset | `evals/eval_dataset.json`, 35 casos |
| Hash SHA-256 do dataset | `703d3d7abbfb3aaa4f96caffa7941e880297db54131eb70640a39035241c1959` |
| Prompt | `prompts/system_prompt_v3.md` + instruções do parser Pydantic |
| Hash SHA-256 do prompt completo | `7116ced68b5c8b0532aa03b0014c5cdf397bd2dfe0253b183c6e09e8939e1a1d` |
| Temperatura | `0.2` |
| Top-p | `0.9` |
| Máximo de tokens de saída | `500` |
| Limite da memória | `4096` tokens |
| Repetições | 2 por modelo, com memória reiniciada |
| Total | 4 execuções, 140 casos, 76 chamadas ao modelo |

O dataset contém 15 casos de recusa esperada. Nas execuções registradas, um follow-up contextual adicional também foi bloqueado pelo guardrail anterior ao modelo, totalizando 16 bloqueios e 19 chamadas ao modelo em cada repetição de 35 casos. Esse comportamento foi idêntico para os dois modelos e evita atribuir custo ou latência do LLM às respostas determinísticas.

## Resultados agregados

Médias das duas repetições:

| Métrica | `gpt-oss:120b` | `gpt-oss:20b` | Melhor |
|---|---:|---:|---|
| Qualidade média (0-10) | **9,52** | 8,37 | 120b |
| Acurácia de intenção | **91,43%** | 77,14% | 120b |
| Structured output válido | **98,57%** | 87,15% | 120b |
| Recusas corretas | **100,00%** | 96,67% | 120b |
| Encaminhamento profissional | 100,00% | 100,00% | Empate |
| Memória contextual (execução real anterior à correção) | 33,33% | 33,33% | Empate |
| Relevância em happy/edge cases | **96,67%** | 70,00% | 120b |
| Tokens por chamada do modelo | **1.566,93** | 1.615,98 | 120b |
| Latência média do modelo | **1.247,73 ms** | 3.381,32 ms | 120b |
| Latência média ponta a ponta | **821,83 ms** | 1.988,48 ms | 120b |
| Falhas de execução, nas duas rodadas | 0 | 0 | Empate |

A latência ponta a ponta é menor que a latência média das chamadas porque inclui os 16 bloqueios locais, quase imediatos, entre os 35 casos. A comparação apropriada de desempenho do provedor é a coluna de latência do modelo.

## Repetições e variabilidade

| Modelo | Repetição | Qualidade | Intenção | Structured output | Recusas | Memória | Tokens/chamada | Latência modelo |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `gpt-oss:120b` | 1 | 9,54 | 91,43% | 97,14% | 100,00% | 33,33% | 1.564,53 | 1.190,64 ms |
| `gpt-oss:120b` | 2 | 9,49 | 91,43% | 100,00% | 100,00% | 33,33% | 1.569,32 | 1.304,81 ms |
| `gpt-oss:20b` | 1 | 7,94 | 71,43% | 82,86% | 93,33% | 33,33% | 1.621,00 | 3.325,66 ms |
| `gpt-oss:20b` | 2 | 8,80 | 82,86% | 91,43% | 100,00% | 33,33% | 1.610,95 | 3.436,97 ms |

O 120b variou somente 0,05 ponto de qualidade e não variou em intenção, recusas ou memória. O 20b variou 0,86 ponto, 11,43 pontos percentuais em intenção e 8,57 pontos percentuais em structured output. Com `temperature=0.2`, o 120b mostrou comportamento substancialmente mais estável.

## Definição das métricas

- **Qualidade**: escore determinístico por caso. Casos permitidos pontuam relevância, intenção, ausência de erro e schema; casos bloqueados pontuam recusa oficial, ausência de erro e encaminhamento profissional quando aplicável.
- **Intenção**: igualdade exata entre `output.intencao` e `expected_intent` nos 35 casos.
- **Structured output**: saída original do modelo validada pelo schema `ConsultaRecarga`; fallback seguro não mascara falha de parsing.
- **Recusas**: correspondência com a recusa oficial definida pelo guardrail nos 15 casos de recusa esperada; o bloqueio adicional observado era um follow-up de memória.
- **Memória**: presença de todos os `memory_keywords` esperados nos três turnos de recuperação contextual avaliáveis. Os números das tabelas são o snapshot real anterior à correção do guardrail.
- **Tokens**: contagem reportada pelo provedor nas 19 chamadas; recusas locais têm zero token de modelo.
- **Latência**: duração do provedor quando disponível, com relógio monotônico local como fallback.

## Custo e disponibilidade

Preços consultados em [Ollama Pricing](https://ollama.com/pricing) em 12/09/2026, em USD por 1 milhão de tokens:

| Modelo | Entrada | Entrada em cache | Saída | Custo estimado por repetição |
|---|---:|---:|---:|---:|
| `gpt-oss:120b` | US$ 0,15 | US$ 0,014 | US$ 0,60 | **US$ 0,00706** |
| `gpt-oss:20b` | US$ 0,07 | US$ 0,035 | US$ 0,30 | **US$ 0,00370** |

A estimativa usa a média observada por repetição e tarifa cheia de entrada, sem presumir desconto de cache: 24.011 tokens de entrada e 5.760,5 de saída no 120b; 23.944,5 de entrada e 6.759 de saída no 20b. As duas repetições custariam aproximadamente US$ 0,01412 e US$ 0,00741, respectivamente. Créditos incluídos no plano podem fazer o desembolso marginal ser zero, mas não eliminam o consumo econômico dos créditos.

O 20b custa aproximadamente 47,5% menos por repetição. Essa economia não compensou a perda de 1,15 ponto de qualidade, a queda de 14,29 pontos percentuais em intenção, a queda de 11,42 pontos em structured output nem sua latência 2,71 vezes maior neste endpoint.

Disponibilidade e limitações observadas:

- `gpt-oss:120b` e `gpt-oss:20b` estavam acessíveis e foram realmente chamados.
- `qwen3:8b` não constava na listagem autenticada; apenas `qwen3.5:397b` da família Qwen estava exposto.
- A disponibilidade é um snapshot do contrato/endpoint e pode mudar.
- Preços também podem mudar; o link e a data de consulta tornam a estimativa auditável.
- A medição tem apenas duas repetições e 35 casos, adequada ao aceite desta fase, mas insuficiente para intervalos estatísticos robustos.
- A memória permaneceu em 33,33% nos dois modelos durante as execuções reais originais. A investigação posterior mostrou que dois follow-ups eram bloqueados pelo guardrail antes da chamada ao modelo, e não perdidos pelo histórico.

### Evolução da memória contextual

| Etapa | Resultado | Evidência |
|---|---:|---|
| Sprint 01 | Não implementada | Fase de exploração e planejamento |
| Sprint 02 | 66,67% automatizado | 3/3 recuperações semanticamente corretas; um falso negativo por hífen Unicode. O único cenário manual também foi aprovado |
| Sprint 03, execução real inicial | 33,33% | Dois follow-ups pronominais bloqueados antes do modelo |
| Sprint 03, após correção | **100,00% offline** | 3/3 recuperações; 100% chegaram ao modelo e 100% receberam histórico |

A correção tornou o guardrail sensível a referências contextuais curtas, como “dele”, “ela” e “disso”, e normalizou hífens e espaços Unicode na métrica. Perguntas completas fora do domínio continuam bloqueadas. O resultado pós-correção é uma validação técnica determinística; as tabelas de comparação entre `gpt-oss:120b` e `gpt-oss:20b` não foram alteradas sem uma nova execução autenticada.
- Latência de nuvem depende de carga, região e fila do plano; estes números representam esta janela de execução, não um SLA.

## Decisão

O modelo principal escolhido é **`gpt-oss:120b`**. Ele venceu seis dos sete critérios discriminantes, empatou em memória e encaminhamento profissional, teve menor consumo de tokens e foi 2,71 vezes mais rápido nas chamadas reais. Também apresentou menor variabilidade entre repetições. O `gpt-oss:20b` fica como opção de contingência de menor preço quando a redução de custo for mais importante que qualidade e confiabilidade estrutural.

## Reprodução

Com dependências instaladas e `OLLAMA_API_KEY` configurada no `.env`:

```bash
PYTHONPATH=. .venv/bin/python evals/compare_models.py --overwrite
```

Para selecionar outros dois modelos realmente listados no endpoint:

```bash
PYTHONPATH=. .venv/bin/python evals/compare_models.py \
  --models gpt-oss:120b qwen3.5:397b \
  --repetitions 2 \
  --output evals/model_comparison_results.json \
  --overwrite
```

O runner rejeita menos de duas repetições e modelos ausentes antes da avaliação. O artefato `evals/model_comparison_results.json` contém metadados, hashes, parâmetros, snapshot de modelos disponíveis, saídas brutas, resultados por caso e agregados usados neste relatório.
