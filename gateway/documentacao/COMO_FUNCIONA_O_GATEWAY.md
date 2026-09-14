# Como funciona o MCP Sentry

O gateway fica entre o cliente MCP e a Donna. Antes de iniciar a Donna, ele
compara o código, a configuração e os metadados atuais com uma versão aprovada.

## Fluxo

1. o operador aprova uma versão conhecida;
2. o cliente passa a iniciar o MCP Sentry, não a Donna diretamente;
3. se nada mudou, o gateway inicia uma cópia verificada da Donna;
4. se houver mudança, a Donna permanece parada e um dossiê é gerado;
5. uma revisão recomenda permitir ou bloquear;
6. uma liberação exige confirmação externa do operador para os mesmos hashes.

## O que ele protege

- alterações nos arquivos cobertos pelo manifesto;
- mudanças na configuração de execução;
- início do backend antes da conclusão da revisão;
- exposição acidental de segredos nos relatórios do gateway.

## Limitações

- protege apenas backends configurados atrás dele;
- uma conexão direta paralela contorna a proteção;
- não é sandbox, antivírus ou autenticação;
- depende da integridade do computador, do gateway e do diretório de estado;
- o protótipo atual é voltado a MCP local por `stdio`.

