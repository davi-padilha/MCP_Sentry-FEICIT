# Recorreção de três casos antes da revisão humana — M2.3

**Data:** 2026-08-26

**Classe:** crítica, prospectiva e aditiva

**Base reconciliada:** `6136ee91962486a768405886950cdf56ad94d2a9`

**Estado:** candidata local; verificação independente e OK humano pendentes

## Decisão do pesquisador

Antes de iniciar o trabalho de `R-A` e `R-B`, o pesquisador reprovou a qualidade
dos casos `M23-NINT-P1-02`, `M23-CN-028` e `M23-MT-001` e determinou sua
correção ou substituição. Nenhuma resposta humana foi coletada.

Os ZIPs v2 já preservados em
`entregas_avaliadores_reavaliacao_pre_bateria_m2_3/` passam a ser históricos e
**não devem ser enviados nem preenchidos**. Eles não são apagados ou editados.

A unidade começou em `97711c3`; durante a preparação, `origin/main` avançou
para `6136ee9` com a importação versionada de evidência externa. Como esses
commits não alteraram os casos, o instrumento ou os ZIPs de revisão, a base foi
reconciliada para `6136ee9` antes da rematerialização final desta candidata.

## Candidata aditiva

`testes_cenarios/m2_3_campanha_v1/reavaliacao_pre_bateria_v2/` substitui somente:

1. `M23-NINT-P1-02`: o delta agora une campos diagnósticos somente quando o
   chamador ativa `preview`, sem submeter esses campos à allowlist pública;
2. `M23-CN-028`: o controle acrescenta diagnóstico de correspondência exata e
   contagem da allowlist, sem normalizar identificadores nem ampliar aceitação;
3. `M23-MT-001`: troca `key_pattern_validator` pelo registro suplementar
   `M23-MT-011` (`common_directory_security`), anteriormente auditado como
   `aprovado_para_extensao_futura`, e constrói predecessor sintético da mesma
   ferramenta com a limitação de alegação já adotada.

Os outros 87 slots apontam sem alteração para a candidata v1 preservada. Os
três casos recebem novos `case_id` e `blind_id`; respostas ou formulários
anteriores não podem ser reutilizados.

## Integração executável — esclarecimento

Os alertas do pesquisador procedem:

- o serializador preservado reconhece a forma MCPTox antiga com `added_tool`,
  não a forma de modificação persistente com `tool`;
- a ordem D preservada ainda contém os quatro IDs N-INT anteriores.

Essa propagação estava prevista para a unidade posterior à aprovação humana,
conforme o prompt de continuidade da reavaliação, que exige novo congelamento e
novo pacote executável com os IDs propagados. O erro de processo foi não tornar
esses dois bloqueios explícitos no boletim de despacho.

Depois da aprovação humana, uma nova unidade crítica deverá, em conjunto:

1. formalizar e testar a forma MCPTox `tool` no contrato/serializador;
2. recalcular a ordem D com os IDs N-INT aprovados;
3. rematerializar os 150 payloads do dry-run;
4. repetir vazamento, contagens, pareamento e determinismo;
5. manter fechados todos os portões de preflight, modelo e campanha.

## Portões

Esta unidade não autoriza despacho, commit, push, modelo, API, MCP, Ollama,
preflight, Fase B, E2 ou bateria. Antes de qualquer despacho são obrigatórios:

1. validação local da candidata;
2. verificação independente por agente que não a criou;
3. OK explícito do pesquisador para preservar;
4. nova materialização e verificação dos pacotes e ZIPs de `R-A`/`R-B`.
