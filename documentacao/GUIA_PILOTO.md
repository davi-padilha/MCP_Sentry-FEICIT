# Guia — candidata 0.8.0 para o piloto

Código principal: `C:\Users\davig\Desktop\MCP_Sentry-FEICIT\desenvolvimento\gateway`.
Instalação de desenvolvimento criada em `desenvolvimento\gateway\.venv`; não altera o MCP
ativo. No PowerShell, a partir da raiz deste repositório:

```powershell
& .\desenvolvimento\gateway\.venv\Scripts\python.exe -m pip install .\desenvolvimento\gateway
& .\desenvolvimento\gateway\.venv\Scripts\mcp-sentry.exe --help
```

Em outra máquina, crie antes esse ambiente com Python 3.11+.
Para instalar a candidata fixa, use o wheel
`pacote-usuario\mcp_sentry_gateway-0.8.0-py3-none-any.whl` em vez de `desenvolvimento/gateway`.
Confira seu SHA-256 com `Get-FileHash -Algorithm SHA256 CAMINHO_DO_WHEEL`;
o valor e o resumo histórico dos testes estão no [registro 0.8.0](VALIDACAO_0.8.0.md).
Use caminhos absolutos para executáveis, manifesto, estado e dados.
O estado de um piloto real precisa ficar fora de **todas** as pastas em que
o agente pode escrever, com controle de acesso pelo operador.
`laboratorio/` é uma área de trabalho gravável pelo agente, não uma configuração
segura para o estado confiável do piloto. Veja a organização em
[laboratorio/README.md](../laboratorio/README.md). As instalações e evidências
brutas anteriores de `.lab-smoke` foram excluídas na limpeza autorizada; novos
testes exigem preparar novamente as instalações e os planos de execução.

## Rota assistida recomendada no Codex

Para uma entrada direta existente Python/Node ou npx/uvx suportada, execute:

```powershell
& .\desenvolvimento\gateway\.venv\Scripts\mcp-sentry.exe setup
```

Para npx/uvx, o assistente reúne materialização, preparação, aprovação e conexão.
Ele pergunta a versão exata quando ausente, runtime e pasta nova, depois requer
INSTALAR, DESCOBRIR, APROVAR e SUBSTITUIR. Não use a configuração ativa para um
smoke test: `--codex-config` aceita um TOML de teste e `--state-root` uma área separada.
O uso no client real continua pendente da etapa 3. Para opções avançadas, outro
client ou npx/uvx com cwd explícito, use a rota manual abaixo.

## Preparação genérica, sem perfil de servidor

`prepare-server` aceita script Python `.py`, `python -m módulo` (arquivo ou
pacote com `__main__.py`) e Node com entrada `.js`, `.mjs` ou `.cjs`. Resolve
o executável, torna a entrada relativa à cópia e exige cobertura do ponto de
entrada. Módulos Python precisam existir na pasta protegida: não há busca
silenciosa do ponto de entrada no ambiente instalado. Perfis são opcionais.

Use vários `--inspect-root` para declarar arquivos, módulos, dependências
locais e configurações. Diretórios são recursivos, incluindo arquivos novos.
Não há inferência universal de importações ou arquivos abertos pelo servidor.
Dependências Python não selecionadas permanecem confiadas no interpretador.
Para Node instalado, inclua `node_modules`, `package.json` e lockfile.

Exemplo genérico (variáveis são caminhos absolutos; crie a pasta de configuração):

```powershell
$sentry = ".\desenvolvimento\gateway\.venv\Scripts\mcp-sentry.exe"
& $sentry prepare-server --name exemplo `
  --project-root $codigo --inspect-root server.py --inspect-root pacote_local `
  --inspect-root config.json --data-root $dados `
  --manifest $manifesto --store $estado --fragment $trecho `
  -- $pythonDoServidor "$codigo\server.py" "CAMINHO_ABSOLUTO_DOS_DADOS"
```

