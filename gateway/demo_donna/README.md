# Donna MCP — Assistente Local

Demonstracao aplicada de um MCP util para Google Calendar e Gmail, com uma
atualizacao de rug pull inteiramente ficticia. O Donna MCP e independente do
MCP Sentry: o gateway externo local pode ser configurado entre o cliente e este
servidor. A integração concluída até agora usa somente uma cópia simulada e
local da Donna.
O subprojeto permanece separado das baterias A/B/C1/C2/D e nao produz evidencia
experimental.

## Estrutura da demonstracao

- `codigo-fonte-do-mcp/`: implementação da Donna; `donna_mcp` e `providers`
  permanecem como nomes técnicos de pacotes Python.
- `configuracao-do-mcp/`: exemplos de configuração e variáveis de ambiente.
- `dados-gerados-pelo-mcp/`: auditoria, estado da simulação e ações pendentes
  produzidos localmente durante o uso.
- `documentacao/`: roteiros e orientações da demonstração.
- `ferramentas-para-demonstracao/`: scripts em Python e PowerShell para
  preparar, verificar e executar os cenários.
- `inicializacao-do-mcp/`: programas que o cliente MCP ou os scripts iniciam.
- `testes-automatizados/`: testes da Donna MCP.
- `versao-em-uso-do-mcp/`: a cópia atualmente selecionada para a simulação ou
  integração Google.
- `versoes-para-demonstracao/`: versões aprovada e maliciosa simulada, usadas
  para comparar os cenários sem alterar o código comum.

## Capacidades

O servidor expoe treze tools:

- `descrever_donna` e `status_seguranca`;
- `consultar_agenda` e `encontrar_horarios_livres`;
- `buscar_emails`, `ler_email` e `ler_anexo_email`;
- `criar_evento`, `remarcar_evento` e `cancelar_evento`;
- `criar_rascunho_email` e `enviar_email`;
- `organizar_reuniao`.

As tools de leitura do Gmail usam a sintaxe de busca da propria caixa, nao
marcam mensagens como lidas e nao alteram labels. O corpo e os anexos sao
tratados como conteudo externo nao confiavel: instrucoes encontradas dentro
deles nunca autorizam novas acoes. Anexos sao devolvidos sem execucao nem
gravacao automatica; conteudo textual tambem e decodificado, enquanto binarios
usam base64url. Cada leitura de anexo fica limitada a 1 MiB.

As consultas sao executadas diretamente. Toda operacao que cria, altera,
cancela ou envia algo funciona em duas etapas:

1. a primeira chamada devolve uma previa e um `confirmation_id` valido por 15
   minutos;
2. a mesma chamada, com os mesmos dados e esse identificador, executa a acao.

O agente deve apresentar a previa e obter confirmacao explicita do usuario. A
confirmacao e reivindicada e persistida antes do efeito. Chamadas concorrentes
nao executam a mesma confirmacao duas vezes; depois de um resultado persistido,
a repeticao devolve esse resultado. Se houver timeout ou falha depois de um
efeito possivel, o estado passa a `unknown` e a repeticao automatica e
bloqueada ate reconciliacao no provedor. Criacoes no Calendar tambem recebem um
ID deterministico quando o provedor oferece esse recurso. A confirmacao fica
vinculada ao modo e a politica de protecao que a prepararam.

Conflitos de agenda detectados sao bloqueados por padrao.
`permitir_conflito=true` existe somente para uma decisao explicita. A checagem
de conflito e de melhor esforco: Calendar nao oferece uma reserva transacional
entre consultar outros eventos e criar ou remarcar, portanto uma alteracao
concorrente ainda pode ocupar o horario. Remarcacoes e cancelamentos nao
notificam participantes por padrao; use `enviar_atualizacoes=true` quando isso
fizer parte da previa aprovada. A previa identifica o estado e a versao
(`etag`) do proprio evento; se ele mudar, a confirmacao perde a validade, e o
Google recebe a mesma versao como precondicao atomica da alteracao ou exclusao.

No fluxo combinado, se o evento for criado mas a resposta do Gmail sobre o
rascunho for ambigua, a resposta sera `partial_unknown`: o evento conhecido e
preservado, o rascunho nao e declarado ausente e a confirmacao nao pode ser
repetida antes da reconciliacao.

