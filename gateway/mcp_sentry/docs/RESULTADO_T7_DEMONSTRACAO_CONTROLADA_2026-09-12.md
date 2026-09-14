# Resultado T7 — demonstração controlada

**Data:** 2026-09-12  
**Escopo:** gateway operacional em `aplicacoes/mcp_sentry/`; não produz
evidência para A/B/C1/C2/D, M2.3 ou suas baterias.  
**Estado:** execução técnica concluída e limpa; o material preservado é
somente sanitizado.

## Conclusão limitada

As duas pistas previstas foram executadas com os resultados abaixo.

- A Pista A criou um único evento sintético após prévia e duas confirmações
  humanas distintas (criação e remoção), verificou a criação e confirmou a
  ausência do mesmo evento após a remoção.
- A Pista B aplicou uma mutação perigosa inerte depois do baseline, exigiu
  revisão, leu todas as páginas do dossiê e persistiu `block` antes de qualquer
  spawn do backend.

Isto demonstra uma fronteira de integridade local para a rota exercida. Não
demonstra isolamento geral do host, segurança de produção, validação de Gmail
ou uso da interface MCP nativa do Codex.

## Pista A — Google controlado

| Item | Resultado sanitizado |
| --- | --- |
| Estado de integridade antes do efeito | `unchanged` |
| Evento | criado, verificado, removido e ausente na verificação final |
| Identificador público | SHA-256 `a5551b93ec933fb1aaa40e927ece768df9bad28d84198521b0a995c5cbcbb2da` |
| Participantes / convites | nenhum / não enviados |
| Tools Gmail | nenhuma chamada |
| Escopos efetivos | Calendar Events, Gmail Compose e Gmail Readonly; igualdade literal com a allowlist T7 |
| Token OAuth | revogado |
| Material privado | token, credencial, auditoria, mutation store e duas raízes privadas removidos |

O baseline e o envelope privados foram reconstruídos antes do efeito porque o
manifesto inicialmente não incluía o provedor Google ativo copiado pelo
gateway. O novo baseline teve hash
`e14d10a3252a01c2a53316552fd7db00633a1583725a87050904ca4d4b99fd66` e o
envelope hash
`87527ba9f927d1901d75506096718bfd5326ebcf345b2c37613099580c1b6128`.

Houve três impedimentos anteriores ao efeito externo: permissão de escrita do
sandbox para a evidência de ciclo de vida, cobertura incompleta do provedor
ativo no manifesto privado e token OAuth com `invalid_grant`. Eles foram
diagnosticados e corrigidos antes da criação do evento. Houve uma única criação
e uma única remoção reais.

## Pista B — mutação simulada

| Item | Resultado |
| --- | --- |
| Fixture | `D-DANGEROUS-BLOCK-01` |
| Mudanças no dossiê | 2, lidas em 2 páginas |
| Decisão | `block` |
| `spawn_attempts` | `0` |
| Último evento do ciclo de vida | `gateway_started` |
| Credenciais / valores de passthrough | ausentes |
| Rede / efeito externo | ausentes |

A raiz temporária da Pista B foi removida após a preservação do resumo
sanitizado.

## Cliente, configuração e limpeza

O gateway foi exercido por um cliente JSON-RPC controlado, iniciado pelo Codex
com o mesmo comando e ambiente da configuração efetiva `Donna_via_Sentry`.
Esse cliente negociou MCP, listou as tools, consultou o estado do Sentry e
encaminhou o fluxo da Donna. A interface MCP nativa do Codex não foi usada
nessa execução; essa verificação permanece separada e exigiria nova
configuração, preflight e autorização antes de qualquer acesso Google.

Depois da limpeza, a entrada efêmera `Donna_via_Sentry` foi removida da
configuração do Codex; `node_repl` permanece somente como capacidade paralela
do host. Não há processos órfãos do gateway ou da Donna.

## Fechamento local

- suíte `aplicacoes/mcp_sentry/tests`: 78 testes aprovados;
- `git diff --check`: aprovado;
- `development_sentry` alinhada a `origin/development_sentry` e sem mudanças
  pendentes;
- as únicas evidências externas remanescentes são dois resumos sanitizados,
  um por pista; as raízes temporárias das pistas A e B não permanecem.

