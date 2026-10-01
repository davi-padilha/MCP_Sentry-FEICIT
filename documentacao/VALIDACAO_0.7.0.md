# Registro técnico — candidata 0.7.0

Execução em 30/09/2026 (logs UTC de 01/10/2026), Windows, laboratório
`C:\Users\davig\Desktop\MCP_Sentry-FEICIT`. Pacote principal: `desenvolvimento/gateway/`.
A configuração ativa de MCP não foi alterada. Este registro complementa,
sem substituir, a [validação anterior](VALIDACAO_0.6.0.md).

**Nota de limpeza:** por autorização explícita do usuário, `.lab-smoke` e seus
resultados, logs, snapshots e instalações foram excluídos. Este documento
conserva o resumo histórico dos testes; suas evidências brutas já não estão
disponíveis. O resumo e o ambiente foram mantidos. Na reorganização seguinte, o wheel 0.7.0 foi substituído pela distribuição 0.8.0; consulte VALIDACAO_0.8.0.md.
Para novas execuções, preparar novamente as instalações em `laboratorio/`.

## Implementação entregue

- Preparação genérica de scripts/módulos Python e entradas Node, com executáveis
  resolvidos e entrada local obrigatória. Declaração explícita de arquivos,
  dependências locais, configurações, variáveis e dados externos. Perfis
  Filesystem/Git e a facilidade MasterTool continuam opcionais.
- Conversão limitada de launchers npx/uvx com versão exata para instalação
  dedicada e `launch.json`. O backend executa Python/Node diretamente na cópia
  verificada; não executa npx/uvx. Instalações npm não executam scripts; a rota
  Python usa wheels e registra as dependências externas confiadas.
- Descoberta inicial e posterior do catálogo em cópia conferida, mediante
  autorização. A descoberta inicial não aprova a referência.
- Inspeção compara arquivos aprovados com a cobertura atual declarada, incluindo
  raízes desaparecidas, novas e substituídas. O dossiê registra remoções,
  adições e mudanças de cobertura, inclusive troca de `.dist-info` com versão.
  Não se apaga a referência anterior. Raízes atuais ausentes impedem aceitar
  ou executar, mas já permitem produzir evidência para revisão.
- Promoção explícita do envelope de execução, vinculada ao parecer e à versão
  exibida, separada da aceitação do código. Decisões recusam alterações durante
  a confirmação. Catálogo alterado exige nova revisão conjunta.
- Remoção de uma captura redundante durante o início: a captura da inspeção é
  reutilizada; a recaptura anterior à cópia e a conferência dos bytes copiados
  continuam obrigatórias. Teste de corrida verifica bloqueio se houver mudança
  entre inspeção e cópia.

## Testes automatizados

Comando executado com a candidata instalada no ambiente de desenvolvimento:

```powershell
& .\desenvolvimento\gateway\.venv\Scripts\python.exe -m unittest discover -s desenvolvimento/gateway/testes -q
```

Resultado: **56 testes; 55 passaram e 1 foi omitido** por falta de privilégio
de symlink no Windows. Incluem os testes existentes de transporte, negociação,
catálogo, bloqueio e aprovação; `test_general_preparation.py` acrescenta:

- substituição de `.dist-info`, mantendo a comparação e exigindo promoção do
  envelope e aceitação explícitas;
- inclusão/remoção de arquivos e cobertura;
- preparação de script Python, módulo Python e entrada Node com runtime real;
- cópia de módulo auxiliar e configuração na descoberta e execução;
- recusa de entrada original absoluta e de fallback de módulo ausente;
- separação entre código, dados e estado;
- parsers npx/uvx com versão fixa e conversão de bin npm simulada;
- mutação durante a promoção e entre inspeção e cópia;
- preparação por `launch.json` sem aprovação automática.

Fixtures, pareceres `allow` e confirmações fornecidos pelos testes são
**verificações técnicas**, não avaliações da IA ou decisões humanas do piloto.

## Servidores reais sem perfil

O runner [smoke_generic.py](../desenvolvimento/gateway/testes/smoke_generic.py) usa preparação
genérica, subprocesso físico do Sentry e protocolo stdio. Faz initialize,
tools/list, chamada normal, alteração controlada do código, chamada bloqueada,
parecer técnico/ACEITAR e nova chamada. Verifica bytes da entrada copiada e
registros de ciclo de vida: **1 início normal, 0 no bloqueio, 1 após aceitação**.
A alteração é um comentário controlado; não representa uma atualização
legítima publicada V2. O código original é restaurado ao encerrar o teste.

| Servidor / versão | Preparação e tarefa real | Arquivos protegidos |
| --- | --- | ---: |
| Memory / 2026.8.31 | materialize npx; create_entities e read_graph; entidade fictícia persistida em MEMORY_FILE_PATH externo | 3.652 |
| Git / 2026.8.18 | materialize uvx por Python/pip; git_status em repositório fictício | 12 |
| Filesystem / 2026.8.31 | instalação npm fixa já existente, launch.json genérico; leitura de arquivo fictício externo | 4.075 |