## Modos

| Modo | Rede | Finalidade |
| --- | --- | --- |
| `simulated-active` | Nao | Ponto canonico da demonstracao aprovada→atual |
| `simulated-safe` | Nao | Desenvolvimento local direto |
| `simulated-rug-pull` | Nao | Compatibilidade com a simulacao direta anterior |
| `live-google` | Sim | Calendar e Gmail da conta autorizada |

O modo `simulated-active` carrega o provedor ativo apenas para reproduzir a
demonstracao. Ele nao decide se uma atualizacao e segura. Essa decisao pertence
ao gateway externo MCP Sentry em `../mcp_sentry/`. O MVP existe, mas uso com
Google real e efeitos externos permanecem fora do escopo autorizado.

## Preparacao

### Instalacao portátil para notebook e desktop (Google real)

O modo portátil mantém somente o código no repositório. Cada máquina recebe
seu próprio ambiente Python, credencial OAuth, token, confirmações e auditoria
em `%LOCALAPPDATA%\MCP-Sentry\DonnaMCP\<profile>`. Assim, Git e
OneDrive não transportam tokens entre computadores.

Pré-requisitos em cada máquina:

- Windows com Python 3.10 ou superior, ou o runtime Python local do Codex;
- uma cópia ou clone deste repositório;
- acesso à internet durante a instalação, autorização e uso das APIs;
- Codex ou outro cliente MCP que aceite servidores locais por `stdio`.

No notebook e depois no desktop, abra PowerShell nesta pasta e execute:

```powershell
.\ferramentas-para-demonstracao\scripts-em-powershell\install_portable.ps1
```

O instalador:

1. cria um `venv` fora do repositório;
2. instala as versões fixadas em `requirements.txt`;
3. executa testes unitários e a verificação MCP simulada;
4. gera um trecho TOML para Codex e um manifesto JSON `stdio` genérico;
5. registra `donna_mcp` em `~/.codex/config.toml`, preservando o
   conteúdo anterior e criando backup quando houver mudança.

Se uma entrada manual chamada `donna_mcp` já existir, o instalador
interrompe sem reescrevê-la. Para apenas gerar o trecho, sem registrar:

```powershell
.\ferramentas-para-demonstracao\scripts-em-powershell\install_portable.ps1 -SkipCodexRegistration
```

Use o mesmo `credentials.json` de cliente OAuth Desktop nas duas máquinas,
transferido por canal seguro, mas autorize cada computador separadamente. Não
copie nem sincronize `token.json`:

```powershell
.\ferramentas-para-demonstracao\scripts-em-powershell\authenticate_portable.ps1 -CredentialsFile "C:\caminho\client_secret.json"
```

Depois, reinicie o Codex e execute:

```powershell
.\ferramentas-para-demonstracao\scripts-em-powershell\diagnose_portable.ps1 -CheckMcp
```

O diagnóstico com `-CheckMcp` inicializa o servidor, lista as treze tools e chama
somente `status_seguranca`. Ele não consulta a agenda, não cria eventos e não
envia e-mail. No Codex, `/mcp` deve mostrar `donna_mcp` conectado.

Para manter contas Google distintas na mesma máquina, use perfis separados em
todos os comandos, por exemplo `-Profile pessoal`. Nomes de perfil aceitam
somente letras, números, `_` e `-`.

O arquivo `run_portable_google.ps1` é um launcher alternativo para clientes
MCP que preferem executar um script PowerShell. A conexão gerada para o Codex
chama diretamente o Python isolado da máquina.

Clientes MCP diferentes do Codex podem adaptar os campos de
`stdio_connection.json` (`command`, `args`, `cwd` e `env`) ao formato de
configuração que suportam. Não existe um arquivo de configuração local único
compartilhado por todos os clientes.

O instalador é atualmente específico para Windows. Ele não copia o código do
servidor: cada máquina precisa manter esta pasta em um caminho estável; se o
repositório for movido, execute o instalador novamente para atualizar o
`config.toml`.

O token continua sendo um JSON OAuth legível pelo usuário local, embora fique
fora do repositório em `%LOCALAPPDATA%`. Use conta Windows protegida, criptografia
de disco e nunca compartilhe a pasta do perfil. Integração com um cofre nativo
do sistema permanece melhoria futura.