Para módulo, use `-- $pythonDoServidor -m meu_pacote`; para Node,
`-- $node "$codigo\dist\index.js"`. `--cwd` é relativo ao código.
`--runtime-path PYTHONPATH=.` aponta uma variável para a raiz da cópia;
`--passthrough-name NOME` repassa o ambiente sem guardar valores.
`--data-root` verifica que código, dados e estado não contêm uns aos outros.
Argumentos/variáveis com dados devem usar caminhos absolutos externos; o
Sentry não conhece a semântica dos argumentos de cada servidor.
`DESCOBRIR` autoriza consultar `tools/list` em uma cópia conferida byte a byte.
A preparação não aprova código nem modifica o client.

## Converter npx/uvx para instalação fixa

`materialize` instala em uma pasta nova e produz `launch.json`, sem iniciar
o servidor. Exige `INSTALAR`; a descoberta exige confirmação separada.

```powershell
& $sentry materialize --install-root $instalacao --runtime $node `
  -- npx -y @escopo/pacote@1.2.3
& $sentry prepare-server --plan "$instalacao\launch.json" --name exemplo `
  --manifest $manifesto --store $estado --fragment $trecho
```

Aceita `npx --package pacote@1.2.3 binario`, wrapper simples `cmd /c npx ...`
e `--version 1.2.3` para launcher sem versão. Lê `bin`, confere nome/versão,
lança Node diretamente e protege dependências npm e lockfile. Usa
`--ignore-scripts`; instalações que precisam desses scripts são manuais.

Para Python, substitua por `--runtime $python -- uvx distribuicao==1.2.3`,
ou `-- uvx --from distribuicao==1.2.3 comando_mcp` (`@1.2.3` também é aceito).
Cria venv por Python/pip, sem exigir uv instalado. Consulta metadados sem
importar a distribuição e resolve o console script `módulo:função`. Protege
arquivos da distribuição e um wrapper que recusa entrada ausente antes de
importar. Outras distribuições continuam confiadas; `dependencies.txt`
registra versões. Mantenha o ambiente fixo.

Tags, ranges, URLs, extras, shell composto e opções avançadas são recusados.
A rota automática Python exige wheels e pacotes comuns com `__init__.py`.
Entry points diferentes, namespace packages e builds de fonte usam o procedimento
manual: instale a versão em ambiente dedicado, localize o script/módulo e
arquivos necessários e use `prepare-server`. Nunca use gerenciador como backend.

## Facilidades opcionais para servidores conhecidos

Ainda não há protocolo V1/V2 nem caminho definitivo do laboratório.
As versões abaixo são versões exatas usadas nos testes técnicos de integração;
a atualização legítima publicada V2 deve ser escolhida no protocolo.
Organize código, dados fictícios, configuração/estado e evidências em pastas
separadas. O perfil rejeita dados dentro do código ou o código dentro dos dados.

**Filesystem:** transforme a instalação usual por `npx` em uma instalação
local fixa. No diretório destinado ao código, use:

```powershell
npm.cmd install --save-exact --ignore-scripts @modelcontextprotocol/server-filesystem@2026.8.31
```

Esse diretório é `--project-root`; deve conter `package-lock.json` e
`node_modules\@modelcontextprotocol\server-filesystem\dist\index.js`.
O perfil protege `node_modules` completo, o lockfile e `package.json` quando
presente. Inclui módulos JS, JSON e dependências transitivas locais. Não usa
`npx`, rede ou busca de pacote na execução protegida. O Node instalado e o
sistema operacional continuam confiados. Uma instalação grande tem custo de
inspeção e cópia maior; para o piloto, comece com `startup_timeout_sec = 120`
e `tool_timeout_sec = 120` na entrada de execução do Codex e meça o tempo real.
No laboratório, 4.075 arquivos levaram 12,87 s na captura fria e 3,84 s na
repetida em um mesmo processo. Esse valor não inclui todo o início do gateway.
Na 0.7.0, a medição completa por cliente técnico stdio, em um processo novo,
foi 0,465 s até initialize/tools-list e 60,783 s para a primeira chamada:
61,249 s do lançamento do Sentry ao primeiro resultado. Após aprovação,
60,919 s. O início do backend é adiado até a primeira ferramenta. Esses tempos
incluem inspeção e cópia, mas não instalação nem avaliação pela IA.
A medição no Codex/Claude Desktop continua pertencendo ao piloto.