Memory foi escolhido porque não possui perfil no Sentry e permite conferir
persistência de dados mutáveis fora do código. A escrita não alterou a
integridade protegida. Essa verificação adicional não amplia a matriz do
piloto. Git confirma a conversão de console script Python; a troca de
`.dist-info` foi verificada em fixture, não com uma segunda versão publicada.

As evidências foram produzidas sob `.lab-smoke/`, com dados/configuração/estado
separados e sem configurar apps. Cada `result.json` registrou versão, hash dos
fontes do Sentry, referência, respostas, entrada da cópia e ciclo de vida.
Os diretórios de cenário também continham logs e evidências de revisão.
Esses arquivos foram excluídos na limpeza autorizada. Para repetir, materialize
novamente a versão exata e use pastas de cenário novas em `laboratorio/`:

```powershell
& .\desenvolvimento\gateway\.venv\Scripts\python.exe .\desenvolvimento/gateway/testes\smoke_generic.py --help
# Exemplo: primeiro recrie a instalação e o launch.json neste caminho.
# O diretório de cenário deve ser novo:
& .\desenvolvimento\gateway\.venv\Scripts\python.exe .\desenvolvimento/gateway/testes\smoke_generic.py `
  --scenario memory --plan .\laboratorio\instalacoes\memory\launch.json `
  --lab .\laboratorio\execucoes\memory-01
```

## Tempo completo de início e primeira chamada

Tempos em segundos da candidata, uma amostra por fase. “Pronto” termina
initialize/tools-list; “primeira chamada” inclui o início adiado do backend.
“Total” vai do lançamento do Sentry à primeira resposta de ferramenta.
Instalação, preparação, parecer e decisão estão fora dessa medida.

| Servidor / fase | Pronto | Primeira chamada | Total |
| --- | ---: | ---: | ---: |
| Filesystem normal | 0,465 | 60,783 | 61,249 |
| Filesystem bloqueado | 0,452 | 12,938 | 13,391 |
| Filesystem após aceitar | 0,456 | 60,462 | 60,919 |
| Memory normal | 0,392 | 50,281 | 50,673 |
| Memory bloqueado | 0,356 | 9,492 | 9,848 |
| Memory após aceitar | 0,363 | 50,210 | 50,573 |
| Git normal | 0,188 | 1,551 | 1,739 |
| Git após aceitar | 0,164 | 1,706 | 1,870 |

Filesystem e Memory expõem custo concreto de inspeção/cópia de milhares de
arquivos. Foi removida a captura redundante, preservando as verificações de
integridade. A medição anterior de Filesystem foi 72,402 s, mas ocorreu com
outro smoke concorrente: não permite atribuir quantitativamente a diferença
à otimização. Não são estatísticas de desempenho. O guia sugere timeout de
120 s para o piloto; medir no Codex/Claude Desktop permanece na etapa 3.

## Candidata reproduzível

Wheel: `pacote-usuario\mcp_sentry_gateway-0.7.0-py3-none-any.whl`, 56.194 bytes.
SHA-256:

```text
6cf65817fd762ff2fc24c770b60c3493f078cf42be1fe289739ead07d7de122d
```

Versão instalada: **0.7.0**. Os módulos instalados e os contidos no wheel
foram comparados byte a byte com os fontes. Hash agregado dos módulos `.py`
(nomes ordenados em UTF-8, NUL, conteúdo bruto de cada arquivo):

```text
15299823d9cec976d8856cdbeb654c4e3fe33e6b4783b8276837659d859e5aa9
```

Os três relatórios finais reais registraram esse hash antes de sua exclusão.
O wheel é a candidata
para o piloto; a versão final usada na validação deve ser fixada antes da
etapa 4, após os ajustes eventualmente encontrados na etapa 3.

## Limites e trabalho restante

Somente ferramentas MCP locais stdio, Python/Node nos formatos documentados.
Não há inferência universal de dependências, migração de todo launcher,
namespace packages na conversão automática, builds Python de fonte, HTTP,
isolamento de processo ou compatibilidade universal. Interpretadores,
sistema operacional, executável Git e dependências Python não selecionadas
continuam confiados. Notificações são consumidas; pedidos do servidor ao
client e resources/prompts não são implementados.

A comparação de atualização preserva o estado: instalar/alterar o código,
ajustar cobertura, inspecionar e revisar; promover execução se alterada;
autorizar descoberta e revisar catálogo se necessário; aceitar a versão
exibida. Não apagar estado nem reaplicar approve inicial.

Etapa 1: definir protocolo, V1/V2 exatas, alterações legítimas/adversariais,
tarefas e caminhos definitivos do laboratório. Etapa 3: instalar com instrução
específica nos clients reais, proteger permissões do estado contra escrita
do agente, testar revisão pela IA/decisão pelo operador e medir usabilidade
e tempos. Os estados deste laboratório são fixtures acessíveis à execução
de testes; não comprovam a proteção de permissões do piloto.

Referências de formato: [npm exec](https://docs.npmjs.com/cli/v11/commands/npm-exec/),
[uv tools](https://docs.astral.sh/uv/guides/tools/),
[Memory MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/memory).