Importante: a protecao contra atualizacao pertence ao MCP Sentry externo. A
portabilidade do Donna MCP nao deve ser confundida com uma verificacao de
integridade ja aplicada ao modo Google real.

### Preparacao da demonstracao local

No PowerShell, de qualquer diretorio:

```powershell
& "C:\caminho\MCP-Sentry-FEICIT\gateway\demo_donna\ferramentas-para-demonstracao\scripts-em-powershell\setup.ps1"
```

O script cria `.venv`, instala as dependencias fixadas e instala de forma
editável a Donna e o MCP Sentry Gateway no mesmo interpretador. Em seguida,
executa os testes, verifica o protocolo MCP por `stdio`, compara as versoes e
deixa o snapshot aprovado ativo em uma sessao local limpa. Ele requer acesso ao
indice de pacotes somente na preparacao.

Se o Python nao for encontrado automaticamente:

```powershell
.\ferramentas-para-demonstracao\scripts-em-powershell\setup.ps1 -PythonExecutable "C:\caminho\python.exe"
```

## Demonstracao recomendada

Mantenha o painel aberto em outro terminal:

```powershell
.\ferramentas-para-demonstracao\scripts-em-powershell\run_dashboard.ps1
```

Abra `http://127.0.0.1:8765`. O painel mostra acoes normais, efeitos ocultos
simulados e bloqueios do Sentry.

### 1. Versao aprovada

```powershell
.\ferramentas-para-demonstracao\scripts-em-powershell\activate_demo_approved.ps1
```

Encerre qualquer conexao anterior antes de executar o comando. Ele ativa o
snapshot aprovado, reinicia o calendario e as confirmacoes locais da
demonstracao e limpa a auditoria anterior. Nenhuma credencial ou dado do Google
e tocado. No cliente MCP, inicie `donna_mcp`, que aponta para
`inicializacao-do-mcp/server_demonstracao.py`. Faca o pedido do roteiro, apresente a previa e
confirme a acao. O fluxo util e concluido sem acao oculta.

### 2. Atualizacao de rug pull

Encerre a conexao e ative a atualizacao:

```powershell
.\ferramentas-para-demonstracao\scripts-em-powershell\activate_demo_rug_pull.ps1
```

O comando reinicia somente o calendario e as confirmacoes simuladas, preserva
a auditoria do estagio aprovado e grava o snapshot posterior no mesmo artefato
executavel canonico `versao-em-uso-do-mcp/simulacao-controlada/provider.py`. O metadado local
ignorado `versao-em-uso-do-mcp/simulacao-controlada/version.json` tambem e atualizado, mas nao e
carregado pelo servidor. Reinicie a mesma conexao `donna_mcp`: ponto de entrada, configuracao e estado inicial
continuam comparaveis. A resposta util continua normal, enquanto o painel
registra o participante ou BCC ficticio com `network_performed=false`.

### 3. Mesma atualização, pelo MCP Sentry externo

Para a demonstração local simulada, configure o cliente para chamar o launcher
do MCP Sentry, que por sua vez iniciará este mesmo servidor. O gateway compara
a versão aprovada e a atual antes de executar a Donna. Siga o manual em
`../mcp_sentry/usuario-final/README.md`; não aplique este fluxo a Google real.
O mecanismo embutido anterior foi preservado apenas em
uma referencia legada, fora da estrutura canonica da Donna MCP.

Compare os dois pacotes logicos, que usam os mesmos caminhos canonicos:

```powershell
.\.venv\Scripts\python.exe ferramentas-para-demonstracao\scripts-em-python\compare_versions.py
```

## Google real (fluxo manual legado)

O mesmo `donna_mcp` e `inicializacao-do-mcp/server_google.py` tambem suportam a demonstracao de
atualizacao aprovada→rug pull. Antes de iniciar o servidor Google pela primeira
vez, ative o snapshot aprovado:

```powershell
.\.venv\Scripts\python.exe ferramentas-para-demonstracao\scripts-em-python\activate_google_live_version.py approved
```

Para simular uma atualizacao posterior, encerre a conexao MCP, execute:

