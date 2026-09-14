# Pacote de fechamento formal — MVP operacional MCP Sentry

**Data:** 2026-08-31
**Classe:** crítica, fronteira de segurança
**Estado:** candidato documental; proibidos commit e push até parecer
independente favorável e novo OK humano explícito.

## Declaração de fechamento

O escopo implementado fecha T1--T5 do MVP local: baseline determinístico,
revisão local, gateway `stdio`, fluxo por fixtures e Donna simulada em cópia
verificada. A cadeia manual Codex -> MCP Sentry -> Donna simulada foi relatada
como aprovada após `a341d3c`; o merge em `main` é `f146dd9`.

O corretivo fixa o interpretador aprovado, conclui o ciclo
`notifications/initialized` antes da tool e usa UTF-8 no transporte público.
O prompt de inspeção independente da correção é
`PROMPT_REVISAO_INDEPENDENTE_CORRECAO_GATEWAY_MANUAL.md`. Não há alegação neste
pacote de parecer histórico não armazenado no repositório.

## Evidência e limites

`MATRIZ_COBERTURA_ACEITE_MVP_GATEWAY.md` relaciona os 16 critérios aos testes
reais e marca as lacunas. `PROTOCOLO_REPETICAO_LOCAL_TEMPORARIA_MVP.md` limita
qualquer repetição ao ambiente efêmero. O ensaio manual é validação aplicada;
não é bateria, preflight, resultado ou evidência do contrato A/B/C1/C2/D.

Permanecem fora do escopo: Donna/Google reais; rede, APIs, credenciais e IA
chamada pelo Sentry; HTTP/SSE; sandbox avançada; múltiplos usuários;
autenticação criptográfica; configuração persistente de cliente; alteração de
M2.3, datasets, baterias, runners, prompts, logs ou artefatos congelados.

## Portão de preservação

Antes de qualquer commit/push, outro agente Codex sem participação material na
criação destes documentos deve inspecionar o conteúdo e o diff reais, executar
somente verificações locais autorizadas e emitir `APROVADO`, `APROVADO COM
RESSALVAS` ou `DEVOLVIDO PARA CORREÇÃO`, com declaração de independência. Com
parecer favorável, o trabalho ainda aguarda **novo OK humano explícito**. Sem
esse OK, este pacote permanece candidato e nenhum commit/push é autorizado.

## T6 explicitamente bloqueada

T6 não foi planejada nem autorizada. Toda evolução após este fechamento exige
novo plano delimitado, revisão independente e autorização humana explícita
antes de implementação, ensaio ou configuração persistente. Isso inclui, sem
limitar, transporte remoto, Donna live-Google, integração persistente de Codex,
novo mecanismo de autorização ou alegações ampliadas de segurança.
