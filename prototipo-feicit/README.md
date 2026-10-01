# Protótipo MCP Sentry usado na FEICIT

Esta pasta preserva a versão anterior e seus cenários de demonstração.
Ela não é o pacote atual para instalação pelo usuário. A entrega atual está em
[pacote-usuario/](../pacote-usuario/README.md); o código atual fica em
[desenvolvimento/gateway/](../desenvolvimento/gateway/README.md).

O protótipo é mantido para reproduzir os cenários da FEICIT.

- `codigo_gateway/`: código instalável do MCP Sentry;
- `configuracao_demo/`: arquivo que conecta o gateway à Donna;
- `exemplo_mcp/`: servidor mínimo para teste;
- `testes_gateway/`: testes automatizados;
- `documentacao/`: funcionamento e descrição da demonstração anterior.

A Donna MCP demonstrada e protegida pelo gateway está em
[`../demonstracao-donna/`](../demonstracao-donna/), fora desta pasta para não
ser confundida com um componente do Sentry.

## Execução

O manual do gateway está em `codigo_gateway/README.md`. Os scripts de
instalação e execução da Donna estão em
`../demonstracao-donna/ferramentas-para-demonstracao/`.

A integração real depende da configuração do cliente MCP, dos endereços
utilizados na demonstração e das credenciais Google do ambiente. Esses dados
não foram copiados. O código funcional foi preservado para que a configuração
possa ser ajustada posteriormente.

## Estado conhecido

A demonstração controlada foi executada e possui resultado sanitizado em
`documentacao/RESULTADO_DA_DEMONSTRACAO_CONTROLADA.md`.
O ensaio antigo Gmail/Sentry não foi executado; seu plano foi retirado. As próximas
etapas são definidas no [plano MOSTRATEC](../documentacao/PLANO_MOSTRATEC.md).
