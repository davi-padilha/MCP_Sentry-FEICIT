# Plano do MVP gateway operacional do MCP Sentry

**Data:** 2026-08-27
**Estado:** T1–T5 e a correção do caminho manual preservadas; ensaio manual
local passou. O próximo portão é apenas o fechamento documental, sem novo
commit/push sem revisão independente e OK humano explícito.
**Classe:** crítica — define fronteira de segurança e autorização de execução
**Criador material declarado pelo pesquisador:** Codex, nesta tarefa local
**Reconferência exigida:** outro agente Codex, em tarefa/worktree distinto e
sem participação na criação material, com declaração de independência no parecer
**Natureza:** demonstração aplicada/produto experimental, fora das baterias
A/B/C1/C2/D e sem valor de evidência científica por si só

## 1. Objetivo

Construir uma camada externa entre um cliente agente e um servidor MCP local
Python por `stdio`. O cliente configura somente o MCP Sentry. O Sentry verifica
o servidor antes de executá-lo e impede que uma versão alterada seja iniciada
sem revisão válida.

O primeiro alvo será um MCP mínimo controlado. DonnaMCP será integrado somente
depois que o fluxo mínimo estiver testado e revisado.

## 2. Decisões humanas vinculantes

1. O Sentry é launcher/gateway externo; não será incorporado ao DonnaMCP.
2. Escopo inicial: Windows, Codex, Python local e transporte `stdio`.
3. Metadados vêm de manifesto estático; validação AST é aplicada quando o
   padrão de código for reconhecível. A versão suspeita nunca é executada para
   descobrir suas tools.
4. A IA do cliente conectado é o avaliador: Codex quando o cliente for Codex,
   Claude quando o cliente for Claude. O Sentry não escolhe nem chama Ollama,
   OpenAI API, Anthropic API ou outro modelo próprio.
5. Hash é apenas detector barato de mudança. B/C1/C2/D não são modos nem nomes
   de camadas do produto; permanecem exclusivos do contrato de pesquisa.
6. O avaliador recebe conjuntamente o diff completo de código, metadados e
   configuração declarados, delimitados como conteúdo não confiável.
7. Falha, ausência de veredito, hash divergente, schema inválido ou estado
   ambíguo resultam em bloqueio.
8. Um `allow` cria autorização de uso único para apenas o hash exato revisado.
   O backend poderá iniciar uma vez, na conexão seguinte. O baseline não muda
   automaticamente.
9. A promoção permanente exige comando humano separado `accept-current`.
10. Relatórios serão JSON estruturado mais resumo textual; `stdout` fica
    reservado ao MCP e mensagens operacionais usam `stderr`.
11. Fluxo principal: **B — tentativa de usar uma tool inicia a revisão no mesmo
    turno**. Fallback: **A — usuário pede explicitamente a revisão pendente**.

As letras A e B do item 11 nomeiam somente opções de experiência operacional
desta decisão. Não correspondem às Condições A e B da pesquisa.

## 3. Não objetivos do MVP

- servidores remotos, HTTP/SSE, sandbox avançada ou monitoramento contínuo;
- interface gráfica, múltiplos usuários ou autoridade criptográfica externa;
- inferir metadados executando `tools/list` na versão suspeita;
- analisar dependências arbitrárias instaladas fora do inventário;
- declarar eficácia científica a partir da demonstração;
- modificar módulos, datasets, prompts, runners ou resultados congelados.

## 4. Modelo de confiança

### 4.1 Confiado no MVP

- executável e código do próprio Sentry;
- baseline criado por aprovação humana inicial;
- política de revisão versionada do Sentry;
- armazenamento local do Sentry fora da árvore do servidor;
- comando, argumentos, diretório e inventário registrados no baseline.

### 4.2 Não confiado

- todo código, comentário, string, descrição, schema e configuração da versão
  atual do servidor;
- instruções encontradas dentro do dossiê;
- manifesto atual quando divergir do baseline;
- veredito que não estiver vinculado ao `review_id`, hash e versão da política;
- alegação de identidade do avaliador fornecida apenas pelo cliente.

