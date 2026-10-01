# MCP Sentry — plano de evolução para a MOSTRATEC

Este plano organiza a evolução do protótipo em cinco etapas, com pedidos para a IA, ações na máquina e critérios de conclusão. O objetivo é chegar a uma demonstração prática, reproduzível e compreensível, com um escopo adequado à MOSTRATEC e ao nível de ensino médio.

## Organização do trabalho

**A sequência principal é 1 → 3 → 4. As etapas 2 e 5 são frentes paralelas.**

```text
1. Definir o protocolo → 3. Fazer o piloto → 4. Executar a validação
          ↕                       ↕                    ↕
2. Ajustes essenciais concluídos; correções pontuais se o piloto exigir

5. Elaborar a proposta e os materiais de comunicação ao longo do projeto
```

A parte relacionada ao usuário da etapa 2 está encerrada por enquanto: implementação concluída na candidata 0.8.0, com usabilidade a confirmar no piloto. Não há nova rodada de melhorias prevista. Se a definição do protocolo ou o piloto revelar um obstáculo concreto, a etapa 2 recebe uma correção pontual; ajustes que impedem um teste precisam ser concluídos antes daquele teste.

A etapa 5 pode começar desde já pela formulação e pelos diagramas. Seus resultados, conclusões e demonstrações serão atualizados conforme as etapas 3 e 4 forem concluídas.

**Prioridade de escopo:** funcionamento completo de três servidores, configuração utilizável e evidência clara. Retomada sofisticada de instalação, GUI completa e compatibilidade com todo o ecossistema MCP ficam fora desta evolução.

### Estado atual das etapas

| Etapa | Estado | Próxima ação |
| --- | --- | --- |
| 1 — Protocolo | Pendente | Definir protocolo, V1/V2, tarefas e caminhos definitivos. |
| 2 — Parte relacionada ao usuário | Encerrada por enquanto | Confirmar usabilidade durante o piloto e corrigir somente obstáculos concretos. |
| 3 — Piloto | Pendente | Após a etapa 1, conectar no client real e exercitar o fluxo completo. |
| 4 — Validação | Pendente | Após o piloto, executar a matriz definida. |
| 5 — Comunicação | Formulação proposta no plano; materiais pendentes | Elaborar diagramas e materiais em paralelo, incorporando resultados quando disponíveis. |

Durante a etapa 2 também foram feitos ajustes internos de segurança/compatibilidade, testes técnicos com Memory, Git e Filesystem, medições de desempenho e empacotamento da candidata. Esses trabalhos preparam as etapas seguintes, mas não equivalem à definição do protocolo, ao piloto nos apps reais ou à execução da matriz de validação. Os pareceres dos testes técnicos são fixtures, não avaliações produzidas pela IA no piloto.

Na limpeza autorizada, as instalações e evidências brutas antigas de `.lab-smoke` foram descartadas, mantendo os registros textuais, o ambiente atual e o wheel atual 0.8.0. Para novas instalações e execuções descartáveis, usar a organização de [laboratorio/README.md](../laboratorio/README.md). O estado confiável do piloto deve continuar fora das áreas graváveis pelo agente. Novos testes exigem preparar novamente os servidores e seus planos.

## Etapa 1 — definir o protocolo de testes

### Objetivo

Definir exatamente o que será testado antes de executar a bateria. Esta etapa pode ser resolvida em uma conversa de planejamento com a IA, acompanhada da inspeção das versões candidatas.

### O que solicitar à IA

> Analise este plano e o estado atual do MCP Sentry. Prepare um protocolo curto de validação prática usando Donna, Filesystem e Git. Inspecione o histórico dos dois servidores externos e proponha versões ou commits exatos para uma atualização legítima com mudança funcional pequena e compreensível. Defina uma tarefa realista por servidor, as cópias com alteração maliciosa controlada, os resultados esperados, os arquivos protegidos e uma tabela de registro. Verifique a viabilidade no Windows e as necessidades de adaptação do Sentry. Justifique a seleção; não presuma compatibilidade nem classifique uma atualização como benigna apenas por ter sido publicada. Nesta etapa, prepare o protocolo e inspecione as fontes; a instalação e a execução ficam para o piloto.

