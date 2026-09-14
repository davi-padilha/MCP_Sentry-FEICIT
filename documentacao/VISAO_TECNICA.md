# Visão técnica

O repositório possui duas partes relacionadas:

## Pesquisa

Casos controlados, entradas para modelos, resultados e análises das condições
A/B/C1/C2/D. Essa parte mede modos de falha e não constitui um produto de
segurança de produção.

## Gateway e Donna

O MCP Sentry operacional verifica a integridade de um backend antes de
iniciá-lo. A Donna é o servidor MCP usado na demonstração funcional, incluindo
os fluxos simulados e a integração Google configurável.

O cliente deve iniciar o gateway, que então controla o início da Donna. Se o
cliente mantiver também uma conexão direta com a Donna, essa rota não estará
protegida.