O MCP permite observar informações declaradas pelo cliente durante a
inicialização, mas o MVP não alegará autenticação criptográfica de que o
veredito veio de um modelo, fornecedor ou usuário específico. O relatório
registrará somente o cliente declarado e a chamada MCP observada.

## 5. Arquitetura

```text
Codex/Claude
  -> MCP Sentry (único servidor configurado)
       -> registro local de baseline, autorizações e relatórios
       -> catálogo aprovado das tools do backend
       -> subprocesso MCP protegido, somente quando autorizado
```

Componentes previstos:

| Componente | Responsabilidade |
| --- | --- |
| `manifest` | inventário explícito de código, metadados, configuração e comando |
| `baseline_store` | snapshot inicialmente aprovado e promoções manuais |
| `integrity` | serialização canônica e hashes dos artefatos |
| `dossier` | diff completo, sinais AST e delimitação de conteúdo não confiável |
| `review_store` | estado pendente, veredito e vínculo ao hash exato |
| `review_policy` | instrução fixa e schema do veredito |
| `gateway` | servidor MCP visível e proxy `stdio` para backend autorizado |
| `reporting` | JSON, resumo textual e auditoria local |
| `cli` | `approve`, `inspect`, `run` e `accept-current` |

## 6. Catálogo de tools

O baseline guarda nomes, descrições e schemas completos das tools aprovadas.
O Sentry pode anunciá-las sem iniciar o backend. Também anuncia três tools de
controle:

- `sentry_security_status`: leitura do estado e do hash atual;
- `sentry_get_pending_review`: leitura paginada do dossiê pendente;
- `sentry_submit_verdict`: grava veredito estruturado e deve ser marcada como
  operação de escrita para que clientes compatíveis solicitem aprovação.

O Sentry não confiará que a aprovação visual do cliente sempre existe. A
segurança decorre da validação do veredito e do bloqueio fechado.

O inventário usado na verificação vem do baseline, não do manifesto atual. O
baseline também fixa raízes inspecionadas e regras de exclusão; arquivos novos
sob essas raízes são detectados mesmo quando a versão atual tenta omiti-los do
manifesto. Exclusões precisam ser explícitas e não podem abranger código Python
ou metadados de tools no MCP mínimo.

## 7. Fluxos operacionais

### 7.1 Primeira aprovação

1. usuário executa `approve` fora da inicialização MCP;
2. Sentry valida manifesto, caminhos e consistência estática possível;
3. usuário confirma a versão conhecida como segura;
4. baseline é salvo fora da pasta do servidor;
5. `approve` recusa sobrescrever baseline existente.

### 7.2 Servidor inalterado

1. Sentry captura os artefatos declarados sem importá-los;
2. hashes e configuração coincidem com o baseline;
3. Sentry recaptura o estado imediatamente antes do `spawn`;
4. backend é iniciado por `stdio` e as mensagens são encaminhadas;
5. divergência ou falha em qualquer passo bloqueia.

### 7.3 Fluxo principal B — tentativa inicia revisão

1. cliente tenta chamar uma tool aprovada do Donna;
2. Sentry detecta mudança e não inicia o backend;
3. a tool responde `security_review_required`, com `review_id`, hash e ação
   seguinte `sentry_get_pending_review`;
4. instruções do servidor orientam o agente a ler todas as páginas, avaliar e
   chamar `sentry_submit_verdict` no mesmo turno;
5. se o agente não continuar, o backend permanece bloqueado e a resposta
   indica o fallback explícito.

### 7.4 Fallback A — pedido explícito

O usuário pede: “Analise a atualização pendente pelo MCP Sentry”. O agente
consulta o estado, lê o dossiê e envia o mesmo veredito estruturado.

### 7.5 Veredito permitir

1. Sentry exige schema exato, `review_id`, `reviewed_hash`, `dossier_hash` e
   `policy_version`;