**Git:** para a instalação usual por `uvx`, materialize primeiro um ambiente
fixo: `uv venv CAMINHO_DO_ENV` e
`uv pip install --python CAMINHO_DO_ENV\Scripts\python.exe mcp-server-git==2026.8.18`.
Alternativa: `python -m venv CAMINHO_DO_ENV` e depois
`CAMINHO_DO_ENV\Scripts\python.exe -m pip install mcp-server-git==2026.8.18`.
O perfil recebe `--project-root CAMINHO_DO_ENV\Lib\site-packages` e esse Python
como `--runtime`. Copia apenas `mcp_server_git` e o `.dist-info` correspondente;
executa `python -B -m mcp_server_git` a partir da cópia, sem `uvx`.
Python, SDK MCP, GitPython, demais dependências do ambiente e o executável Git
continuam externos e confiados. Registre `pip freeze` como evidência e mantenha
esse ambiente fixo. Configure `GIT_PYTHON_GIT_EXECUTABLE` com caminho absoluto;
o perfil repassa essa variável e `PATH` para os subprocessos Git.

Prepare cada um pelo comando abaixo, substituindo os caminhos e o perfil.
Crie previamente a pasta `config`, fora do código. Confira o código antes de
digitar `DESCOBRIR`: a descoberta inicial inicia uma cópia conferida uma vez.

```powershell
& .\desenvolvimento\gateway\.venv\Scripts\mcp-sentry.exe prepare-profile `
  --profile filesystem --version 2026.8.31 --name filesystem `
  --runtime "C:\Program Files\nodejs\node.exe" `
  --project-root "CAMINHO_DO_CODIGO" --data-root "CAMINHO_DOS_DADOS" `
  --manifest "CAMINHO_CONFIG\manifest.json" `
  --store "CAMINHO_ESTADO" --fragment "CAMINHO_CONFIG\codex.toml"
