# Lado direito do banner — proposta final de textos

Proposta escrita para substituir os blocos atuais. O PDF não foi alterado. Os percentuais abaixo foram preservados da conclusão existente; não foram recalculados nesta edição.

## Alterações na organização

- Retirar “Evidências complementares e viabilidade”, “Por que combinar evidências?” e “Viabilidade operacional”.
- Usar a área superior para “MCP Sentry — da pesquisa à aplicação”, reunindo texto e fluxograma ampliado.
- Substituir o bloco atual de aplicação por “Evolução proposta — controle integrado ao client”.
- Substituir a conclusão pelo texto abaixo e manter as referências no rodapé.

## MCP SENTRY — DA PESQUISA À APLICAÇÃO

A pesquisa fundamentou o desenvolvimento do MCP Sentry, um gateway local entre o client de IA e o servidor MCP. Antes de iniciar o servidor, ele compara arquivos, configuração e metadados com uma referência aprovada. Quando detecta mudanças, mantém o servidor parado e apresenta evidências para revisão assistida pela IA do client. O parecer não autoriza a execução: a decisão cabe ao operador e é vinculada à versão revisada. Quando autorizado, o servidor executa uma cópia verificada dos arquivos selecionados.

### Fluxo de verificação e revisão

Client de IA → MCP Sentry → Verificar versão → Houve mudança?

**Não:** Preparar cópia verificada → Iniciar servidor.

**Sim:** Manter servidor bloqueado → Revisão assistida por IA → Decisão do operador.

**Sem autorização:** Permanecer bloqueado.

**Com autorização:** Revalidar versão e configuração → Preparar cópia verificada → Iniciar servidor.

**Legenda do fluxograma:** “Fluxo simplificado da rota protegida. O catálogo anunciado é conferido após a inicialização e antes de encaminhar chamadas. Fonte: Os autores (2026).”

## EVOLUÇÃO PROPOSTA — CONTROLE INTEGRADO AO CLIENT

O gateway funciona como prova de conceito de um mecanismo que poderia ser incorporado ao próprio client de IA. Nessa proposta, verificar mudanças e apresentar evidências para revisão fariam parte da experiência de uso. A integração deve preservar a decisão do operador e impedir que o agente altere a referência aprovada ou a autorização.

**Implementado:** Client de IA → Gateway Sentry → Servidor MCP local.

**Proposta futura:** Client de IA com controle integrado → Servidor MCP local.

**Legenda:** “A integração nativa é uma proposta futura, ainda não implementada.”

## CONCLUSÕES

No núcleo N-INT, a combinação de interface e código bloqueou 84% das mudanças perigosas e permitiu 88% das benignas entre as decisões válidas. Esses resultados sustentam o uso de evidências complementares no conjunto avaliado, mas também mostram que o julgamento da IA permanece sujeito a erros.

Além da bateria experimental, o trabalho produziu o MCP Sentry, que coloca a verificação de mudanças no caminho de execução. Os registros técnicos documentam bloqueio antes do início em cenários controlados. A contribuição aplicada é vincular a autorização à versão revisada, separando a verificação de integridade, a recomendação da IA e a decisão do operador.

A proteção depende de uma referência e de um ambiente confiáveis e limita-se à rota local e aos arquivos configurados. O piloto completo da candidata atual em clients reais permanece pendente. Como evolução, propõe-se integrar esse controle ao próprio client de IA.

## REFERÊNCIAS

Manter as referências existentes no rodapé. Conferir a bibliografia na edição final do banner.

## Orientação de montagem

Dar maior espaço ao bloco do gateway e ampliar o fluxograma atual. Usar um bloco menor para a integração proposta, com o rótulo de trabalho futuro visível. A conclusão fica em três parágrafos curtos. Não incluir os números de custo e latência retirados do bloco superior como medidas de desempenho do gateway.
