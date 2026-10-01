# Complemento para a MOSTRATEC — valor do gateway

Este trecho foi pensado para entrar no final da apresentação existente, como uma extensão de aproximadamente 40 segundos.

## Ideia central

**A aprovação de uma ferramenta precisa acompanhar as mudanças da sua implementação.**

O valor do MCP Sentry é transformar essa preocupação em um mecanismo concreto: verificar a versão local antes de iniciar o servidor, interromper a execução quando houver mudanças e oferecer evidências para revisão. A IA ajuda a interpretar; o operador mantém a decisão de autorizar.

## Fala para acrescentar à apresentação

> Além de investigar como a IA avalia mudanças em ferramentas, desenvolvemos uma forma de colocar essa revisão no caminho de execução. O MCP Sentry verifica se o servidor local continua correspondente à versão aprovada. Quando encontra uma mudança, mantém o servidor parado e apresenta evidências para análise. A IA recomenda; o operador autoriza. Hoje esse mecanismo funciona como gateway. Como evolução, propomos incorporá-lo ao próprio client de IA, para que revisar uma mudança faça parte do uso da ferramenta. Essa integração ainda é uma proposta.

## Comparação visual simples

**Implementado:** client de IA → gateway Sentry → servidor MCP local.

**Proposta futura:** client de IA com verificação e revisão integradas → servidor MCP local.

Nos dois casos, a ideia é preservar a decisão do operador e impedir que o agente altere a referência ou a autorização. Na implementação atual, a revisão usa uma interface separada.

## Acréscimos propostos aos materiais

- **Relatório:** inserir um parágrafo de discussão: “O gateway demonstra uma forma de vincular a autorização à versão local revisada. Sua arquitetura oferece uma base para estudar a incorporação desse controle aos clients de IA, mantendo a verificação de integridade, a recomendação da IA e a decisão humana como responsabilidades distintas.”
- **Banner:** acrescentar apenas um bloco: **“Da prova de conceito à integração nativa”**, com a comparação acima e a legenda **“Integração nativa: proposta futura”**.
- **Vídeo:** acrescentar uma tela final com a mesma comparação e a frase: “O próximo passo proposto é levar esse controle ao próprio client.”

**Limite que acompanha o complemento:** o protótipo cobre servidores locais pela rota e pelos arquivos configurados. Há testes técnicos registrados; o piloto completo da candidata atual nos clients reais permanece pendente.
