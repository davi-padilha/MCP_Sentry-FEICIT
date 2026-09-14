# Usar o MCP Sentry

## O que é

O MCP Sentry é uma camada local de proteção para um servidor MCP por `stdio`.
Em vez de configurar o cliente para iniciar diretamente o servidor, você o
configura para iniciar o Sentry. O Sentry só inicia o backend quando os arquivos
atuais correspondem à versão aprovada ou quando uma alteração recebeu um
veredito válido de revisão.

Ele foi criado para reduzir o risco de uma atualização silenciosa alterar um
servidor MCP previamente confiado. Não é antivírus, sandbox, autenticação de
usuários ou garantia de segurança de produção.

## O que você precisa

- Windows e Python 3.11 ou superior;
- um cliente MCP que aceite servidores locais por `stdio`;
- o código do gateway em um caminho estável;
- um diretório local separado para o estado do Sentry.

O diretório de estado guarda a versão aprovada, revisões e relatórios. Nunca o
coloque dentro da pasta do servidor protegido, pois o Sentry recusará essa
configuração.

## Instalação

Abra o PowerShell na pasta `aplicacoes/mcp_sentry/gateway` e execute:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools
python -m pip install .
```

Se o comando `py -3.11` não existir, use o caminho do Python 3.11 ou posterior
instalado na máquina. `setuptools` é o backend de build declarado pelo pacote;
instalá-lo explicitamente evita falha em ambientes Python que não o incluem por
padrão.

## Primeira aprovação

Antes de usar um backend, confirme manualmente que ele é a versão que você
pretende aprovar. Crie um diretório de estado fora do projeto protegido. Este
exemplo usa o servidor mínimo incluído no repositório:

```powershell
$store = Join-Path $env:LOCALAPPDATA "MCP-Sentry\estado-exemplo"
mcp-sentry approve `
  --manifest ..\examples\mcp_minimo\manifest.json `
  --store $store
```

`approve` cria o baseline inicial e não o substitui depois. Para substituir uma
versão aprovada de propósito, use o fluxo de revisão e a promoção explícita;
não apague o estado para contornar uma alteração.

Depois de uma revisão concluída e de uma decisão humana de tornar a nova versão
permanente, o operador pode promovê-la explicitamente:

```powershell
mcp-sentry accept-current `
  --manifest ..\examples\mcp_minimo\manifest.json `
  --store $store
```

Esse comando troca o baseline. Use-o somente quando você tiver confirmado que
a alteração é a versão que deve passar a ser confiada.

## Configurar o cliente MCP

Substitua a entrada direta do backend por uma entrada que execute o gateway. O
formato exato depende do cliente; conceitualmente, a configuração é:

```json
{
  "command": "C:\\caminho\\para\\mcp-sentry-gateway.exe",
  "args": [
    "--manifest", "C:\\caminho\\para\\manifest.json",
    "--store", "C:\\Users\\voce\\AppData\\Local\\MCP-Sentry\\meu-backend"
  ]
}
```

Em uma instalação no ambiente virtual, o executável costuma estar em
`.venv\Scripts\mcp-sentry-gateway.exe`. Mantenha uma única entrada ativa para
o backend protegido. Uma conexão direta paralela com o mesmo backend contorna
o gateway.

Para testar sem configurar um cliente, inicie o gateway no terminal:

```powershell
mcp-sentry-gateway `
  --manifest ..\examples\mcp_minimo\manifest.json `
  --store $store
```

Ele espera mensagens MCP em `stdin`; portanto, não é uma interface interativa
para uso manual comum.

## Quando uma atualização é encontrada

1. O Sentry não inicia a versão alterada.
2. O cliente recebe um pedido de revisão e um identificador de revisão.
3. O revisor lê o dossiê completo e envia uma recomendação estruturada de
   permitir ou bloquear.
4. Uma recomendação de permitir permanece bloqueada. Fora do MCP, o operador
   confere os hashes e aprova a revisão exata, gerando uma autorização única
   para aqueles mesmos bytes e exigindo nova conexão.
5. Para tornar a alteração o novo baseline, um operador executa uma promoção
   explícita, separada da revisão.

O Sentry falha fechado: erro, dossiê inválido, revisão expirada ou alteração
posterior ao veredito mantêm o backend bloqueado.

`sentry_security_status` também inclui a evidência sanitizada
`backend_lifecycle` quando chamado por um gateway ativo. O campo
`spawn_attempts` é persistido antes de qualquer `subprocess.Popen`; por isso,
valor zero na sessão identificada demonstra que aquela instância não chegou à
fronteira de inicialização do backend. Se essa evidência não puder ser gravada,
o Sentry falha fechado e não tenta iniciar o processo. A resposta MCP é
vinculada à instância que a produziu; o arquivo `current` facilita inspeção
externa, e uma cópia identificada por `gateway_session_id` preserva cada sessão
para o pacote sanitizado.

### Aprovar uma recomendação externamente

Depois de conferir o dossiê, o operador usa os valores exibidos pela revisão:

```powershell
mcp-sentry approve-review-execution `
  --manifest ..\examples\mcp_minimo\manifest.json `
  --store $store `
  --review-id <review_id> `
  --reviewed-hash <current_hash> `
  --dossier-hash <dossier_hash> `
  --human-confirmation APPROVE_REVIEW_EXECUTION
```

O comando não é uma tool MCP. A confirmação é uma atestação operacional, não
autenticação criptográfica; a separação depende de o store e esse comando não
estarem disponíveis para escrita pelo modelo.

## Limitações importantes

- Protege um backend por instância e manifesto; para vários backends, use uma
  instância por backend.
- Protege somente o backend iniciado pelo Sentry. Não intercepta conexões MCP
  já abertas ou entradas diretas paralelas.
- Confia no host local, no executável do Sentry, no interpretador e no diretório
  de estado. Não oferece isolamento de dependências externas.
- O escopo atual é local, Python e `stdio`; HTTP, SSE, múltiplos usuários e
  monitoramento contínuo não fazem parte do MVP.
- A demonstração Donna coberta pelo gateway é simulada e local. Google real,
  credenciais e efeitos externos não estão autorizados por este MVP.
- O gateway não chama nem escolhe um modelo de IA próprio. O cliente/agente
  configurado realiza a revisão quando isso fizer parte do seu fluxo.

## Verificar a instalação

Na raiz de `aplicacoes/mcp_sentry`, execute:

```powershell
$env:PYTHONPATH = "gateway\src"
python -m unittest discover -s tests -v
```

Os testes são locais e usam fixtures; eles não exigem credenciais, rede nem
uma conta Google.

## Ambiente compartilhado da demonstração Donna

Para a demonstração integrada, use o interpretador absoluto criado por
`aplicacoes/donna_mcp/scripts/powershell/setup.ps1`. O script instala Donna e
este gateway nesse mesmo ambiente; assim, o launcher `-m
mcp_sentry_gateway.gateway` e o backend Donna não dependem de `PYTHONPATH`, do
diretório atual ou dos aliases `python`/`py`. Isto prepara somente o ambiente
local; não autoriza OAuth, Google ou T7.

## Documentação técnica

Para decisões, marcos de desenvolvimento e detalhes de segurança, consulte
[`../docs/README.md`](../docs/README.md). Esses documentos descrevem o projeto;
este guia é a referência prática para instalação e operação local.
