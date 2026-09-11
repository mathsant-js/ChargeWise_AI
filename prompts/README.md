# Versionamento de prompts

| Versão | Arquivo | Mudanças | Motivação | Evidência esperada |
|---|---|---|---|---|
| v1 | `system_prompt_v1.md` | Prompt inicial. | Estabelecer o comportamento base. | Baseline das avaliações legadas. |
| v2 | `system_prompt_v2.md` | Escopo positivo GoodWe/EV, regras de segurança e precisão, recusa padronizada e saída JSON alinhada a `ConsultaRecarga`. | Reduzir prompt injection, instruções elétricas perigosas, dados inventados e respostas não estruturadas sem bloquear custo de recarga. | Casos unitários de escopo, validação Pydantic e moderação; comparação com o baseline. |

O carregador de prompt seleciona a maior versão disponível, atualmente v2. Alterações
de comportamento devem criar uma nova versão e uma nova linha nesta tabela, preservando
as versões anteriores para reprodução das avaliações.
