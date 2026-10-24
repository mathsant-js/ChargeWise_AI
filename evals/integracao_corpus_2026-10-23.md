# Integração e verificação do corpus — 2026-10-23

Executar na raiz do repositório, com `requirements.txt` instalado e Ollama acessível em `127.0.0.1:11434` com `nomic-embed-text` para reconstruir o índice.

## Corpus e índice

```bash
python3 -m src.rag.loader --manifest data/knowledge_base/manifest.json
python3 -m src.rag.vector_store index --reindex
python3 -m src.rag.vector_store inspect --limit 11
python3 -m evals.verify_rag_index
python3 -m src.rag.vector_store index
pytest -q tests/
```

Resultado observado: 12 seções carregadas de 2 arquivos Markdown declarados no manifesto; 11 chunks gerados (a seção inicial do primeiro arquivo contém apenas título). Nenhum PDF está no manifesto, portanto as 12 seções têm `page=None` no loader e `page=0` no Chroma. A auditoria comparou texto e metadados de cada chunk com o loader: 11 IDs únicos, 11 textos únicos, 12 seções, sem divergência de `source`, `document`, `section`, `version`, `date`, `type`, `authority`, `corpus_path`, `page` ou `characters`. Fingerprint: `a2f26ab6542240f04af18c47f88df3b372228ddddd3fee98f09d16d31e015845`. A segunda indexação retornou `unchanged` com 11 chunks. Suíte completa: 72 testes passaram.

O corpus contém somente o cenário simulado v2 e uma FAQ editorial derivada dele. A FAQ repete fatos do cenário, mas não gera chunks de texto idêntico. Não foram encontrados manuais, tarifas oficiais ou documentos reais adicionais declarados no manifesto.

## Recuperação e resposta

A busca vetorial com `k=3` para “Qual é a tarifa do cenário condominial simulado?” retornava introdução da FAQ, quantidade/potência e conflitos; o trecho de tarifa da FAQ aparecia na posição 6 e o trecho original na posição 11. Isso causou recusa indevida. O serviço agora examina todos os chunks da coleção pequena e filtra por assunto antes de selecionar citações. A pergunta “Como funcionam as reservas e a prioridade em conflitos no cenário?” era barrada pelo filtro de escopo; a expressão foi incluída.

Com Chroma e embeddings reais, um seletor determinístico que só devolve citações literais verificou:

| Pergunta | Resultado |
|---|---|
| Tarifa do cenário simulado | `R$ 0,92/kWh` com marcador `[1]`, documento e seção exibidos; `authority=simulado` |
| Tarifa oficial vigente da GoodWe | Recusa `sem_evidencia_aplicavel`, sem fontes |
| Potência nominal oficial do GoodWe GW-X | Recusa `dado_especifico_ausente`, sem fontes |

O teste de injeção em `tests/test_rag_pipeline.py` confirma que uma instrução maliciosa recuperada não é aceita como citação, enquanto uma frase factual literal no mesmo trecho pode ser usada. O serviço continua devolvendo somente texto literal presente em um chunk com ID válido, seguido por citação e fonte exibida.

Limite: uma chamada completa ao gerador local `qwen2.5:1.5b` excedeu 75 segundos (`timeout`, exit 124); não há resultado de qualidade do gerador nesta execução. Os testes de resposta acima verificam recuperação, filtragem, validação de citação e recusa com seletor determinístico, não a qualidade de seleção do modelo. A primeira tentativa de reconstrução falhou porque o sandbox não alcançava o Ollama local; com acesso ao serviço, `--reindex` terminou normalmente.
