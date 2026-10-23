# Corpus da Sprint 4

Este diretório contém apenas conteúdo do cenário **simulado** do projeto. A tarifa, o número de carregadores, a potência média e as regras de agendamento não são dados oficiais da GoodWe nem informações de um condomínio real. Não há manual ChargeGrid/EV ChargeOps ou especificação oficial GoodWe disponível no repositório; nenhum foi inventado.

| Arquivo | Origem | Versão/data | Tipo | Seções |
|---|---|---|---|---|
| `condominio_cenario_v2.md` | Cópia de `data/conhecimento_condominio_v2.md` | v2; data original desconhecida, inventariado em 2026-10-23 | Regras simuladas | Tarifa, quantidade, potência média, pico, agendamento, conflitos |
| `faq_condominio_simulado_v1.md` | FAQ derivada do mesmo arquivo v2 | v1; 2026-10-23 | FAQ simulada | Tarifa, pico, reservas, quantidade/potência |

O arquivo `manifest.json` é a fonte de metadados para a ingestão: caminho, origem, versão, data, tipo, autoridade e seções. Não há licença explícita registrada para os materiais do projeto. Antes de acrescentar PDFs ou manuais externos, verificar origem legítima e direito de uso, registrar a licença/permissão e os metadados no manifesto. O PDF `docs/EV_Challenge_2026_GoodWe_Sprint_03.pdf` foi usado somente para validar a extração por página; é um enunciado acadêmico da Sprint 3 e não integra o corpus nem serve como documentação técnica GoodWe.

## Ingestão repetível

Instale `requirements.txt` e execute na raiz do projeto:

```bash
python3 -m src.rag.loader --manifest data/knowledge_base/manifest.json
```

O comando carrega e limpa os documentos, lista seções/páginas e metadados. Markdown é separado por cabeçalhos; PDFs são carregados por página com `PyMuPDFLoader`. Cada registro conserva `source`, `document`, `section`, `page`, `version`, `date`, `type` e `authority`. A numeração de página é 1-based; Markdown não possui página (`null`). Cabeçalhos dentro de PDFs não são inferidos: a seção é identificada como `Página N` até que uma estrutura de títulos confiável seja fornecida.

## Índice vetorial (fase 2)

Instale as dependências de `requirements.txt`, inicie o Ollama e obtenha o modelo com `ollama pull nomic-embed-text`. Defina `OLLAMA_BASE_URL` se o endpoint não for o local padrão; `OLLAMA_EMBED_MODEL` pode alterar o modelo, mas exige reindexação. A configuração inicial usa chunks de 900 caracteres com overlap de 135, separados por parágrafos, linhas, frases e espaços, nessa ordem. Cada chunk registra tamanho efetivo em caracteres e tokens `cl100k_base`, além de `source`, `document`, `section`, `page` (quando existe) e `chunk_id` estável. Quando o vocabulário do tiktoken não estiver disponível offline, `tokens_cl100k_base` recebe `-1`; os caracteres permanecem exatos.

```bash
python3 -m src.rag.vector_store index
python3 -m src.rag.vector_store inspect --limit 5
```

O índice é persistido em `data/chroma/`, ignorado pelo Git. `CHROMA_PERSIST_DIR` permite outro diretório. Repetir `index` sobre corpus/configuração idênticos mantém a coleção e evita novos embeddings. Após alteração dos arquivos, modelo ou parâmetros, use `python3 -m src.rag.vector_store index --reindex`; o comando gera embeddings antes de substituir a coleção. O hash de versão da coleção cobre texto dos chunks, versão declarada e modelo. Se a substituição falhar após a remoção, execute `--reindex` novamente. O índice é derivado do corpus versionado e pode ser reconstruído com esses comandos. Nunca grave chaves ou índices em Git.

No corpus atual, seções curtas permanecem como chunks individuais; o tamanho de 900 caracteres é apenas um teto inicial, não um tamanho alvo atingido. As contagens efetivas devem ser conferidas em `inspect` após a indexação. Chunks compostos somente de títulos são descartados.

Na coleção Chroma, `page=0` indica Markdown sem paginação; em PDFs, a página é positiva e começa em 1. A indexação inicial do corpus atual em 23/10/2026 com `nomic-embed-text` gerou 11 chunks. Repetir o comando retornou `unchanged` e manteve os 11 registros. Isso verifica persistência e ausência de duplicatas, não mede qualidade de recuperação ou resposta.
