# Revisão de entrega — Sprint 4

Data da inspeção: 23/10/2026. Branch local: `sprint4_rag`; commit de partida:
`c876692bd0c00e30ffdeec13faccf2a537d7328e`.

| Verificação | Resultado |
|---|---|
| Repositório remoto | `mathsant-js/ChargeWise_AI`, visibilidade pública confirmada pelo conector GitHub; permissão de leitura pública disponível. |
| Credenciais | `.env` existe apenas localmente, está ignorado por `.gitignore` e tem permissão `600`. Nenhum caminho `.env` aparece no histórico Git inspecionado. `.env.example` contém campos de exemplo. |
| Índice transitório | `data/chroma/` está ignorado; a reconstrução é documentada em `app/README.md`. |
| Histórico e arquivos grandes | Nenhum arquivo versionado acima de 1 MB no commit de partida. Os maiores são PDFs de referência e snapshots de avaliação; não há `node_modules/` ou `.venv/` versionados. |
| Equipe | `integrantes_rm_turma.txt` criado com os seis nomes, RMs e turma registrados na documentação anterior. |
| Interface e testes | Instruções de instalação, indexação e execução em `app/README.md`; `pytest -q tests/` passou com 70/70 testes em 23/10/2026. |
| Avaliação | Dataset, snapshots, rubrica e relatório RAG preservados em `evals/`; comparação RAG de modelos registrada separadamente do comparativo conversacional legado. |
| Relatório de evolução | Markdown e PDF gerados em `docs/sprint4/`; PDF A4 com 2 páginas, renderizado e inspecionado visualmente. |

O corpus segue limitado a dados condominiais simulados. O benchmark depende
de Ollama e dos modelos locais para ser repetido.

Antes da submissão remota, conferir o `git diff` final, registrar um commit e
publicar a branch desejada. A inspeção acima não equivale a um push deste
estado de trabalho.
