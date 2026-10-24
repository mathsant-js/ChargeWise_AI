# Fase 3 — consulta RAG

O serviço em `src/rag/pipeline.py` consulta o índice Chroma criado na fase 2. Exemplo local após indexar e disponibilizar o Ollama:

```bash
python3 -m src.rag.vector_store index
python3 - <<'PY'
from src.rag.pipeline import RAGService
print(RAGService().answer("Qual é a política de agendamento do carregador?").to_dict())
PY
```

`RAG_TOP_K` (padrão avaliado 3) configura o número de trechos; `OLLAMA_MODEL` seleciona o modelo gerador (`qwen2.5:1.5b` por padrão); `OLLAMA_HOST` e `OLLAMA_API_KEY` configuram seu endpoint. Embeddings usam `OLLAMA_BASE_URL` e `OLLAMA_EMBED_MODEL`, que devem corresponder ao índice. Sem índice ou serviço Ollama, a consulta retorna erro operacional ao chamador; não há resposta simulada.

O recuperador retorna texto, distância e metadados. O serviço aplica os guardrails de entrada, exige metadados de origem e distância até `1.0` (parâmetro `max_distance`). Antes da geração, restringe os trechos ao assunto da pergunta quando há correspondência. Solicitações de telemetria atual ou potência nominal de modelo sem documentação são recusadas. O modelo seleciona citações literais em JSON; o serviço verifica identificador, texto e ausência de instruções maliciosas antes de montar a resposta. A resposta publicada contém apenas trechos verificados, referência numerada, documento, seção e página quando disponível. Fontes também são retornadas em campos estruturados. Documentos simulados são identificados explicitamente, inclusive ao responder perguntas sobre o condomínio ou equipamento pessoais.

O limite de distância permanece hipótese de operação, sem calibração conclusiva. Os testes cobrem passagem de metadados, citação, foco do contexto, falta de evidência, bloqueio de segurança e injeção em documento. As medições reais e suas limitações estão em `evals/relatorio_rag.md`.
