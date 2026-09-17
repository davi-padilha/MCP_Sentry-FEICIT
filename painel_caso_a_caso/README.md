# MCP Sentry · caso a caso

Painel revisado a partir do artefato público fornecido pelo usuário. Os arquivos em `dist/` são a versão final, com 11 telas, navegação por teclado, modo projeção, glossário e filtros de erros.

As decisões, justificativas e os valores de custo foram preservados. As antigas subclasses foram reunidas em casos perigosos, legítimos e sem mudança. Datas das chamadas e o esforço dos modelos foram retirados da apresentação; as duas configurações do Luna são identificadas por baixo/alto.

Na tela 6, os totais consideram apenas casos e repetições com decisões binárias nas três defesas. Na tela 7, R3 continua sendo diagnóstico: 10 acertos, 5 erros e 4 inconclusivas, conferidos nos registros oficiais das duas campanhas.

As recusas do Opus 5 são distinguídas de decisões semânticas e de inconclusivas. O painel não possui os detalhes da regra de segurança acionada. A possibilidade de encaminhar uma análise recusada a outro modelo segue a documentação do provedor e não foi testada nesta campanha: https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback

`preparar-painel.mjs` registra a importação inicial e não deve ser executado sobre a versão revisada. `validar-painel.mjs` verifica arquivos e totais com o original e os registros de pesquisa no diretório pai.

Para visualizar, sirva a pasta `dist/` por HTTP. A biblioteca G2 5.4.8 está incluída; as fontes IBM Plex são carregadas do Google Fonts, com fontes do sistema como alternativa.
