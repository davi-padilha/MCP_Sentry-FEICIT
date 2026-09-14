# Gateway MCP Sentry e Donna MCP

Esta pasta contém a demonstração funcional do projeto.

- `codigo_gateway/`: código instalável do MCP Sentry;
- `demo_donna/`: Donna completa, incluindo provedores simulados e Google;
- `configuracao_demo/`: arquivo que conecta o gateway à Donna;
- `exemplo_mcp/`: servidor mínimo para teste;
- `testes_gateway/`: testes automatizados;
- `documentacao/`: funcionamento, resultado da demonstração e material da FEICIT.

## Execução

O manual do gateway está em `codigo_gateway/README.md`. Os scripts de
instalação e execução da Donna estão em `demo_donna/scripts/`.

A integração real depende da configuração do cliente MCP, dos endereços
utilizados na demonstração e das credenciais Google do ambiente. Esses dados
não foram copiados. O código funcional foi preservado para que a configuração
possa ser ajustada posteriormente.

## Estado conhecido

A demonstração controlada foi executada e possui resultado sanitizado em
`documentacao/RESULTADO_DA_DEMONSTRACAO_CONTROLADA.md`.
O ensaio pareado Gmail/Sentry foi planejado e revisado, mas não aparece como
resultado executado nesta edição.
