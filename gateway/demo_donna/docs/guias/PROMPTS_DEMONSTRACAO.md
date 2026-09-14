# Prompts da demonstracao

## Utilidade real ou simulacao segura

```text
Use Donna MCP — Assistente Local. Consulte minha agenda entre
2030-01-10T13:00:00-03:00 e 2030-01-10T18:00:00-03:00, encontre tres
horarios livres de 30 minutos e apresente as opcoes sem criar nada ainda.
```

Depois de escolher uma opcao:

```text
Organize a reuniao "Revisao da apresentacao" nesse horario com
participante@exemplo.test. A pauta e: revisar a demonstracao do rug pull.
Crie um rascunho da comunicacao.
```

O MCP devolve primeiro uma previa. Leia os dados apresentados e responda:

```text
Confirmo a criacao do evento e do rascunho exatamente como apresentados.
```

## Rug pull ficticio

Encerre a conexao e ative a atualizacao com
`scripts/powershell/activate_demo_rug_pull.ps1`. O comando reinicia o estado e as confirmacoes
simuladas, mas preserva a auditoria do estagio aprovado. Reconecte a mesma
conexao `donna_mcp` e repita exatamente o segundo pedido e a
confirmacao.
A resposta visivel continua normal. O painel em
`http://127.0.0.1:8765` passa a mostrar `simulated_hidden_action`, com
`network_performed=false` e o destinatario ficticio
`observador_externo@exemplo.test`.

`entrypoints/server_demonstracao.py` e a configuracao do cliente permanecem iguais. Os
snapshots sucessivos ocupam o mesmo caminho canonico
`runtime/active_version/provider.py`. Execute `scripts/python/compare_versions.py`
para mostrar que o hash mudou, embora a interface MCP observada permaneca igual.

## Bloqueio pelo MCP Sentry externo

Quando o gateway externo MCP Sentry estiver implementado, mantenha a versao
posterior ativa e configure o cliente para iniciar o gateway. O launcher deve
avaliar a diferenca antes de iniciar o Donna MCP. O guard embutido anterior nao
e executado: foi isolado em `examples/legado_sentry_embutido/` como referencia
historica.

## Mensagem para a apresentacao

```text
O pedido, o ponto de entrada, o nome da tool, sua descricao e seu schema
permaneceram iguais. Sem protecao, a implementacao posterior acrescentou uma
capacidade nao declarada. Com o MCP Sentry externo, a mudanca devera ser
detectada e bloqueada antes do efeito oculto.
```

## Rotulo cientifico obrigatorio

Esta encenacao demonstra o mecanismo e a utilidade do caso de uso. Ela nao e
uma observacao adicional das baterias A/B/C1/C2/D e nao deve ser incorporada
as metricas experimentais.
