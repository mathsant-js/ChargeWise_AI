# Avaliação Antes/Depois

Dataset: `evals/eval_dataset.json` (`703d3d7abbfb3aaa4f96caffa7941e880297db54131eb70640a39035241c1959`)
Modo: `real` | Modelo: `gpt-oss:120b`
Legado: `system_prompt_v1.md` em 2026-09-12T00:23:31.221795+00:00
LCEL: `system_prompt_v3.md` em 2026-09-12T00:26:51.600575+00:00

| Métrica | Antes (legado) | Depois (LCEL) | Delta |
|---|---:|---:|---:|
| Qualidade (0-10) | 7.09 | 8.97 | 1.88 |
| Happy paths | 86.67% | 80.00% | -6.67% |
| Structured output | 0.00% | 94.29% | 94.29% |
| Recusas corretas | 66.67% | 100.00% | 33.33% |
| Encaminhamento profissional | 40.00% | 100.00% | 60.00% |
| Memória contextual | 66.67% | 33.33% | -33.34% |
| Tokens por chamada | 1720.80 | 1583.11 | -137.69 |
| Latência real do modelo | 801.48 ms | 1388.56 ms | 587.08 ms |

Valores negativos em tokens ou latência representam redução. O resultado de memória considera apenas turnos que exigem recuperação de contexto anterior.
