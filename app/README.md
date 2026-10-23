# Interface web — ChargeWise AI

Execute os comandos na raiz do repositório com Python 3.10 ou superior.

## Instalação e configuração

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

O `.env` é ignorado pelo Git. O exemplo aponta para Ollama local. Instale e inicie o Ollama, depois obtenha os modelos configurados em `.env`:

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:1.5b
```

`OLLAMA_BASE_URL` configura embeddings; `OLLAMA_HOST` configura geração. Ambos devem apontar para o servidor desejado. Para serviço remoto, ajuste os dois endereços e coloque `OLLAMA_API_KEY` somente no `.env` ou no ambiente. O modelo de embeddings usado na consulta deve ser o mesmo usado na indexação. `RAG_TOP_K` controla a quantidade de trechos consultados; o padrão avaliado é 3. `RAG_PROMPT_VERSION` escolhe `v1`, `v2` ou `v3`; `v3` é a versão padrão avaliada.

## Indexação e execução

```bash
python3 -m src.rag.vector_store index
python3 -m src.rag.vector_store inspect --limit 5
python3 -m streamlit run app/app.py
```

Abra a URL local exibida pelo Streamlit. Envie uma pergunta; a interface mostra a resposta e as fontes com documento, seção e página quando houver. Recusas são destacadas. Erros de índice, conexão ou modelo são exibidos como falhas operacionais, sem criar respostas fictícias.

O índice fica em `data/chroma/` por padrão e é ignorado pelo Git. Para movê-lo, defina `CHROMA_PERSIST_DIR` antes de indexar e executar a interface. Se o corpus, a configuração de chunking ou o modelo de embeddings mudar, reconstrua com:

```bash
python3 -m src.rag.vector_store index --reindex
```

O corpus atual contém apenas material de condomínio **simulado**. Consulte `data/knowledge_base/README.md` para origem e limitações. A aplicação precisa de índice persistente e Ollama disponíveis para responder; o mock conversacional legado não é usado pelo serviço RAG.

## Verificação

```bash
pytest -q tests/test_rag_pipeline.py tests/test_rag_app.py
OLLAMA_MODEL=qwen2.5:1.5b RAG_PROMPT_VERSION=v3 python3 evals/run_rag_phase5.py \
  --mode live --top-k 3 --config-id verificacao-local --output /tmp/rag-verificacao.json
```

O segundo comando usa o índice e o Ollama reais. Escolha outro arquivo de saída se `/tmp/rag-verificacao.json` já existir. Os resultados e limites da avaliação concluída estão em `evals/relatorio_rag.md`.

## Comparação de modelos da Sprint 4

Para repetir o benchmark com dois modelos locais já baixados, mantenha o
mesmo índice, dataset, prompt e `top-k`. O executor não sobrescreve saídas:

```bash
OLLAMA_MODEL=qwen2.5:1.5b RAG_PROMPT_VERSION=v3 python3 evals/run_rag_phase5.py \
  --mode live --top-k 3 --config-id qwen-nova-rodada \
  --output /tmp/rag-qwen-nova-rodada.json
OLLAMA_MODEL=llama3.2:latest RAG_PROMPT_VERSION=v3 python3 evals/run_rag_phase5.py \
  --mode live --top-k 3 --config-id llama-nova-rodada \
  --output /tmp/rag-llama-nova-rodada.json
```

Execute em sequência se for comparar latência em uma única máquina. O
relatório `docs/relatorio_modelos.md` distingue este benchmark RAG do
comparativo conversacional da Sprint 3. As notas 0–1 exigem revisão das
respostas brutas conforme a rubrica em `evals/relatorio_rag.md`.