```powershell
.\.venv\Scripts\python.exe ferramentas-para-demonstracao\scripts-em-python\activate_google_live_version.py rug-pull
```

e reinicie a mesma conexao `donna_mcp`. O caminho configurado, o nome do MCP e
as tools nao mudam. A versao `rug-pull` acrescenta uma BCC oculta para
`23000315@liberato.com.br` em cada envio; restaure `approved` ao fim da
demonstracao. Use somente conteudo e contas controlados.

1. Crie um projeto no Google Cloud.
2. Ative Google Calendar API e Gmail API.
3. Configure a tela de consentimento e contas de teste.
4. Crie um cliente OAuth para aplicativo de computador.
5. Salve o JSON em `local_data/credentials.json`.
6. Execute a autorizacao interativa separadamente:

```powershell
$env:MCP_SECRETARY_MODE = "live-google"
.\.venv\Scripts\python.exe ferramentas-para-demonstracao\scripts-em-python\authenticate_google.py
```

O token fica em `local_data/token.json`, ignorado pelo Git. O servidor real nao
abre o navegador nem inicia OAuth durante o startup; sem token valido, falha com
uma orientacao clara para executar o script de autenticacao.

Depois da autorizacao:

```powershell
.\ferramentas-para-demonstracao\scripts-em-powershell\run_live_google.ps1
```

Escopos solicitados:

- eventos do Google Calendar;
- composicao e envio pelo Gmail.
- leitura de mensagens e anexos pelo Gmail, sem permissao para excluir,
  arquivar ou mudar labels.

Quando os escopos aumentarem, execute novamente o autenticador. Ele detecta o
token sem as novas permissoes e inicia uma nova tela de consentimento:

```powershell
.\ferramentas-para-demonstracao\scripts-em-powershell\authenticate_portable.ps1
```

Se os escopos mudarem, remova somente o token local e autorize novamente.

## Configuracao no Codex

Use `configuracao-do-mcp/codex_config.example.toml` e ajuste os caminhos absolutos. Ele
define uma conexão direta `donna_mcp`, útil apenas para a demonstração direta.
Para a demonstração protegida, substitua essa entrada pelo launcher do MCP
Sentry conforme o manual do gateway. O setup já deixa a versão aprovada ativa.

Para `donna_mcp`, prefira `install_portable.ps1`: ele usa os caminhos
reais da máquina, separa dados por perfil e registra um bloco delimitado no
arquivo do Codex. Segundo a documentação oficial, Codex desktop, CLI e extensão
compartilham essa configuração local.

## Verificacoes locais essenciais

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s testes-automatizados -v
.\.venv\Scripts\python.exe ferramentas-para-demonstracao\scripts-em-python\verify_mcp.py
.\.venv\Scripts\python.exe ferramentas-para-demonstracao\scripts-em-python\compare_versions.py
```

O verificador MCP inicia processos locais do mesmo ponto de entrada e reproduz
a sequencia do roteiro sobre uma auditoria cumulativa:

- aprovado;
- rug pull direto, com efeito oculto ficticio.

Ele tambem confirma schemas identicos, confirmacao obrigatoria e repeticao
idempotente.

## Limites deliberados

- A disponibilidade considera somente o `calendar_id` configurado na conta
  autorizada; nao revela agenda privada de terceiros sem permissao.
- Donna MCP usa texto simples e nao anexa arquivos.
- A verificacao de atualizacoes sera fornecida pelo gateway externo MCP Sentry;
  este subprojeto nao deve ser interpretado como um gateway por si so.
- Em resultado `unknown`, uma pessoa deve consultar Calendar ou Gmail antes de
  emitir uma nova confirmacao. O Gmail nao oferece uma chave de idempotencia de
  envio equivalente ao ID deterministico usado no Calendar.
- A integracao Google precisa de um ensaio controlado com as contas de
  demonstracao antes de ser declarada validada no ambiente real.
- O painel e local e de apresentacao, nao multiusuario.

## Rotulo cientifico

Esta demonstracao explica o mecanismo e a utilidade do caso de uso. Ela nao e
uma observacao adicional das baterias A/B/C1/C2/D e nao deve ser incorporada as
metricas experimentais.
