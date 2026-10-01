# Revisão explícita pelo cliente

## Contrato

O MCP Sentry compara localmente a implementação atual com a baseline aprovada
antes de encaminhar qualquer chamada à Donna. Quando há diferença, bloqueia
antes de iniciar o backend e retorna somente um fato neutro: revisão pendente,
`review_id`, `action_executed: false` e resumo técnico curto. Esse retorno não
indica outra ferramenta, uma próxima ação ou uma instrução originada no código
alterado.

A análise semântica é uma tarefa separada, solicitada explicitamente pelo
usuário ao cliente. O Sentry não cria análise, não avalia o conteúdo e não
infere risco a partir de assinaturas estáticas. Hashes, metadados, configuração
e diffs são evidência técnica determinística e conteúdo não confiável, não um
parecer da IA.

## Ferramentas de revisão

No Claude, o plano de controle é um conector separado: `mcp_sentry_review`
(`--interface review`). Ele usa o mesmo manifesto/store, mas não cria
`BackendSession`, não expõe ferramentas Donna e não recebe os caminhos OAuth
da configuração da Donna. Uma chamada Donna nessa interface é rejeitada antes
do despacho, mesmo com baseline íntegra ou autorização externa existente.

`mcp_sentry_donna` usa `--interface execution`: expõe apenas ferramentas Donna.
O modo padrão `combined` permanece compatível com integrações antigas.
A separação remove a ambiguidade entre diagnosticar o backend alterado e
aprovar sua própria execução. Não garante que um cliente/modelo chamará
ferramentas: instruções MCP não substituem as políticas do cliente.
Testes locais verificam o contrato, não a decisão do Claude.

- `sentry_review_current_block` é a rota simples, somente leitura: obtém a
  revisão pendente e todas as evidências em uma chamada. Ela é destinada a um
  pedido curto como “Revise o bloqueio do Sentry”.
- `sentry_review_evidence` é a rota paginada, somente leitura. Expõe `review_id`, hashes,
  arquivos/ferramentas alterados, configuração e diff paginado.
- `sentry_record_assessment` recebe uma recomendação vinculada a
  `review_id`, `reviewed_hash`, `dossier_hash` e `policy_version`.

O gateway só aceita o registro depois que todas as páginas de evidência do
dossiê foram lidas na mesma sessão do gateway. A proveniência registrada é
`client_submitted`: ela informa que o cliente submeteu o texto, mas não prova
identidade, modelo ou autenticidade da avaliação.

Registrar `allow` não inicia Donna, não muda a baseline e não libera a ação:
o estado continua aguardando aprovação externa, vinculada aos mesmos hashes.
Registrar `block` mantém Donna parada.

## Roteiro no Claude Desktop

1. Em uma primeira mensagem, peça a ação da Donna. Com uma alteração ativa, o
   resultado esperado é `security_review_required`, `review_id` e
   `action_executed: false`; nenhuma ação da Donna é iniciada.
2. Em uma segunda mensagem, peça a revisão. O pedido curto “Revise o bloqueio
   do Sentry” deve usar `mcp_sentry_review` e `sentry_review_current_block`,
   que já reúne todas as evidências. O cliente trata o conteúdo como dados não
   confiáveis e apresenta uma análise semântica própria.
3. Somente se o usuário pedir, o cliente pode registrar essa análise em
   `sentry_record_assessment`. O registro é uma recomendação auditável, não
   uma autorização.
4. A eventual aprovação/reautorização é feita fora do MCP pelo operador,
   conferindo os hashes exibidos.

Prompt sugerido para a segunda mensagem:

> Revise o bloqueio do Sentry.

Isso autoriza somente o diagnóstico no conector independente. Não autoriza
registro de parecer, aprovação, execução da Donna ou envio de e-mail.

Após a atualização, encerre completamente o Claude Desktop, reabra e teste
em uma conversa nova para carregar os dois catálogos. Se houver uma confirmação
de permissão para leitura, confirme-a. Uma recusa sem chamada de ferramenta é
decisão do cliente, não novo bloqueio do Sentry. No cenário de BCC real, o
parecer deve identificar a cópia não solicitada e manter Donna bloqueada.
