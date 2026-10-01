# Validação técnica — candidata 0.8.0

Verificação realizada em 30/09/2026, no Windows. A configuração ativa de MCP
foi preservada. Esta validação complementa a [0.7.0](VALIDACAO_0.7.0.md);
não representa o piloto em um client de IA real.

## Melhoria entregue

- `setup` integra materialização, preparação, descoberta, aprovação inicial e
  conexão para os formatos delimitados de npx/uvx, sem perfil por servidor.
- Pacote sem versão exige uma versão exata informada pelo operador; tags,
  intervalos e opções avançadas continuam na rota manual.
- Runtime e pasta nova são sugeridos; instalação requer INSTALAR. A cobertura
  vem do plano gerado e pode ser ampliada. Descoberta requer DESCOBRIR; aprovação
  e edição da configuração continuam exigindo APROVAR e SUBSTITUIR.
- Argumentos, variáveis explícitas e opções suportadas do Codex são preservados.
  npx/uvx com cwd explícito requer preparação manual; os caminhos de dados
  precisam ser absolutos. Download não equivale a execução nem aprovação.
- Instalação e estado não podem se sobrepor. Estado existente é recusado antes
  do download. Falha de instalação preserva o config.toml, mas pode deixar uma
  instalação parcial para inspeção; repetir em uma pasta nova.
- O terminal exibe até 20 hashes de arquivos, mantendo a referência completa
  no estado aprovado. Entradas Node locais incluem sugestões de node_modules
  e metadados quando presentes na raiz escolhida.
- Empacotamento declara explicitamente o pacote, excluindo a pasta de testes.

## Verificações

```powershell
& .\desenvolvimento\gateway\.venv\Scripts\python.exe -m unittest discover -s desenvolvimento/gateway/testes -q
```

Resultado: **63 testes: 62 passaram e 1 foi omitido** por falta de privilégio
para symlinks. Os sete testes novos exercitam a integração uvx sem versão,
npx via cmd /C, cancelamento, falha de instalação, tags/cwd não suportados,
estado existente e separação entre instalação e estado.

No teste npx, apenas a etapa de download npm é substituída por uma fixture;
a materialização, descoberta e execução Node são reais. Uma chamada confirma
execução fora da instalação original; alteração posterior bloqueia antes do
início do backend. No teste uvx, a materialização é simulada com uma fixture
Python; descoberta, aprovação e execução são reais. Estes testes não comprovam
um novo download de pacote publicado nem revisão pela IA.

O wheel foi instalado no ambiente de desenvolvimento. A CLI instalada passou
pelo fluxo uvx até o cancelamento anterior ao download, com TOML descartável;
a configuração permaneceu intacta. Todos os módulos do wheel foram comparados
byte a byte com os fontes. Não contém testes, caches ou o ambiente virtual.
Nenhuma entrada ativa de MCP aponta para a pasta cliente removida.

## Distribuição e organização

- Usuário final: [pacote-usuario/README.md](../pacote-usuario/README.md) e wheel 0.8.0.
- Desenvolvimento: [desenvolvimento/gateway/](../desenvolvimento/gateway/README.md),
  com código, empacotamento, ambiente local e testes.
- Guias e registros: `documentacao/`. Instalações e execuções descartáveis:
  [laboratorio/](../laboratorio/README.md). Protótipo anterior: `prototipo-feicit/`.
- Wheel anterior e saídas temporárias de build removidos após a verificação.

SHA-256 do wheel `mcp_sentry_gateway-0.8.0-py3-none-any.whl`:

```text
dd9e9b0ef59f2349ab0a90d42345163356d00c4546366d92026860e682fa4ddb
```

Hash dos módulos-fonte (nome, byte zero e conteúdo, ordenados por nome):

```text
eae6d793f58d10baa0ee54beb0ab3e7ecc31ef7b561e9b3a1838af67ef0834aa
```

## Próximas etapas

Etapa 2 encerrada por enquanto. Etapa 1 define protocolo, V1/V2, tarefas e
caminhos; etapa 3 valida conexão, revisão pela IA, decisão humana, permissões
do estado e tempos nos clients reais; etapa 4 executa a matriz. Etapa 5 segue
em paralelo para explicação e materiais. Não foram executadas nesta rodada.