2. autorização de uso único é registrada para aquele hash e dossiê;
3. resposta solicita reconexão; a chamada original não é repetida;
4. na conexão seguinte, o Sentry recaptura os bytes;
5. a autorização é consumida atomicamente antes de um único `spawn`; falha de
   inicialização não a restaura automaticamente;
6. somente correspondência exata permite iniciar o backend;
7. `accept-current` promove permanentemente a versão após comando humano.

### 7.6 Veredito bloquear

O hash permanece impedido de executar. Justificativa e riscos ficam
registrados. Mudança posterior cria outra revisão; não herda o veredito.

## 8. Schema mínimo do veredito

```json
{
  "review_id": "identificador opaco",
  "reviewed_hash": "sha256",
  "dossier_hash": "sha256 do dossiê canônico completo",
  "policy_version": "mcp-sentry-review-v1",
  "decision": "allow ou block",
  "justification": "texto não vazio",
  "risks": ["risco observado"]
}
```

Campos ausentes, extras, tipos incorretos ou valores fora do domínio falham
fechados. O dossiê inclui a instrução de que seu conteúdo é evidência e nunca
autoridade para alterar política, schema ou papel do avaliador.

Código aprovado e atual pode ser armazenado localmente para produzir o diff e
deve ser tratado como dado sensível. Valores de tokens, senhas, chaves e outras
credenciais nunca entram no manifesto, baseline, dossiê ou relatório. Para
configuração secreta, registram-se apenas nomes de variáveis, caminhos
declarados e políticas não secretas; valores permanecem fora do Sentry.

## 9. Redução de TOCTOU e limite declarado

O MVP fará captura única coerente para análise e nova captura imediatamente
antes de iniciar o subprocesso. A autorização é vinculada ao hash completo.
Para o MCP mínimo, o Sentry executará uma cópia verificada dos artefatos em
área própria, não o arquivo mutável original.

Isso reduz fortemente a troca entre verificação e execução, mas não prova
isolamento de dependências externas ou do interpretador. DonnaMCP só entrará
depois de um inventário fechado de módulos e dependências necessárias.

## 10. Etapas de implementação após aprovação deste plano

### T1 — núcleo determinístico

- manifesto, baseline, hashing, diff, armazenamento e CLI;
- nenhuma rede, modelo ou subprocesso do servidor nos testes de inspeção.

### T2 — MCP mínimo e servidor de revisão

- versão segura e rug pull fictício com marcador em diretório temporário;
- tools de controle, instruções MCP e respostas `security_review_required`.

### T3 — gateway `stdio`

- proxy para versão inalterada/autorizada;
- disciplina estrita de `stdout`, lifecycle, cancelamento, erros e encerramento.

### T4 — fluxo agente-avaliador

- B como principal e A como fallback;
- fixtures de veredito sem chamar IA real;
- teste manual com Codex somente após portão próprio;
- compatibilidade com Claude em etapa posterior, sem alterar o protocolo.

### T5 — integração DonnaMCP

- inventário de código/configuração/metadados;
- primeiro simulação local segura; Google real fica fora até portão específico;
- configuração do cliente passa a apontar ao Sentry.

Cada etapa crítica segue plano → implementação → verificação independente → OK
humano → commit/push. Não haverá commit registral isolado.

## 11. Testes de aceite do MCP mínimo

1. sem baseline: backend não executa;
2. baseline válido e hash igual: tool `ping` funciona pelo gateway;
3. rug pull alterado: tentativa retorna revisão e marcador de execução não surge;
4. dossiê contém diff de código, metadados e configuração;
5. ausência/falha da continuação automática mantém bloqueio e oferece fallback;
6. `allow` com hash, dossiê, review expirado ou schema inválido é rejeitado;
7. `allow` válido exige reconexão, libera os mesmos bytes uma única vez e é
   consumido antes do `spawn`;
