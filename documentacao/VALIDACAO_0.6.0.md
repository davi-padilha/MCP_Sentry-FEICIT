# Registro técnico — 30/09/2026

Registro histórico da 0.6.0. A generalização, correção de atualizações
estruturais e medições completas posteriores estão em
[VALIDACAO_0.7.0.md](VALIDACAO_0.7.0.md), a candidata atual para o piloto.

Pacote principal `desenvolvimento/gateway/`, versão de desenvolvimento 0.6.0. Instalado em
`C:\Users\davig\Desktop\MCP_Sentry-FEICIT\desenvolvimento\gateway\.venv` com Python 3.12.14.
Os módulos instalados foram comparados byte a byte com os fontes.

## Verificações

- `python -m unittest discover -s desenvolvimento/gateway/testes -q`: 43 testes, 42 passaram,
  1 ignorado porque o Windows não permitiu criar symlinks nesse ambiente.
- Notificações antes de initialize, tools/list e tools/call; resposta com ID
  errado; negociação suportada e recusa de protocolo não suportado.
- Bloqueio sem iniciar backend, liberação de um início, aprovação permanente
  vinculada ao parecer exibido e recusa se o código mudar na confirmação.
- Descoberta autorizada de catálogo em cópia verificada, aplicação sem
  aprovação automática e exigência de novo parecer sobre código e metadados.
- Pacote Python local por `-m`, módulos adicionados, exclusão de bytecode/caches
  e recusa de fallback para código instalado fora da cópia.
- Perfis exigem versão instalada exata e rejeitam gerenciadores na execução.

## Servidores reais, em instalações isoladas

| Servidor | Versão | Cobertura | Tarefa |
| --- | --- | --- | --- |
| Filesystem | 2026.8.31 | 4.075 arquivos, incluindo dependências npm locais e lockfile | `read_text_file`, conteúdo fictício conferido |
| Git | 2026.8.18 | 11 arquivos de `mcp_server_git` e `.dist-info` | `git_status`, arquivo fictício não rastreado conferido |

Em ambos, a tarefa funcionou na cópia verificada. Um comentário acrescentado
ao código causou bloqueio com zero tentativas de início. Um parecer de fixture
`allow` e a decisão local vinculada permitiram nova execução. O teste restaurou
o arquivo de código ao final. **A alteração usada é uma fixture técnica; não
substitui a atualização legítima publicada V2 do protocolo.** O parecer não
foi produzido por IA e não é resultado de avaliação semântica.

O gateway solicitou `2025-03-26` nos testes de ferramentas reais. A descoberta
inicial solicita `2025-06-18` e recusa respostas fora das duas versões
suportadas. Testes de fixtures verificaram explicitamente ambos os protocolos.

Reprodução: `desenvolvimento/gateway/testes/smoke_installed.py --help`. Dados, manifestos,
catálogos e logs foram produzidos em `.lab-smoke`, ignorada pelo Git. Na limpeza
autorizada pelo usuário, essa pasta foi excluída integralmente, incluindo
`filesystem-final`, `git-final` e as instalações. Este documento conserva o
resumo histórico; as evidências brutas não estão mais disponíveis. Novos testes
exigem reinstalação e usam a organização de `laboratorio/`. Estados graváveis
pelo agente servem apenas aos testes; **não usar como estado confiável do piloto**.

O perfil Filesystem cobre também arquivos auxiliares das dependências, sem
selecionar apenas o ponto de entrada. Uma captura fria levou 12,87 s e uma
repetida 3,84 s nesse laboratório. O cache mantém somente texto já redigido
para evidências, limitado a 32 MiB; os bytes continuam sendo lidos e seus
hashes recalculados em cada captura. O início completo exige várias capturas
e cópia; usar timeouts do client compatíveis e registrar o tempo no piloto.

## Limites e próximos critérios

Nenhuma configuração ativa de MCP foi alterada. Os testes reais usaram
`StdioGateway` diretamente, e não Codex ou Claude Desktop conectados. Faltam
o protocolo com V1/V2 publicadas, os caminhos definitivos do laboratório,
a tarefa completa em cada client real e os cenários do piloto/validação.
O suporte foi delimitado pelos perfis locais; não há resolução automática
de caches arbitrários `npx`/`uvx`, GUI ou compatibilidade universal.

A 0.6.0 é a candidata de desenvolvimento. Antes da etapa 4, fixe a distribuição
e seu hash, registre os runtimes/dependências e repita execuções afetadas por
correções posteriores. Hash do conjunto dos fontes Python desta revisão:
`253d8252c5d9cdea70e4106276871467d6e6b723e0d6e294e0c1c76af28e7ba8`
(SHA-256 da concatenação ordenada de nome UTF-8, byte zero e conteúdo de cada
`desenvolvimento/gateway/mcp_sentry_gateway/*.py`).

Referências de formato: [Filesystem oficial](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem),
[Git oficial](https://github.com/modelcontextprotocol/servers/tree/main/src/git) e
[transporte MCP stdio](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports).
