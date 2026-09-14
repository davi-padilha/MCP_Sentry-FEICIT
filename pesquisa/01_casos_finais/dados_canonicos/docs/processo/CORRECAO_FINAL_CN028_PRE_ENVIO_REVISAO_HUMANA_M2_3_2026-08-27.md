# Correção final de CN-028 antes da revisão humana M2.3

Data: 2026-08-27
Autoridade: decisão explícita do pesquisador
Unidade: correção aditiva crítica pré-despacho

## Decisão

Antes do envio a R-A e R-B, substituir somente `M23-CN-028` por uma nova
versão em que a decisão final recalcule literalmente a pertinência
`channel in allowed`.

`matched_by` e `checked_count` são exclusivamente diagnósticos: não podem ser
lidos como entradas nem controlar a decisão. O estágio anterior à decisão
mantém apenas `channel` e `allowed`.

## Escopo preservado

- `M23-NINT-P1-02` está aprovado para seguir sem nova alteração;
- `M23-MT-001` está aprovado para seguir sem nova alteração;
- os outros 87 casos também permanecem inalterados;
- os pacotes e ZIPs v3 ficam preservados como históricos e suspensos;
- nenhum pacote pode ser enviado antes de verificação independente desta
  unidade e novo OK explícito do pesquisador.

## Bloqueios posteriores

O contrato/serializador MCPTox e a ordem D continuam bloqueios formais depois
da aprovação humana e antes de qualquer execução experimental. Não bloqueiam a
revisão humana dos casos.

## Portões

- revisão humana: pendente;
- verificação independente desta correção: pendente;
- commit/push: pendentes de verificação e OK explícito;
- envio a R-A/R-B: não autorizado;
- modelos, rede, preflight e bateria: não autorizados.