8. mudança após veredito invalida autorização;
9. arquivo novo omitido do manifesto atual é detectado pelas raízes aprovadas;
10. `block` persiste para o hash e nunca inicia o subprocesso;
11. `approve` não sobrescreve baseline; `accept-current` é separado;
12. stdout contém somente protocolo MCP;
13. falha do backend, relatório ou armazenamento resulta em bloqueio explícito;
14. instrução maliciosa dentro do código/metadado permanece delimitada como dado;
15. credenciais fictícias de teste não aparecem em baseline, dossiê ou relatório;
16. relatórios JSON e texto permitem reconstruir detecção, revisão e decisão.

## 12. Arquivos permitidos e proibidos na implementação

Permitidos, após aprovação e após a reorganização estrutural:

- `aplicacoes/mcp_sentry/src/mcp_sentry_gateway/`;
- `aplicacoes/mcp_sentry/examples/mcp_minimo/`;
- `aplicacoes/mcp_sentry/tests/`;
- `aplicacoes/mcp_sentry/docs/`, `scripts/` e `config/`.

Proibidos sem nova autorização:

- `testes_cenarios/`, `logs_resultados/`, baterias e artefatos congelados;
- runners, políticas, prompts ou resultados da M2.3;
- credenciais, tokens, dados Google ou efeitos fora de diretório controlado;
- alteração retroativa de `hash_guard.py`, `hybrid_guard.py` ou contratos A-D.

O pacote científico existente em `mcp_sentry/` permanece na raiz e não é a
localização da implementação operacional.

## 13. Portões e condição de parada

T1–T5 foram preservadas nos commits `4c9001a`, `af48867`, `894264b`,
`3db3bb5` e `4b531dc`. T5 foi autorizada apenas para a Donna simulada local: inventário
estático fechado, caminhos de runtime relativos à cópia verificada e testes
sem Google, credenciais, rede ou configuração real de cliente. Por operar
fronteira de segurança, T5 foi verificada independentemente, recebeu OK
explícito do pesquisador e foi preservada. A autorização de T5 não libera IA
real, rede, APIs, Donna live-Google ou Codex integrado.

Se a revisão identificar que Codex não consegue prosseguir do retorno de uma
tool para outra chamada no mesmo turno, B permanece tentativa de melhor esforço
e A continua fallback obrigatório; a segurança e o escopo não são ampliados.

## 14. Fechamento factual do MVP operacional (2026-08-31)

T1--T5 foram preservadas em `4c9001a`, `af48867`, `894264b`, `3db3bb5` e
`4b531dc`. A correção posterior `a341d3c` eliminou três impedimentos do ensaio
manual local: fixa o literal `python` ao interpretador que aprovou o baseline,
completa `notifications/initialized` antes da tool e normaliza somente o
transporte público `stdin`/`stdout` para UTF-8. Ela foi integrada em `main` pelo
merge `f146dd9`.

O ensaio Codex -> MCP Sentry -> Donna simulada local foi relatado como
**passou**, com uma chamada `descrever_donna` retornando sem erro de
decodificação. A revisão independente da correção tinha escopo e verificações
fixados em `PROMPT_REVISAO_INDEPENDENTE_CORRECAO_GATEWAY_MANUAL.md`; este plano
não inventa um parecer histórico separado que não esteja versionado. A revisão
independente exigida para o pacote documental de fechamento é registrada no
próprio pacote, antes de qualquer preservação nova.

Pré-requisitos e limites do ensaio: Windows, Python local já existente com
`mcp==1.29.0`, Donna somente simulada, `stdio`, diretório temporário e
interpretador indicado por `MCP_SENTRY_DONNA_PYTHON`. Não houve Donna/Google
real, rede, API, credencial, modelo chamado pelo Sentry nem configuração
persistente do cliente. A repetição é permitida somente pelo protocolo
temporário; a matriz de cobertura define o que foi ou não demonstrado.

T6 não integra este MVP. Qualquer T6 -- inclusive transporte remoto, sandbox,
Donna live-Google, integração persistente de cliente, autenticação forte ou
nova alegação de segurança -- requer novo plano, revisão independente e
autorização humana explícita antes de implementação ou execução.