```

Para Git, troque perfil, versão, runtime e pasta de instalação. `--data-root`
deve apontar para um repositório Git. Os gerenciadores de pacotes são rejeitados
como comando de backend, inclusive na preparação manual. A conversão genérica
cria instalações novas, sem importar caches arbitrários ou migrar todo launcher.
MasterTool mantém sua facilidade opcional no `setup`.

Caches, `.git`, `.venv`, `venv`, `.pytest_cache`, `.cache`, `__pycache__` e
bytecode Python são excluídos. As pastas selecionadas continuam sendo
inspecionadas recursivamente: módulos novos também são detectados. Arquivos
`.env` e nomes usuais de credenciais causam recusa; mantenha credenciais,
dados mutáveis e logs fora da seleção. Acrescente configurações locais
necessárias em `inspect_roots` no manifesto; não selecione o ambiente inteiro.

## Aprovar e conectar

Confira o manifesto, arquivos e catálogo descoberto. Como operador, use
`approve --manifest CAMINHO --store CAMINHO` e depois `doctor` com os mesmos
argumentos. Isso aprova a referência inicial; não é aprovação automática da IA.

No **Codex**, o fragmento `codex.toml` tem a entrada de execução e
`mcp_sentry_review_NOME`. Sua instalação só deve ser aplicada na etapa do
piloto, com instrução específica. Desative a rota direta e reconecte o client.
Para servidores Python locais, o assistente `setup` também está disponível;
ele pede autorização antes de substituir a configuração.

No **Claude Desktop**, crie as duas entradas em `mcpServers`, com nomes
`NOME` e `mcp_sentry_review_NOME`. Em ambas, `command` é o Python absoluto do
Sentry. Os `args` são `-m`, `mcp_sentry_gateway.gateway`, `--interface`,
`execution` ou `review`, `--manifest`, caminho, `--store`, caminho.
Variáveis necessárias vão apenas no `env` da execução. Reconecte para recarregar
o catálogo. A configuração JSON completa está no README.

Codex e Claude Desktop são os clients previstos. As conexões em apps reais
ainda precisam ser verificadas no piloto; os testes desta etapa usam o gateway
diretamente, sem editar suas configurações.

## Bloqueio, revisão e decisão

1. Uma alteração bloqueia a ferramenta antes de iniciar o servidor. A resposta
   informa a interface de revisão gerada para o servidor. Solicite à IA a revisão
   nessa interface; peça separadamente o registro do parecer.
2. No terminal do **operador**, execute
   `mcp-sentry review-update --action once` ou `--action accept`. O comando
   lista servidores no estado padrão `%LOCALAPPDATA%\MCP-Sentry`; use
   `--state-root` para outro local ou informe `--manifest` e `--store` juntos.
3. Leia o parecer e os arquivos alterados. Digite `AUTORIZAR` para um início
   ou `ACEITAR` para a referência permanente. O comando exige parecer `allow`
   vigente e reutiliza internamente os hashes da revisão exibida. Mudança
   durante a decisão é recusada. Reconecte o client depois da aprovação.

Se o catálogo mudou, após a revisão do código execute
`mcp-sentry review-update --action catalog`. `DESCOBRIR` autoriza iniciar
**uma cópia verificada da versão revisada**, apenas para consultar o catálogo.
Confira descrições e esquemas; `APLICAR_CATALOGO` grava-os no manifesto, sem
aprovar a versão. A proposta fica em `catalogo-proposto.json` no estado. Peça
nova revisão do dossiê conjunto (código e metadados), registre novo parecer e
então use `--action accept`. Se o catálogo não mudar, o manifesto e o parecer
existente são preservados; a versão de código continua dependendo de decisão.
Cancelar antes de `DESCOBRIR` não aprova nem inicia a descoberta.

Mudanças no comando, nas raízes, em `cwd` ou variáveis exigem promoção separada
do envelope pelo operador (`review-update --action envelope`), após conferir
a configuração e digitar `PROMOVER`. É vinculada à versão exibida e não aprova
o código. Não ofereça comandos de aprovação ao agente. O estado confiável precisa
estar protegido por permissões do sistema; a confirmação textual não autentica
o operador.

## Testes e limites

Uma atualização preserva manifesto, estado e snapshot aprovado. Encerre a
conexão anterior, substitua o código e ajuste `inspect_roots` se houver troca
de `.dist-info` ou cobertura. `inspect` compara a seleção atual com os arquivos
aprovados, produzindo remoções, adições e alterações. O campo `coverage` mostra
raízes anteriores/atuais/ausentes; uma raiz desaparecida já gera um dossiê.
Raízes atuais ausentes impedem aceitar ou iniciar: declare a cobertura nova.
Após parecer `allow`, promova o envelope se necessário, descubra/revise novo
catálogo se necessário e aceite a versão. Não apague o estado nem execute
`approve` de novo para uma atualização.

`desenvolvimento\gateway\.venv\Scripts\python.exe -m unittest discover -s desenvolvimento/gateway/testes -v`
verifica uso, bloqueio, decisão vinculada, catálogo, módulos e notificações.
`desenvolvimento/gateway/testes\smoke_installed.py --help` descreve o teste opcional dos
servidores reais instalados, com dados e estado descartáveis.
`desenvolvimento/gateway/testes\smoke_generic.py --help` descreve a verificação genérica de
Memory, Git e Filesystem, sem perfil. Pareceres e confirmações desse runner
são fixtures técnicas; não substituem a avaliação da IA e do operador no piloto.

Somente ferramentas via stdio. Protocolos suportados: `2025-03-26` e
`2025-06-18`. Notificações intercaladas são consumidas sem confundi-las com
respostas; não são encaminhadas ao client. Pedidos do servidor ao client
(roots, sampling, elicitation) não são implementados; o gateway anuncia
capacidades vazias. Mudança dinâmica de catálogo permanece bloqueada, sem
aceitação automática. HTTP, GUI completa, isolamento de processos e
compatibilidade universal estão fora do escopo.
