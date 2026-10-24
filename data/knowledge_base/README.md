# Corpus da Sprint 4

Este diretório contém apenas conteúdo do cenário **simulado** do projeto. A tarifa, o número de carregadores, a potência média e as regras de agendamento não são dados oficiais da GoodWe nem informações de um condomínio real. A revisão do workspace em 23/10/2026 não encontrou fonte adicional utilizável; o corpus não foi ampliado. Não há manual ChargeGrid/EV ChargeOps ou especificação oficial GoodWe disponível no repositório; nenhum foi inventado.

| Arquivo | Origem | Versão/data | Autoridade | Licença/permissão conhecida | Limitações |
|---|---|---|---|---|---|
| `condominio_cenario_v2.md` | Cópia de `data/conhecimento_condominio_v2.md` | v2; data original desconhecida; inventariado em 2026-10-23 | Simulado | Uso acadêmico inferido pela presença no repositório; licença e redistribuição não documentadas | Tarifa, equipamentos, horário e regras são fictícios; não representam GoodWe ou condomínio real. |
| `faq_condominio_simulado_v1.md` | Reformulação editorial do mesmo arquivo v2 | v1; 2026-10-23 | Simulado | Derivado de material do projeto; licença e redistribuição não documentadas | Não é FAQ oficial nem fonte independente; repete o cenário fictício. |

O arquivo `manifest.json` é a fonte de metadados para a ingestão: caminho, origem, versão, data, tipo, autoridade, licença/permissão conhecida, limitações e seções. Os campos de licença descrevem apenas o que é conhecido; a presença no repositório não comprova direito de redistribuição. O PDF `docs/EV_Challenge_2026_GoodWe_Sprint_03.pdf` é um enunciado acadêmico da Sprint 3, não documentação técnica GoodWe. Relatórios do projeto em `docs/` são análises secundárias e não devem ser usados como fonte primária de especificações, regras ou tarifas.

## Lacunas e entrada de novas fontes

Faltam: (1) manuais GoodWe do produto pertinente, com modelo, revisão e URL ou arquivo de origem; (2) regulamento aprovado de um condomínio identificável, com vigência e permissão de uso; (3) FAQ de carregamento publicada por autoridade identificável, com versão/data e licença ou permissão; (4) tabela tarifária aplicável, com emissor, localidade, período de vigência, unidade e permissão. Não há anexos desta conversa disponíveis para ingestão. Até obter esses materiais, os dados simulados permanecem os únicos indexados.

Para incorporar uma fonte, guardar uma cópia verificável neste diretório, registrar no `manifest.json` os campos obrigatórios de cada entrada (`path`, `document`, `source`, `origin`, `version`, `date`, `type`, `authority`, `license_or_permission`, `limitations`, `sections`) e conferir texto, seções e páginas com o comando de ingestão abaixo. Usar `desconhecido` quando versão ou data não forem informadas e descrever explicitamente essa limitação. Registrar URL e data de acesso em `origin` quando a origem for online. Manter o material simulado com `authority: simulado`; marcar documentos oficiais apenas quando a origem e a autoridade estiverem verificadas. Só depois de validar permissão e conteúdo, adicionar o documento ao manifesto e reconstruir o índice com `--reindex`.

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

O índice é persistido em `data/chroma/`, ignorado pelo Git. `CHROMA_PERSIST_DIR` permite outro diretório. Repetir `index` sobre corpus/configuração idênticos mantém a coleção e evita novos embeddings. Após alteração dos arquivos, modelo ou parâmetros, use `python3 -m src.rag.vector_store index --reindex`; o comando gera embeddings antes de substituir a coleção. O hash de versão da coleção cobre texto, metadados armazenados, modelo e parâmetros de chunking. Correções de fonte ou seção, portanto, exigem reindexação. Se a substituição falhar após a remoção, execute `--reindex` novamente. O índice é derivado do corpus versionado e pode ser reconstruído com esses comandos. Nunca grave chaves ou índices em Git.

No corpus atual, seções curtas permanecem como chunks individuais; o tamanho de 900 caracteres é apenas um teto inicial, não um tamanho alvo atingido. As contagens efetivas devem ser conferidas em `inspect` após a indexação. Chunks compostos somente de títulos são descartados.

Na coleção Chroma, `page=0` indica Markdown sem paginação; em PDFs, a página é positiva e começa em 1. A indexação inicial do corpus atual em 23/10/2026 com `nomic-embed-text` gerou 11 chunks. Repetir o comando retornou `unchanged` e manteve os 11 registros. Isso verifica persistência e ausência de duplicatas, não mede qualidade de recuperação ou resposta.
