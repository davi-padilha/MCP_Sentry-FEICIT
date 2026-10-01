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

A resposta de bloqueio indica uma interface de diagnóstico independente,
somente leitura; ela não recomenda aprovação nem tentativa de contorno. A
revisão é uma tarefa posterior, solicitada pelo usuário, por exemplo “Revise o
bloqueio do Sentry”. O cliente usa o diagnóstico que reúne as evidências e,
se solicitado separadamente, registra sua própria justificativa vinculada aos
hashes. Uma recomendação de permitir continua exigindo autorização externa do
operador.

Sem parecer, o status declara que a mudança ainda não foi avaliada semanticamente.
Indicadores técnicos são evidência, não uma conclusão semântica. Veja o roteiro
em [AVALIACAO_SEMANTICA_CLIENTE.md](AVALIACAO_SEMANTICA_CLIENTE.md).

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
