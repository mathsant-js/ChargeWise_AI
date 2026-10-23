# Corpus da Sprint 4

Este diretório contém apenas conteúdo do cenário **simulado** do projeto. A tarifa, o número de carregadores, a potência média e as regras de agendamento não são dados oficiais da GoodWe nem informações de um condomínio real. Não há manual ChargeGrid/EV ChargeOps ou especificação oficial GoodWe disponível no repositório; nenhum foi inventado.

| Arquivo | Origem | Versão/data | Tipo | Seções |
|---|---|---|---|---|
| `condominio_cenario_v2.md` | Cópia de `data/conhecimento_condominio_v2.md` | v2; data original desconhecida, inventariado em 2026-10-23 | Regras simuladas | Tarifa, quantidade, potência média, pico, agendamento, conflitos |
| `faq_condominio_simulado_v1.md` | FAQ derivada do mesmo arquivo v2 | v1; 2026-10-23 | FAQ simulada | Tarifa, pico, reservas, quantidade/potência |

O arquivo `manifest.json` é a fonte de metadados para a ingestão: caminho, origem, versão, data, tipo, autoridade e seções. Não há licença explícita registrada para os materiais do projeto. Antes de acrescentar PDFs ou manuais externos, verificar origem legítima e direito de uso, registrar a licença/permissão e os metadados no manifesto. Não incluir o PDF do enunciado como documentação técnica GoodWe.

## Ingestão repetível

Instale `requirements.txt` e execute na raiz do projeto:

```bash
python3 -m src.rag.loader --manifest data/knowledge_base/manifest.json
```

O comando carrega e limpa os documentos, lista seções/páginas e metadados, sem criar embeddings ou índice (fase 2). Markdown é separado por cabeçalhos; PDFs são carregados por página com `PyMuPDFLoader`. Cada registro conserva `source`, `document`, `section`, `page`, `version`, `date`, `type` e `authority`. A numeração de página é 1-based; Markdown não possui página (`null`). Cabeçalhos dentro de PDFs não são inferidos: a seção é identificada como `Página N` até que uma estrutura de títulos confiável seja fornecida.