### Seleção recomendada

| Servidor | Tarefa do usuário | Motivo da escolha |
| --- | --- | --- |
| Donna | Consultar compromissos de uma agenda de teste | Aproveita a implementação e a demonstração existentes; acrescenta evidência no client real. |
| Filesystem | Ler dois arquivos fictícios e salvar um resumo em uma pasta autorizada | Tarefa cotidiana, resultado visível e implementação em Node.js. |
| Git | Consultar e explicar alterações de um repositório pequeno de teste | Acrescenta Python, dispensa contas e permite verificar o resultado. |
| Memory, opcional | Registrar informações fictícias e recuperá-las após reiniciar o client | Acrescenta persistência, caso os três servidores principais estejam concluídos. |

Os servidores externos são candidatos do [repositório de referência MCP](https://github.com/modelcontextprotocol/servers). Eles ampliam a diversidade funcional e de runtimes, mas pertencem à mesma origem; o teste não representa todo o ecossistema.

O Filesystem pode receber a pasta permitida por argumento. O Memory, se incluído, deve usar um arquivo persistente fora da cópia de código. O repositório manipulado pelo Git também fica separado do código do servidor e do estado confiável do Sentry.

### O que fazer na máquina

1. Conferir quais clients estão disponíveis e registrar suas versões. A proposta é Codex como principal e Claude Desktop como segundo client.
2. Conferir os runtimes disponíveis: Python e Node.js. A instalação do que faltar será feita na preparação do piloto.
3. Inspecionar os arquivos e versões da Donna já disponíveis no projeto.
4. Organizar uma pasta de laboratório com áreas separadas para código dos servidores, dados fictícios, configurações/estado do Sentry e evidências.
5. Salvar o protocolo e a tabela de registro no repositório, com os caminhos que serão utilizados.

### Estados a definir

| Estado | Preparação | Resultado esperado |
| --- | --- | --- |
| V1 aprovada | Versão fixada e conferida do servidor | A tarefa funciona normalmente. |
| V2 legítima | Versão posterior publicada pelo projeto, com diferença funcional inspecionada | O Sentry detecta a mudança; a IA recomenda uma decisão; após aprovação humana, a tarefa funciona. |
| V1-M alterada | Cópia de V1 modificada no laboratório | O Sentry detecta a mudança antes de iniciar o servidor; a IA analisa o risco; sem aprovação, a tarefa permanece bloqueada. |

Para Filesystem e Git, escolher atualizações publicadas reais. Uma alteração apenas no README ou no número de versão não basta. Registrar origem, versões, diff e justificativa da classificação esperada.

Para Donna, podem ser reutilizadas as versões controladas existentes. Identificar sua atualização benigna como preparada pelos autores, caso não corresponda a uma publicação independente.

A alteração maliciosa deve implementar um comportamento observável com dados fictícios: por exemplo, acrescentar conteúdo não solicitado a uma resposta ou adulterar um resultado conhecido. A descrição da ferramenta pode permanecer igual, para verificar a contribuição da análise do código. Identificar a versão como modificação de laboratório; não atribuir comprometimento ao projeto original.

### Critério de conclusão

- [ ] Três servidores principais e uma tarefa por servidor definidos.
- [ ] Versões/commits exatos e alterações escolhidos, com origem registrada.
- [ ] Resultados esperados definidos antes das execuções.
- [ ] Rota de execução, cobertura dos arquivos e dependências externas descritas.
- [ ] Protocolo e tabela prontos para uso.

## Etapa 2 — ajustes essenciais do usuário, encerrada por enquanto

### Objetivo

Oferecer preparação, configuração e revisão/aprovação utilizáveis para servidores MCP locais dentro das capacidades implementadas: Python e Node.js, ferramentas via stdio. Perfis de Filesystem, Git e MasterTool são facilidades opcionais.

**Estado:** implementação essencial concluída na candidata 0.8.0; etapa encerrada por enquanto. A facilidade de uso será confirmada na etapa 3. O setup reúne a preparação dos formatos delimitados de npx/uvx no mesmo assistente. A preparação ainda usa terminal e confirmação de caminhos/arquivos; não se exige instalação automática para qualquer servidor para encerrar esta rodada.

### O que solicitar à IA se houver um obstáculo no piloto

> A parte relacionada ao usuário da etapa 2 está encerrada por enquanto. Durante o piloto, encontrei o seguinte obstáculo: [descrever o problema, o passo realizado e o resultado observado]. Analise os registros e faça somente a correção necessária para concluir esse fluxo. Preserve a execução pela cópia verificada e a aprovação do operador, atualize o guia e execute os testes pertinentes. Não abra uma rodada geral de melhorias. Não altere a configuração ativa de MCP além do que estiver explicitamente autorizado para o piloto.

### Escopo entregue

1. **Preparação genérica e assistida.** `setup` integra instalação fixa de npx/uvx, sugestão de cobertura, descoberta, aprovação e conexão no Codex; pede versão exata quando ausente. Launchers com cwd explícito e formatos avançados seguem a rota manual. A listagem de hashes no terminal é limitada, mantendo a referência completa no estado. `prepare-server` prepara script/módulo Python ou arquivo de entrada Node com seleção declarada. `materialize` converte formatos comuns de `npx`/`uvx` com versão exata para instalação local e lançamento direto na cópia. Opções não convertíveis seguem procedimento manual genérico, sem encaminhar o gerenciador ao backend. Perfis conhecidos são opcionais.
2. **Cobertura dos arquivos e evolução estrutural.** Seleção declarada de módulos, dependências locais e configurações, com separação de dados mutáveis, caches, credenciais e ambientes virtuais e indicação das dependências externas confiadas. A seleção atual é comparada com o snapshot aprovado, registrando arquivos adicionados/removidos/alterados, raízes anteriores/atuais/ausentes e mudanças na configuração. A troca de `.dist-info` preserva a baseline e permite gerar o dossiê. Cobertura nova exige promoção separada do envelope, vinculada à versão revisada.
3. **Aprovação de atualização.** Seleção interativa do servidor, apresentação do parecer e decisão do operador, sem copiar manualmente vários caminhos e hashes. A aprovação é vinculada internamente à versão efetivamente revisada.
4. **Atualização do catálogo.** Descoberta autorizada do catálogo da versão revisada, apresentação das diferenças e nova revisão conjunta quando os metadados mudam. Aceitar o código e descobrir o catálogo são ações distintas; iniciar a descoberta exige autorização específica do operador.
5. **Mensagens e documentação.** Referência à interface de revisão correspondente ao servidor, `pacote-usuario/` como entrega ao usuário e `desenvolvimento/gateway/` como fonte principal e guia de preparação, conexão, uso, bloqueio e aprovação. A clareza das instruções nos clients reais será conferida no piloto.
6. **Verificações internas e desempenho.** Tratamento de notificações intercaladas, negociação das versões suportadas e testes técnicos de integridade/execução. O tempo completo até a primeira resposta foi medido: Filesystem 61,249 s e Memory 50,673 s em uma amostra técnica por fase. Essas medições não encerram o piloto nem tornam uma otimização condição para fechar a parte relacionada ao usuário; registrar o impacto no uso real na etapa 3.

### O que fazer na máquina a partir de agora

1. Usar a candidata 0.8.0 e o guia existente na preparação do piloto, após definir o protocolo.
2. Durante a etapa 3, registrar dificuldades de configuração, mensagens, revisão/aprovação e tempo de espera. Encaminhar à IA somente obstáculos concretos que precisem de correção.
3. Se houver correção, atualizar o pacote e o guia e executar os testes pertinentes.
4. Antes da etapa 4, fixar a distribuição e o hash que serão usados na validação. Repetir execuções afetadas por correções posteriores.

### Critério de conclusão

- [x] Assistente setup integrado aos formatos delimitados de npx/uvx, com cancelamentos e preservação da configuração verificados.
- [x] Preparação genérica implementada para Python e Node, com conversão local dos formatos delimitados de npx/uvx e rota manual documentada.
- [x] Servidores reais foram instalados e exercitados via cliente técnico stdio pela preparação genérica, sem perfil específico.
- [x] Alteração bloqueia antes do início; revisão e decisões vinculadas permitem executar depois da aprovação. Pareceres dos testes são fixtures técnicas.
- [x] Troca de .dist-info e inclusão/remoção de arquivos produzem dossiê mantendo a baseline; cobertura exige decisão separada.
- [x] Testes pertinentes e limites documentados em `documentacao/GUIA_PILOTO.md` e no registro técnico da candidata.

**Verificação futura, pertencente à etapa 3:** conexão e tarefa nos apps reais, com estado protegido por permissões do operador. O estado dos testes técnicos é descartável e gravável pelo agente. Essa verificação não mantém a etapa 2 aberta.

Estado da implementação: `desenvolvimento/gateway/` é o pacote principal; a candidata 0.8.0 integra ao setup a preparação genérica entregue na 0.7.0. Os testes novos usam configurações descartáveis e fixtures; não constituem o piloto em clients reais. A verificação técnica usou Memory como servidor adicional sem perfil (persistência externa ao código), Git por conversão genérica de uvx e Filesystem por preparação genérica. Isso não acrescenta Memory à matriz principal: continua sendo uma verificação de integração. A escolha de V1/V2 publicadas, das tarefas e dos caminhos definitivos permanece na etapa 1. Resumo histórico dos servidores reais: `documentacao/VALIDACAO_0.7.0.md`. Validação da melhoria: `documentacao/VALIDACAO_0.8.0.md`; as evidências brutas anteriores foram descartadas na limpeza autorizada.

**Decisão de encerramento:** basta a entrega essencial atual para fechar esta rodada. Melhorias adicionais só serão abertas se a etapa 1 ou o piloto revelar uma necessidade concreta. Investigação ou otimização adicional de desempenho é trabalho complementar, não uma pendência obrigatória desta etapa.

## Etapa 3 — fazer um piloto completo com Filesystem

### Objetivo

Exercitar o fluxo completo em um servidor e um client antes de repetir o procedimento. Esta etapa começa após a definição do protocolo e depende dos ajustes da etapa 2 necessários ao Filesystem.

**Estado:** pendente. Os testes técnicos da candidata não substituem este piloto.

### O que solicitar à IA

> Execute comigo o piloto do Filesystem no Codex usando o protocolo aprovado. Prepare e instale as versões fixadas e os dados fictícios, configure o Sentry e oriente os pedidos que devo fazer no client. Verifique que o servidor executa a cópia protegida, que não existe uma entrada direta ativa para o mesmo servidor durante o teste protegido e que as chamadas passaram pelo MCP. Conduza V1, V2 legítima e V1-M, preservando logs e resultados. Explique quais ações exigem que eu reinicie o client, envie um pedido ou aprove uma versão. Registre falhas e encaminhe as correções necessárias para a etapa 2.

### O que fazer na máquina

1. Instalar Node.js, caso necessário, e instalar/preparar localmente as versões fixadas do Filesystem.
2. Criar dois arquivos fictícios e uma pasta de saída. Mantê-los fora do código protegido e do estado confiável do Sentry.
3. Testar V1 diretamente no client para confirmar que a instalação original funciona.
4. Instalar/atualizar o pacote Sentry e preparar a proteção da instalação escolhida.
5. Conferir e aprovar V1; substituir a conexão direta pela execução via Sentry e pela interface de revisão.
6. Reiniciar/reconectar o client conforme necessário e confirmar as ferramentas disponíveis.
7. Executar os três cenários abaixo, restaurando dados e encerrando conexões anteriores entre eles.

### Roteiro do piloto

**V1:** pedir ao client que leia os dois arquivos pelo Filesystem e salve um resumo na pasta de saída. Conferir as chamadas MCP e o arquivo produzido.

**V2 legítima:** substituir os arquivos de código cobertos pela atualização selecionada, mantendo a referência V1 aprovada. Fazer novamente o pedido e observar o bloqueio. Solicitar a revisão, registrar o parecer, realizar a aprovação como operador e estabelecer uma nova conexão. Repetir a tarefa e conferir o resultado.

**V1-M:** restaurar V1 e sua referência aprovada, aplicar a modificação controlada e repetir o pedido. Solicitar a revisão e registrar o parecer. Conferir a ausência de início do servidor e de efeito da tarefa protegida. O comportamento da versão alterada será conferido separadamente pela rota direta de controle.

Pedidos ao client devem mencionar a ferramenta MCP escolhida. No Codex, conferir que o agente não realizou a tarefa por ferramentas de arquivo ou shell disponíveis em paralelo.

### Confirmação da usabilidade

Durante o piloto, observar se o usuário consegue:

- Preparar e conectar o servidor seguindo o guia.
- Entender o bloqueio e solicitar a revisão.
- Aprovar a atualização sem ajuda constante nem copiar hashes manualmente.
- Concluir a tarefa com mensagens compreensíveis e tempos de espera registrados.

Medir a primeira chamada e as chamadas seguintes na mesma sessão para entender o impacto do custo de início. Registrar dificuldades e corrigir apenas as que atrapalham concretamente o fluxo; a confirmação de usabilidade não abre automaticamente uma rodada de aperfeiçoamento da etapa 2.

### Critério de conclusão

- [ ] Instalação e tarefa normal verificadas no client real.
- [ ] Atualização legítima detectada, revisada e aprovada pelo procedimento.
- [ ] Alteração maliciosa controlada bloqueada antes do início do servidor.
- [ ] Parecer da IA e evidência técnica registrados separadamente.
- [ ] Procedimento reproduzível, com dificuldades e correções anotadas.

Uma recomendação errada ou uma recusa da IA é um resultado observado. Registrar a ocorrência; não ajustar o cenário apenas para obter a resposta desejada.

## Etapa 4 — executar e registrar a validação prática

### Objetivo

Aplicar o procedimento do piloto à matriz pequena de testes. Esta etapa vem depois da etapa 3 e dos ajustes indispensáveis da etapa 2.

### O que solicitar à IA

> Prepare a execução da matriz definida no protocolo com a versão fixada do Sentry. Reutilize o procedimento do piloto, configure Donna e Git no client principal e Filesystem no segundo client, e organize os registros de cada execução. Faça os controles diretos nas instalações de laboratório e preserve as evidências das chamadas, dos resultados e do ciclo de vida. Ao final, produza uma tabela descritiva com êxitos, erros, recusas e limitações, sem misturar bloqueio por integridade com acerto da avaliação da IA e sem extrapolar para servidores não testados.

### Matriz recomendada

| Bloco | Combinações | Execuções |
| --- | --- | --- |
| Codex com Sentry | Donna, Filesystem e Git × V1, V2 e V1-M | 9 |
| Codex sem Sentry | Os mesmos três servidores e estados, pela conexão direta | 9 |
| Claude Desktop com Sentry | Filesystem × V1, V2 e V1-M | 3 |
| **Total** | | **21** |

As execuções válidas do piloto podem compor as nove protegidas do Codex se usarem o mesmo protocolo e a mesma versão final do Sentry. Se mudanças posteriores afetarem seu comportamento, repetir as execuções afetadas.

O segundo client verifica portabilidade somente para Filesystem. Memory é uma extensão opcional, após concluir os três servidores principais, e exige atualizar previamente a matriz e o protocolo.

### O que fazer na máquina

1. Instalar/preparar Donna e as versões fixadas do Git, incluindo Python e o executável Git necessários.
2. Criar uma agenda de teste para Donna e um pequeno repositório Git com alterações conhecidas. Usar as versões controladas da Donna já disponíveis quando adequadas ao protocolo.
3. Aplicar o Sentry aos três servidores no Codex, cada um com manifesto e estado próprios.
4. Executar os nove cenários protegidos, seguindo o roteiro do piloto.
5. Alternar para a rota direta no ambiente de laboratório e repetir os nove controles. Manter apenas a rota correspondente ativa em cada bloco para evitar ambiguidades.
6. Instalar/configurar as interfaces de execução e revisão do Filesystem no Claude Desktop e executar seus três cenários.
7. Salvar registros, conferir resultados e gravar uma demonstração curta do fluxo completo.

Nos controles diretos das versões alteradas, o comportamento deve ser funcional e observável com dados fictícios. O controle ajuda a demonstrar o efeito que o Sentry impediu; a ausência de início é verificada também pelos registros do próprio gateway.

### Roteiro de cada execução protegida

1. Restaurar o estado inicial dos dados e selecionar a versão prevista.
2. Abrir uma conversa nova e enviar o pedido definido.
3. Conferir a chamada MCP e o resultado observado.
4. Se houver bloqueio, solicitar a revisão e registrar a recomendação da IA.
5. No cenário legítimo, realizar a aprovação como operador, reconectar e repetir a tarefa.
6. Conferir respostas, arquivos e registros do ciclo de vida.

### Registro mínimo

| Campo | O que registrar |
| --- | --- |
| Identificação | Servidor, cenário, data e identificador da execução |
| Ambiente | Versões de client, modelo, servidor e Sentry |
| Entrada | Pedido enviado e alteração aplicada |
| Expectativa | Resultado definido no protocolo |
| Integridade | Mudança detectada ou não; servidor iniciado ou não |
| Avaliação da IA | Recomendação e justificativa; erro ou recusa, se ocorrer |
| Decisão humana | Aprovação realizada ou bloqueio mantido |
| Resultado | Resposta, arquivo ou outro efeito efetivamente observado |
| Operação | Tempo e dificuldades |
| Evidência | Caminhos para logs, diffs, transcrição ou gravação |

O bloqueio inicial de V2 é esperado, mesmo sendo uma atualização legítima. A contribuição da análise semântica aparece na avaliação posterior. Bloqueio por hash não é contado como acerto da IA.

### Critério de conclusão

- [ ] Matriz executada, com falhas e tentativas de preparação explicitadas.
- [ ] Resultados verificáveis e evidências preservadas.
- [ ] Tabela descritiva pronta, sem alegação de eficácia universal.
- [ ] Vídeo curto do fluxo completo disponível.
- [ ] Conclusões limitadas aos servidores, versões, tarefas e clients testados.

## Etapa 5 — formular a prova de conceito e preparar a comunicação, em paralelo

### Objetivo

Explicar o que o protótipo demonstra e como seu mecanismo poderia ser incorporado aos clients de IA. Esta etapa começa desde já e acompanha os resultados dos testes.

### O que solicitar à IA

> Desenvolva a comunicação do MCP Sentry como prova de conceito, usando este plano e as evidências disponíveis. Prepare a formulação central, um fluxograma da arquitetura atual e um desenho simples da possível arquitetura nativa. Escreva trechos proporcionais para relatório, banner, apresentação oral e roteiro de vídeo. Identifique o que já foi implementado e testado, o que está em validação e o que é proposta futura. Atualize os trechos de resultados após a etapa 4, sem antecipar êxitos ou sugerir uma integração nativa já realizada.

### O que precisa ser desenvolvido

O gateway existente, com os ajustes da etapa 2 e a validação das etapas 3 e 4, é a implementação da prova de conceito. Para esta frente, produzir:

- Uma formulação clara do projeto.
- Um fluxograma do funcionamento implementado.
- Uma comparação simples entre a arquitetura atual e a proposta nativa.
- Textos e roteiro de apresentação apoiados nas evidências.
- Opcionalmente, uma tela ilustrativa de aprovação, identificada como proposta.

Criar um client próprio ou alterar internamente um client de terceiros não integra este plano.

### Formulação recomendada

> O MCP Sentry é uma prova de conceito de verificação de integridade e revisão assistida por IA de alterações em servidores MCP locais. Implementado como gateway, explora um mecanismo que poderia ser incorporado nativamente aos clients de IA.

### Explicação oral curta

> Hoje implementamos esse controle por meio de um gateway. A proposta futura é que o próprio client verifique mudanças antes de iniciar o servidor, solicite a análise da IA e apresente ao usuário a decisão de autorizar.

### Arquitetura a explicar

**Atual:** client de IA → gateway Sentry → servidor MCP protegido. Quando há mudança, a revisão ocorre pela interface separada, e a aprovação cabe ao operador.

**Proposta:** client com controle integrado → servidor MCP. O client administra a versão aprovada, verifica alterações, solicita a análise da IA e apresenta a decisão ao usuário.

O fluxo central é: versão aprovada → comparação antes de iniciar → mudança detectada → análise pela IA → decisão humana → execução autorizada.

A proposta nativa precisa manter o estado confiável e a aprovação fora do alcance de escrita do agente. Estar fora da pasta do projeto, sozinho, não garante isso. O parecer da IA continua sendo uma recomendação; o controle de execução é determinístico.

### O que fazer na máquina e nos materiais

| Material | Ação concreta | Quando preparar |
| --- | --- | --- |
| Relatório | Inserir arquitetura implementada, método, resultados, limites e proposta de integração nativa | Estrutura desde já; resultados após os testes |
| Banner | Inserir formulação curta, fluxograma atual e indicação de integração nativa como trabalho futuro | Rascunho desde já; versão final após os resultados |
| Apresentação oral | Preparar explicação do problema, evidências, demonstração e proposta futura | Desde já, atualizando os resultados |
| Vídeo | Gravar o Sentry funcionando e encerrar com uma tela sobre a proposta futura | Roteiro desde já; gravação com o fluxo validado |
| Diagramas | Exportar arquitetura atual e proposta em formatos adequados aos materiais | Desde já, conferindo com o funcionamento final |

Nos materiais, distinguir a pesquisa investigativa sobre o julgamento dos modelos, a validação prática do gateway e a proposta de função nativa. O protótipo cobre a rota local configurada, os arquivos declarados e as capacidades efetivamente implementadas; depende de uma versão inicial confiável e de um ambiente confiável. Esses limites devem acompanhar as conclusões.

### Critério de conclusão

- [ ] Formulação adotada e consistente entre os materiais.
- [ ] Diagramas correspondem à implementação final e identificam a proposta futura.
- [ ] Relatório e apresentação incorporam resultados observados e limitações.
- [ ] Demonstração mostra o fluxo completo em um client real.
- [ ] Nenhum material apresenta a integração nativa como já desenvolvida.

## Referências de trabalho

- [Pacote do usuário e instruções atuais](../pacote-usuario/README.md).
- [Demonstração controlada já registrada](../prototipo-feicit/documentacao/RESULTADO_DA_DEMONSTRACAO_CONTROLADA.md).
- [Fluxo de revisão pelo client](../prototipo-feicit/documentacao/AVALIACAO_SEMANTICA_CLIENTE.md).
- [Filesystem MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem).
- [Git MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/git).
- [Memory MCP, opcional](https://github.com/modelcontextprotocol/servers/tree/main/src/memory).

**Estado deste documento:** plano de trabalho atualizado com o encerramento provisório da parte relacionada ao usuário da etapa 2. As etapas 1, 3 e 4 continuam pendentes; a etapa 5 tem formulação proposta e materiais pendentes. Os testes, versões e resultados futuros precisam ser registrados conforme forem definidos e executados.
