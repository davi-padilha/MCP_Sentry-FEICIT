# MCP Sentry — evolução até a MOSTRATEC e diário de bordo

**Versão:** 1.1 — 29/09/2026, incorporando as respostas dos pesquisadores.

**Situação:** planejamento por entregas e dependências, sem datas ou carga horária impostas.

**Base examinada:** commit `5c24cf3`; pacote de usuário `cliente/`, versão declarada `0.5.4`.
**Contexto:** aproximadamente três semanas; ritmo definido pela dupla. Codex e Claude disponíveis no Windows; começar pelo Codex. Claude Pro, GPT Plus e créditos OpenRouter informados pelos autores. Todo o trabalho existente está nesta pasta, sem alterações externas.

**Começo imediato:** A assume M02 (pacote e jornada de uso); B assume M03 e a preparação de S2 em M05 (protocolo e servidor independente). Ambos podem usar IA como assistência documentada, preservando autoria e decisões dos pesquisadores; ver seção 8.

## 1. Direção recomendada

Concluir uma pesquisa com duas etapas claramente separadas: **avaliação experimental da análise de mudanças pela IA**, já realizada, e **validação prática do fluxo completo do MCP Sentry em clientes de IA reais**, ainda a completar. A melhoria de usabilidade serve para tornar esse fluxo instalável, compreensível e repetível por outra pessoa.

Recomendo enquadrar o Sentry como **prova de conceito de um controle de integridade e revisão assistida por IA para servidores MCP locais, que poderia ser incorporado nativamente ao aplicativo de IA**. Hoje, esse controle é implementado por um gateway externo. A integração nativa é uma proposta arquitetural, não uma implementação já entregue.

Título provisório para discussão: **“MCP Sentry: verificação de integridade e revisão de mudanças assistida por IA em servidores MCP locais”**. Não mudar o título oficial inscrito sem conferir as exigências da organização.

O objetivo das três semanas não é transformar o protótipo em produto universal. É fechar uma cadeia de evidência convincente: problema → investigação → implementação → uso real em mais de um servidor → resultados, falhas e limites. Para uma feira de ensino médio, uma demonstração pequena, reproduzível e bem explicada é mais defensável que muitas funcionalidades incompletas.

## 2. Diagnóstico do que existe

Os caminhos desta seção são relativos à raiz do repositório. “Implementado” não significa “validado em aplicativo real”.

| Área | Evidência encontrada | Interpretação para o planejamento |
|---|---|---|
| Pesquisa investigativa | `pesquisa/01_casos_finais/README.md`: 90 casos e 150 entradas C1/C2/D; relatórios em `pesquisa/02_resultados/` | Preservar a bateria e os dados; não refazer a campanha como requisito da MOSTRATEC |
| Campanha principal | `01_campanha_principal/analise_final/LEIA_PRIMEIRO_RESULTADOS_DA_CAMPANHA.md`: 1.500 unidades com desfecho terminal | São resultados da avaliação investigativa, não 1.500 testes do gateway em aplicativos |
| Extensão | `02_extensao_multimodelo/analise_descritiva/LEIA_PRIMEIRO_RESULTADOS_DA_EXTENSAO.md`: 450 pares, 900 unidades, 23 falhas terminais | Manter denominadores e limitações; não confundir concordância entre repetições com acurácia |
| Pacote para usuário | `cliente/README.md`, `cliente/pyproject.toml` | Já há distribuição independente da Donna, Python 3.11+, sem dependências declaradas do gateway |
| Instalação assistida | `cliente/mcp_sentry_gateway/setup.py` | Lê uma configuração Codex, seleciona servidor elegível, descobre catálogo, pede aprovação, faz backup, troca entradas e roda diagnóstico |
| Preparação e diagnóstico | `cliente/mcp_sentry_gateway/onboarding.py` | `prepare-codex` e `doctor` existem; diagnóstico local não equivale a conexão funcional no aplicativo |
| Proteção e revisão | `core.py`, `gateway.py`, `mcp_facade.py`, `review.py` dentro de `cliente/mcp_sentry_gateway/` | Comparação com referência aprovada, cópia verificada, revisão separada e autorização local fora das ferramentas MCP |
| Compatibilidade inicial | README e testes de `cliente/` | Ferramentas via stdio; setup para Python com script `.py` e um adaptador específico do MasterTool. Não é suporte genérico a `npx`, `uvx`, HTTP, recursos ou prompts |
| Evidência prática anterior | `gateway/documentacao/RESULTADO_DA_DEMONSTRACAO_CONTROLADA.md` | Demonstração técnica de 12/09 com Google Calendar e alteração inerte, usando cliente JSON-RPC controlado; documento exclui explicitamente validação pela interface MCP nativa do Codex |
| Gmail | `gateway/README.md` e `gateway/documentacao/PLANO_DO_TESTE_COM_GMAIL.md` | Ensaio planejado; não tratar como resultado executado nesta cópia |
| Outras aplicações | Testes `test_gateway_universal.py` e adaptação MasterTool em `test_setup.py` | Evidência automatizada com servidores/fixtures; não prova instalação real do MasterTool nem interoperabilidade ampla |

### Verificação feita nesta análise

Foi executada a suíte `python -m unittest discover -s testes_cliente -v` usando o Python fornecido pelo ambiente Codex: **30 testes encontrados; 29 passaram e 1 foi ignorado**, sem falhas. O teste ignorado depende da criação de link simbólico, indisponível por privilégio do Windows. O comando `python` do PATH não funcionou neste ambiente; isso, isoladamente, não é defeito do Sentry.

Esses testes cobrem preparação, cancelamentos, preservação de configuração, mudanças durante aprovação, integração com servidor mínimo e bloqueio. Não foi feita, nesta análise, uma nova campanha científica, execução de clientes reais ou auditoria completa de segurança. As demais suítes do repositório não foram reexecutadas.

### Pontos que precisam ser corrigidos ou completados

1. **Duas implementações com o mesmo nome de pacote.** `cliente/mcp_sentry_gateway/` e `gateway/codigo_gateway/mcp_sentry_gateway/` diferem em vários módulos. Recomendação: usar `cliente/` como fonte da versão MOSTRATEC, documentar `gateway/` como material histórico da demonstração e identificar regressões essenciais a portar. Não apagar o histórico nem presumir que os testes antigos exercitam a nova versão.
2. **Entrada documental desatualizada.** O README principal orienta a começar pelo gateway histórico e não apresenta `cliente/`. O relatório principal também aponta para `documentacao/RESULTADOS_E_LIMITACOES.md`, que não foi encontrado nesta árvore. Corrigir a navegação e localizar o documento original com os autores; não reconstruir conclusões ausentes por suposição.
3. **Ajuda da CLI incompleta.** `cli.py` encaminha `setup`, `prepare-codex` e `doctor` antes do parser principal, mas eles não aparecem nas opções do parser geral. A ajuda principal deve mostrar todos os comandos e a jornada recomendada.
4. **Retomada após interrupção.** O setup admite reutilizar uma pasta `config` vazia, mas rejeita estado já preenchido. Cancelar após preparar ou aprovar deixa um estado intermediário que exige orientação manual. Implementar retomada explícita e segura ou, no mínimo, um guia verificado para cada estado, sem mandar apagar a pasta indiscriminadamente.
5. **Seleção dos arquivos protegidos.** No Python comum, a sugestão inicial cobre apenas o script de entrada. Módulos e configurações necessários dependem do usuário. Mostrar claramente o escopo incluído/excluído e testar um servidor com múltiplos arquivos. Não prometer descoberta automática completa de dependências.
6. **Ciclo de revisão difícil para usuário.** A liberação usa identificadores e hashes longos; distinguir “permitir uma execução”, “aceitar como nova referência” e “aprovar mudança na configuração de execução”. Priorizar um guia curto e, se couber, comando local assistido que preserve as verificações e a confirmação humana.
7. **Diagnóstico limitado.** `doctor` verifica arquivos/configuração, mas não demonstra que o aplicativo conectou, não executa a ferramenta e não examina todas as camadas de configuração. Apresentar esse limite na saída e separar “configuração pronta” de “teste no aplicativo concluído”.
8. **Desconexão e recuperação.** Há backup e rollback automático em certas falhas do setup; falta uma jornada de recuperação/desinstalação fácil de encontrar no manual. Documentar como restaurar somente as entradas envolvidas, preservando alterações posteriores do usuário.
9. **Compatibilidade precisa ser medida.** O gateway implementa negociação das versões `2025-03-26` e `2025-06-18`; testar as versões efetivas dos clientes escolhidos. Não ampliar protocolo, linguagens e capacidades ao mesmo tempo durante estas três semanas.
10. **Estado fora do alcance da IA é uma premissa.** Guardar o estado fora do projeto não prova que o agente não pode escrevê-lo. Registrar permissões efetivas e outros acessos do aplicativo. Se a proteção não for imposta pelo ambiente, apresentá-la como premissa, nunca como isolamento comprovado.

## 3. Enquadramento científico e arquitetural

### Perguntas a responder

- **Investigação anterior:** nas condições e casos avaliados, a IA consegue distinguir mudanças benignas e perigosas? Explicar C1, C2, D, gabaritos, denominadores e erros a partir dos materiais originais. Não sintetizar tudo em uma porcentagem genérica de “eficácia”.
- **Nova etapa:** em aplicativos reais, o Sentry mantém um servidor local parado quando os arquivos/configuração inspecionados mudam, permite a revisão pelo modelo do aplicativo e preserva a decisão humana antes de voltar a executar?
- **Transferência:** esse fluxo funciona em pelo menos dois servidores distintos, incluindo um além da Donna, dentro do escopo declarado?
- **Usabilidade:** outra pessoa consegue instalar, entender um bloqueio e concluir a recuperação seguindo o guia?

### Por que vale a pena propor uma função nativa

A arquitetura MCP atribui ao **host**, isto é, ao aplicativo de IA, o controle do ciclo de vida, das permissões e das decisões do usuário. Por isso, situar ali a verificação antes de iniciar o servidor é uma proposta coerente com a arquitetura. Essa é uma inferência de projeto, não uma obrigação do protocolo nem uma promessa de adoção. Fonte: [arquitetura MCP, versão 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/architecture), consultada em 29/09/2026.

A OWASP já recomenda controles de integridade de descrições/esquemas e outros mecanismos de segurança MCP. Portanto, não alegar que o Sentry inventou o uso de hashes ou a revisão de ferramentas. A contribuição a defender é a combinação implementada, sua avaliação investigativa e a demonstração de revisão de mudanças de código/configuração com o modelo do próprio aplicativo. Fonte: [OWASP MCP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html), consultada em 29/09/2026. A originalidade exata ainda requer a revisão bibliográfica dos autores.

| Alternativa | Benefício | Custo/limite | Decisão para três semanas |
|---|---|---|---|
| Gateway externo atual | Permite experimentar sem alterar o aplicativo | Configuração extra, duas entradas MCP e possibilidade de rota direta paralela | Implementar e validar esta opção |
| Função nativa do host | Poderia reunir configuração, revisão e autorização na interface e controlar o lançamento | Exige alteração do aplicativo e armazenamento/autorizações confiáveis; não elimina falhas da IA | Especificar e discutir, sem construir um novo cliente |
| Alterar o protocolo MCP | Eventualmente padronizaria intercâmbio adicional | Exige consenso e escopo muito maior | Fora do trabalho até a feira |

**Fluxo proposto para uma integração nativa futura:** registrar uma versão inicialmente confiável → comparar artefatos antes de iniciar → impedir lançamento se mudou → apresentar diferenças como dados não confiáveis ao modelo → mostrar recomendação e evidências ao usuário → registrar decisão humana vinculada à versão → executar os artefatos verificados ou manter bloqueio.

A função nativa precisaria proteger a referência aprovada contra escrita pelo agente, controlar todas as rotas de lançamento sob sua responsabilidade e invalidar aprovações quando os artefatos mudarem. A interface humana de autorização deve ficar fora do poder decisório do modelo. Desenhar esse fluxo em uma página; não confundir um desenho de interface com implementação nativa.

### Limites que devem aparecer no relatório e na apresentação

- Hash detecta diferença, não intenção maliciosa. Uma mudança benigna também exige revisão.
- IA recomenda; o bloqueio inicial é determinístico. Bloquear uma alteração não comprova acerto semântico do modelo.
- O servidor é local, via stdio, com ferramentas e arquivos declarados. Interpretador, bibliotecas externas, dados mutáveis e outros componentes não inspecionados permanecem fora da cobertura.
- A descoberta inicial executa o servidor original: exige confiança inicial e não é uma varredura segura de código desconhecido.
- A comparação do catálogo em runtime ocorre depois da inicialização do backend. Nesse caso não alegar bloqueio “antes de qualquer execução”.
- O gateway não é sandbox e não controla conexões diretas, processos já abertos ou todo o computador. A cópia verificada não transforma dependências externas em confiáveis.
- Dossiês podem conter tentativas de instruir o modelo. Tratar conteúdo como evidência não confiável reduz ambiguidade, mas não demonstra imunidade a prompt injection.
- O campo de origem do parecer não autentica a identidade do modelo. Registrar a versão indicada pelo aplicativo como informação observada.
- Poucos testes em clientes reais demonstram viabilidade nas combinações testadas, não segurança universal nem uma nova estimativa robusta de acurácia.

## 4. Escopo e prioridades

**Obrigatório:** uma versão do pacote claramente identificada; jornada de instalação/revisão/recuperação documentada; dois servidores distintos; execução real em pelo menos um aplicativo; evidências do bloqueio antes do lançamento para alterações inspecionadas; revisão da IA e decisão humana separadas; relatório que una as duas etapas sem misturar métricas.

**Escopo inicial acordado:** Codex no Windows, dois servidores, três cenários principais e duas repetições por combinação. Melhorar a ajuda e o diagnóstico e fazer ensaio de usabilidade com os dois pesquisadores trocando papéis. Claude no Windows é extensão opcional após esse núcleo funcionar.

**Somente se sobrar tempo:** terceiro servidor, participante externo para usabilidade, comando local assistido de revisão, adaptação adicional de launcher.

**Adiar:** interface gráfica completa, marketplace, extensão nativa para cliente fechado, nova campanha extensa de modelos, servidores remotos/HTTP, suporte geral a `npx`/`uvx`, sandbox próprio e operações Gmail reais. Nenhum desses itens é necessário para demonstrar o ponto central.

## 5. Protocolo prático enxuto

### Seleção da matriz antes do piloto

Aplicativos disponíveis foram confirmados pelos pesquisadores; a compatibilidade com o Sentry ainda será testada:

- **Cliente A:** Codex no Windows, prioridade inicial. Registrar versão e modelo efetivamente usados.
- **Cliente B:** Claude no Windows, opcional. Confirmar modalidade/versão do aplicativo antes de configurar MCP local. Documentação antiga de integração não vale como validação da versão atual.
- **Servidor S1:** Donna com provedor simulado e dados sintéticos, aproveitando o material existente.
- **Servidor S2 recomendado:** [Time MCP Server, do repositório de referência MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/time). Tem funções de horário/conversão de fuso, implementação Python e dispensa credenciais de serviço externo. É um candidato de baixo custo operacional para provar independência da Donna; ainda não foi instalado ou validado com o Sentry nesta análise. Fixar commit e dependências antes do piloto.

**Adaptação a verificar para S2:** o modo documentado `python -m mcp_server_time` não é aceito pelo setup atual, que espera um script `.py`. Preparar um launcher local mínimo e incluir tanto esse launcher quanto o código real de `mcp_server_time` nas raízes inspecionadas. Demonstrar que o módulo importado vem da cópia verificada, não apenas de `site-packages`. Não basta proteger um script que importa código externo mutável. Uma alternativa é adaptar o suporte a módulos, apenas se isso não ampliar demais o escopo. Bibliotecas de terceiros continuam sendo dependências confiadas e devem ter versões registradas.

Para o Time, usar conversão com entrada conhecida e gabarito definido no ambiente de teste. P1 pode ser refatoração sem efeito funcional; P2 pode adulterar intencionalmente o resultado ou acrescentar escrita local indevida simulada. Isso demonstra alteração de integridade, sem alegar que seja um ataque publicado contra o servidor. Se houver incompatibilidade impeditiva, registrar a tentativa e escolher outro servidor Python simples com código local e utilidade real. MasterTool não é requisito; sua disponibilidade não foi confirmada.

O servidor `echo` dos testes serve para diagnóstico de protocolo, mas não deve ser a única evidência de uso além da Donna. Se for impossível obter um segundo servidor independente, apresentar a limitação explicitamente. Não chamar uma nova fixture feita apenas para o Sentry de validação independente.

Selecionar S2 por compatibilidade efetiva: stdio, ferramentas suportadas, runtime disponível, dependências identificadas e ausência de efeitos externos no ensaio. Fixar origem, versão/commit e licença. Descrever qualquer adaptação feita; não ocultar dificuldades de integração.

### Cenários principais

| ID | Preparação e ação no cliente real | Resultado esperado | Evidência necessária |
|---|---|---|---|
| P0 — referência íntegra | Aprovar versão conhecida, abrir conexão nova e pedir uma ação simples | Ferramenta executa pela rota Sentry e devolve o resultado esperado | Chamada MCP no aplicativo, resposta e log de lançamento/ação |
| P1 — alteração benigna | Em cópia de laboratório, mudar código sem introduzir comportamento perigoso; reiniciar conexão | Bloqueio inicial; IA lê diferenças e recomenda permitir; continua parado até decisão humana; após liberação executa | Hashes antes/depois, bloqueio, dossiê, parecer, autorização local e sucesso posterior |
| P2 — alteração perigosa inerte | Introduzir mudança com efeito indevido simulado, sem comunicação externa; reiniciar conexão | Bloqueio antes do backend, revisão identifica risco e recomenda bloquear | `spawn_attempts = 0` na sessão bloqueada, ausência de ação, parecer e arquivos da mutação |

P1 testa também que um `allow` registrado não libera sozinho. P2 deve ter um marcador local observável caso a ação fosse executada, ou outra instrumentação equivalente, sem exfiltrar dados. Guardar o gabarito fora do conteúdo dado ao modelo e definir o comportamento esperado antes da coleta.

Se o modelo errar P1/P2, guardar o erro. A proteção mecânica e a recomendação semântica são resultados separados. Uma aprovação humana não pode “corrigir” retrospectivamente a nota da IA.

### Quantidade proposta e controles

- Núcleo: **1 cliente (Codex) × 2 servidores × 3 cenários × 2 repetições = 12 execuções protegidas**. Cada repetição usa conexão/conversa nova e restauração documentada do estado inicial.
- Fazer ainda **2 verificações diretas da versão benigna**, uma por servidor, para comprovar funcionamento sem gateway. Depois desativar a rota direta antes da execução protegida. Total inicial: 14 sessões principais/controles.
- Controles técnicos adicionais, uma vez na versão candidata: mudança de configuração de execução exige promoção específica; autorização antiga não vale para novo hash; retomada de instalação preserva dados; catálogo divergente é bloqueado antes de `tools/call`, reconhecendo que o backend já iniciou.
- Extensão opcional no Claude: repetir a mesma matriz, chegando a 24 execuções protegidas + 4 controles diretos no total. O núcleo com Codex já é uma entrega válida; sem essa extensão, declarar que portabilidade entre aplicativos não foi demonstrada.
- Se o segundo cliente funcionar apenas parcialmente, registrar incompatibilidade e causa. Não removê-lo silenciosamente da tabela. O objetivo é caracterizar viabilidade e limites, não produzir uma tabela artificialmente perfeita.

As duas repetições verificam repetibilidade básica, não fornecem poder estatístico para generalizações. Não é necessário reexecutar centenas de avaliações semânticas.

Usar inicialmente o modelo do aplicativo, conforme a pergunta de pesquisa. Créditos OpenRouter ficam como recurso opcional para investigação adicional; uma revisão por API externa não substitui a evidência de revisão pelo próprio cliente de IA. Não há necessidade inicial de comprar serviços.

### Procedimento por execução

1. Registrar ID, data, pesquisador, versão do pacote, cliente, modelo exibido, sistema operacional, servidor, versão do protocolo, manifesto sanitizado e hashes.
2. Fechar as conexões anteriores. Preparar baseline conhecida, aplicar apenas a mudança prevista e registrar estado inicial. Não reutilizar uma autorização de outra execução.
3. Confirmar que a sessão experimental só oferece a rota protegida e que o armazenamento de referência respeita as premissas documentadas.
4. Executar um pedido fixo pelo mecanismo MCP nativo do aplicativo. Não substituir por Python, terminal ou cliente JSON-RPC auxiliar. Se o agente contornar a rota, marcar desvio de protocolo.
5. Para mudança, pedir leitura/revisão do bloqueio. Pedir registro do parecer em uma mensagem explícita separada. Salvar tanto o texto quanto a chamada de ferramenta efetiva; uma frase “eu revisei” não basta.
6. Em P1, verificar que a recomendação não iniciou o backend; o pesquisador decide localmente e cria nova conexão para a execução autorizada. Em P2, manter bloqueado.
7. Salvar logs e evidências sanitizadas. Registrar falhas, recusas do cliente, timeouts, intervenções e tempo. Não sobrescrever tentativas malsucedidas com o ensaio posterior.

### Métricas e registro

Para cada execução, registrar separadamente: instalação/conexão, chamada real, integridade, lançamento do backend, ação executada, recomendação da IA, decisão humana e resultado funcional. Usar `passou`, `falhou`, `inconclusivo` ou `não aplicável`, com motivo.

Medidas úteis: execuções com resultado esperado/planejadas; bloqueios pré-lançamento/mudanças inspecionadas tentadas; recomendações corretas/revisões previstas, mantendo inconclusivas visíveis; tempo de instalação; tempo de revisão; número de intervenções. Informar números absolutos junto das porcentagens. Se não houver medição de tokens/custo no aplicativo, registrar “não disponível”, nunca zero.

Tempos direto/com Sentry são apenas observações exploratórias com ambiente e estado frio/quente identificados; duas repetições não demonstram diferença estatística de desempenho.

Ao começar a coleta, criar `próximos passos/evidencias/EXP-001/` e equivalentes, contendo ficha, versões/configuração sanitizada, hashes/diff, logs, parecer e captura ou vídeo curto. Criar um índice CSV com uma linha por tentativa. Não incluir tokens, credenciais ou dados pessoais. Se for necessário guardar um original privado, registrar sua localização controlada sem copiá-lo para o repositório.

## 6. Dupla trabalhando em paralelo

Os papéis A/B são provisórios, não atribuições de nomes. Ambos devem entender método, código e resultados; a divisão define quem conduz cada entrega.

| Frente | Pesquisador A — implementação e operação | Pesquisador B — experimento e comunicação | Ponto de encontro |
|---|---|---|---|
| Preparação | Fonte do pacote, ajuda, diagnóstico, recuperação e correções críticas | Revisão da pesquisa anterior, escolha dos casos, gabaritos, fichas e servidor independente | Protocolo fixado e primeiro piloto real antes da coleta |
| Validação | Corrigir defeitos encontrados, preparar versão candidata e apoiar integrações | Executar matriz e organizar evidências/resultados; relatar falhas reproduzíveis | Testes críticos revisados por ambos; congelar versão ao final da coleta |
| Fechamento | Estabilizar instalação, preparar demonstração offline | Fechar relatório, limitações, proposta nativa e materiais da feira | Revisão cruzada dos dados e dois ensaios de apresentação |

**Trabalho independente desde o primeiro dia:** B não precisa esperar o setup ficar pronto para selecionar S2, definir gabaritos e organizar o relatório. A não precisa esperar toda a redação para corrigir a jornada do usuário. Fazer um piloto cedo evita descobrir incompatibilidade apenas na segunda semana.

**Regras de integração:** A conduz alterações em `cliente/` e `testes_cliente/`; B conduz fixtures experimentais, evidências e relatório. Ambos revisam mudanças na fronteira entre versão aprovada, parecer e autorização. Usar branches próprias se trabalham em máquinas separadas. Não editar simultaneamente o mesmo arquivo compartilhado sem combinar; inserir entradas do diário em ordem e resolver conflitos sem apagar registros.

**Rotina:** reunião de 10–15 minutos para impedimentos e próxima entrega; registro ao final de cada sessão; revisão cruzada de evidências. Fixar o commit usado em cada execução. Se uma correção alterar o comportamento medido, repetir as células afetadas e manter os resultados anteriores identificados como outra versão.

## 7. Sequência de entregas e backlog executável

Prioridade P0 = necessária para concluir; P1 = desejável; P2 = extra. Estados permitidos: `a fazer`, `em andamento`, `bloqueado`, `concluído`, `adiado`. Concluir exige evidência vinculada.

| ID / prioridade | Etapa | Responsável | Entrega e critério de conclusão | Dependência | Estado |
|---|---|---|---|---|---|
| M01 / P0 | Preparação | Ambos | Registrar versões dos aplicativos, atribuir A/B, conferir requisitos oficiais e esclarecer uso assistido de IA com orientador/organização | Seções 8 e 10 | a fazer |
| M02 / P0 | Preparação | A | Definir `cliente/` como versão de trabalho ou justificar alternativa; README aponta para ela; import/instalação confirmam origem do pacote | Nenhuma | a fazer |
| M03 / P0 | Preparação | B | Protocolo, gabaritos, pedidos fixos e índice de evidências prontos; separar pesquisa anterior e novo ensaio | Pode começar já | a fazer |
| M04 / P0 | Preparação | A | Ajuda completa, diagnóstico compreensível, cobertura de arquivos e instruções de retomada/recuperação verificadas | M02 | a fazer |
| M05 / P0 | Piloto | B + A | S2 funcional diretamente e primeiro caminho P0/P2 pelo MCP nativo do Codex; provar origem do código executado e salvar evidência | M02, preparação de S2 | a fazer |
| M06 / P0 | Piloto | Ambos | Trocar papéis: cada um segue o guia; registrar tempo, pedidos de ajuda e compreensão de bloqueio/liberação; corrigir impedimentos | M04, M05 | a fazer |
| M07 / P0 | Validação | A | Versão candidata identificada; testes do pacote e regressões críticas portadas passam; limites de compatibilidade registrados | M04–M06 | a fazer |
| M08 / P0 | Validação | B; A apoia | Matriz Codex executada na versão identificada, incluindo falhas e inconclusivos; evidências por tentativa | M03, M07 | a fazer |
| M09 / P1 | Extensão opcional | A + B | Claude validado na mesma matriz, ou incompatibilidade documentada | M08; sem impedir fechamento | a fazer |
| M10 / P0 | Consolidação | Ambos | Revisão cruzada de registros; correções críticas e repetições afetadas; tabela final ligada aos logs | M08 | a fazer |
| M11 / P0 | Em paralelo e fechamento | B; A revisa | Relatório reúne investigação, protótipo, novo método/resultados e limites; figura da proposta nativa e referências | Começar já; M10 para resultados | a fazer |
| M12 / P0 | Fechamento | Ambos | Materiais da feira, demonstração offline de poucos minutos, vídeo e arquivos locais preparados | M01, M10, M11 | a fazer |
| M13 / P0 | Fechamento | Ambos | Dois ensaios completos, conferência de números e arquivos, backup | M12 | a fazer |

Não há estimativa de horas nem calendário diário, por escolha dos pesquisadores. Avançar pelos critérios de conclusão; cortar extras antes de cortar rastreabilidade.

**Pontos de decisão:** se o piloto de S2 não funcionar, suspender melhorias cosméticas e resolver integração; validar o núcleo no Codex antes de ampliar para Claude; após fechar resultados, só corrigir defeitos que comprometem resultados/demonstração e repetir o que for afetado. Reservar margem para comunicar e reproduzir o que existe.

### Aceite de usabilidade

O pesquisador que não implementou a jornada deve conseguir, seguindo apenas o guia: instalar/configurar um servidor elegível; identificar os arquivos cobertos; distinguir bloqueio de integridade de parecer da IA; manter uma mudança rejeitada bloqueada; liberar uma mudança benigna com decisão local; recuperar uma configuração interrompida. Registrar toda ajuda adicional. O ensaio com os próprios autores é formativo e tem viés; não apresentá-lo como estudo representativo de usuários.

### Critério de conclusão para a MOSTRATEC

O trabalho estará pronto quando a versão testada estiver identificada, a matriz efetivamente executada tiver resultados rastreáveis, a dupla conseguir reproduzir um caso íntegro e um bloqueio com revisão, as afirmações do relatório corresponderem às evidências e os materiais exigidos estiverem conferidos. Falhas registradas podem ser resultados científicos; uma barreira de segurança que falha precisa ser corrigida ou explicitamente excluída das garantias demonstradas.

## 8. Como apresentar a contribuição

Organizar a explicação em cinco partes: (1) uma ferramenta aprovada pode mudar; (2) investigação sobre uso da IA para avaliar essas diferenças; (3) Sentry detecta mudança e organiza revisão antes do uso; (4) testes em aplicativos reais e servidores diferentes; (5) limites e proposta de integração no host.

Mostrar um caso benigno é importante: se só houver alterações perigosas, “bloquear tudo que mudou” pode parecer resolver o problema inteiro. O benefício da análise semântica aparece ao ajudar o usuário a diferenciar a atualização legítima da mudança arriscada, enquanto a autorização permanece independente.

Usar uma tabela de resultados da investigação e outra da validação prática. Fazer os experimentos nos aplicativos antes da feira e guardar vídeo e logs. A apresentação no estande deve funcionar offline: vídeo previamente gravado, diferenças, parecer e evidências armazenadas localmente, além de uma demonstração local do bloqueio se aplicável. Identificar gravações como gravações; não representar resposta pronta como análise ao vivo. A restrição oficial de internet está descrita abaixo.

### Requisitos oficiais consultados em 29/09/2026

As fontes abaixo são do site da MOSTRATEC-LIBERATO. As orientações são para Ensino Médio; não aplicar dispensa de relatório da MOSTRATEC Júnior ao projeto.

| Item | O que preparar ou esclarecer | Fonte |
|---|---|---|
| Avaliação | Relatório, resumo, estande/banner, caderno de campo e apresentação oral | [Regulamento 2026, item 8.1](https://mostratec.liberato.com.br/wp-content/uploads/2026/09/REGULAMENTO_Mostratec_2026-v.2.pdf) |
| Relatório | Texto em português, espanhol ou inglês; A4, Arial/Times 12, preto, espaçamento 1,5 e páginas numeradas; cópia impressa encadernada no estande | [Relatório da pesquisa](https://mostratec.liberato.com.br/relatorio-da-pesquisa/) |
| Conteúdo do relatório | Introdução com problema/objetivos, referencial, método, resultados/discussão, conclusão e referências, além dos elementos pré-textuais indicados | [Estrutura oficial](https://mostratec.liberato.com.br/relatorio-da-pesquisa/) |
| Resumo | Parágrafo único de 250–500 palavras com objetivo, procedimentos, resultados e conclusão; versão final redigida pelos autores | [Resumo](https://mostratec.liberato.com.br/resumo/) |
| Diário | Disponível no estande; manter registros reais de observações, referências e decisões. Este arquivo inicia o registro desta etapa, não substitui retroativamente o histórico anterior | [Caderno de campo](https://mostratec.liberato.com.br/caderno-de-campo/) e [Exposição](https://mostratec.liberato.com.br/regras-de-exposicao/) |
| Banner e equipamento | Respeitar dimensões do estande; não há modelo único de banner; levar computador próprio e dar crédito às imagens | [Exposição](https://mostratec.liberato.com.br/regras-de-exposicao/) |
| Internet no estande | A página de exposição lista conexões de e-mail/internet entre os itens proibidos. Planejar offline; eventual exceção precisa ser esclarecida com a organização | [Exposição, itens proibidos, alínea k](https://mostratec.liberato.com.br/regras-de-exposicao/) |

**Prazo externo, sem impor agenda interna:** o regulamento atualizado em 04/09 informa envio do relatório em PDF até **12/10/2026, às 18h59 de Brasília**, com ID do projeto, para `relatorio.mostratec@liberato.com.br`. Conferir inscrição: para feiras afiliadas realizadas de 01/08 a 28/09, consta 30/09 como limite. A data da FEICIT e a situação da inscrição não foram verificadas. Fonte: [regulamento 2026, seção 6](https://mostratec.liberato.com.br/wp-content/uploads/2026/09/REGULAMENTO_Mostratec_2026-v.2.pdf). O planejamento não executa inscrições nem envia mensagens.

Não presumir que avançar da FEICIT para MOSTRATEC no mesmo ano obriga a chamar o projeto de “Fase II”. Conferir o enquadramento formal de continuidade com o orientador conforme as regras da edição.

### Uso de IA na pesquisa e no desenvolvimento

O regulamento, item 3.2.2(e), exige autoria dos estudantes e prevê penalização para projetos criados por IA. O trecho consultado não define precisamente a fronteira do uso assistido. Portanto, **não afirmar que qualquer uso de IA é proibido, nem que o uso intensivo proposto já está autorizado**. A dupla deve esclarecer com orientador/organização o uso em código, análise e redação e registrar a orientação. Fonte: [regulamento 2026](https://mostratec.liberato.com.br/wp-content/uploads/2026/09/REGULAMENTO_Mostratec_2026-v.2.pdf).

Como procedimento de transparência, registrar a ferramenta/modelo usado, a tarefa solicitada, a contribuição recebida e a revisão humana. A dupla define perguntas, método e gabaritos, confere resultados e fontes, entende as alterações aceitas e redige a versão final autoral. Esta recomendação não equivale a uma autorização da organização.

Separar **IA como objeto do experimento** (o modelo revisando diferenças) de **IA como assistente dos pesquisadores** (apoio no código ou na escrita). Usar conversa/contexto separado para a avaliação experimental, sem revelar gabaritos ou instruções de montagem do caso. Cada pesquisador pode conduzir sua frente com assistência, mas toda entrega tem um responsável humano; outra IA revisar uma saída não substitui a verificação da dupla.

## 9. Instruções para pesquisadores e IAs que continuarem o trabalho

1. Ler este arquivo e as últimas entradas do diário antes de agir. Conferir o estado atual do Git e a versão efetivamente instalada.
2. Escolher um ID do backlog, registrar responsável e marcar `em andamento`. Não iniciar uma reescrita ampla a partir deste plano.
3. Distinguir observação, hipótese, decisão e resultado. Não converter recomendação em fato nem teste automatizado em validação de aplicativo.
4. Preservar dados da pesquisa e tentativas experimentais. Guardar mudanças de protocolo com data e motivo; não ajustar o método silenciosamente após ver resultados.
5. Ao modificar código, testar o comportamento afetado no pacote correto. Em particular, testar que recomendação `allow` não equivale a autorização, que nova mudança invalida a revisão e que execução usa os arquivos verificados.
6. Não executar aprovações locais em nome do pesquisador durante a coleta como se fossem intervenção humana. Ações humanas são realizadas e registradas pelo operador.
7. Atualizar backlog, diário e links de evidência ao terminar. Se bloqueado, registrar qual informação falta e qual trabalho independente ainda pode seguir.

### Modelo de entrada do diário

```text
Data e horário:
Autor(es) / IA utilizada e papel:
ID do backlog e objetivo da sessão:
Versão/commit e ambiente:
O que foi feito:
Evidências (caminhos e IDs das execuções):
Resultado observado (incluindo erros e tentativas):
Interpretação e limites:
Decisões tomadas e justificativa:
Pendências / impedimentos:
Próxima ação e responsável:
Tempo dedicado:
```

### 29/09/2026 — análise inicial e planejamento

- **Autor:** IA assistente, a pedido dos pesquisadores; análise de código/documentação e elaboração deste plano.
- **Base:** commit `5c24cf3`, pacote `cliente/` 0.5.4. Nenhuma alteração funcional do Sentry realizada nesta sessão.
- **Observações:** encontrados setup e diagnóstico assistidos, revisão separada de autorização, duas árvores divergentes do pacote e uma demonstração anterior explicitamente limitada a cliente JSON-RPC controlado.
- **Verificação:** suíte `testes_cliente`: 30 testes, 29 aprovados, 1 ignorado por privilégio de symlink; nenhuma falha. Isso não valida aplicativos reais.
- **Proposta registrada:** usar o gateway como prova de conceito de controle potencialmente nativo do host; priorizar dois servidores e, se disponíveis, dois aplicativos em protocolo pequeno.
- **Informações solicitadas:** data/horas e papéis; clientes/sistemas/servidores/orçamento; relatório completo, exigências da feira e trabalho fora desta cópia.
- **Próxima ação registrada inicialmente:** obter definições da dupla e iniciar M02/M03 em paralelo. As respostas e a revisão subsequente estão na entrada abaixo.
- **Tempo dedicado:** não aferido.

### 29/09/2026 — atualização após respostas da dupla

- **Informações recebidas:** trabalhar sem datas/horas impostas; papéis intercambiáveis e uso frequente de IA; Codex e Claude no Windows; prioridade inicial Codex; Claude Pro, GPT Plus e créditos OpenRouter disponíveis; abertura para selecionar novo servidor; nenhum trabalho fora desta pasta.
- **Decisões do plano:** substituir calendário por dependências; núcleo de 12 execuções protegidas no Codex e 2 controles diretos; Claude opcional; Time MCP como candidato independente com prova obrigatória da origem do código na cópia verificada.
- **Consulta oficial:** regulamento 2026 atualizado em 04/09 e páginas de relatório, resumo, caderno e exposição. Incluídos requisitos, prazo externo de relatório, restrição de internet e pendência sobre uso assistido de IA.
- **Resultado:** versão 1.1 do plano; nenhuma dessas decisões representa experimento já executado. Fonte de cada requisito vinculada na seção 8.
- **Próxima ação:** M02 e M03 em paralelo, preparação de S2 em M05 e esclarecimentos de M01 conduzidos pelos pesquisadores.

## 10. Definições confirmadas e pendências reais

Não é necessário responder novamente sobre horas ou calendário. As pendências abaixo podem ser resolvidas durante o desenvolvimento e não impedem começar a organização técnica.

| Informação | Estado | Por que afeta o plano |
|---|---|---|
| Ritmo de desenvolvimento e divisão nominal | Dupla define conforme necessidade; A/B intercambiáveis | Sem calendário imposto |
| Clientes e sistema | Codex e Claude no Windows; versões/modelos ainda a registrar | Codex primeiro; Claude opcional |
| Servidor independente | Dupla aberta à seleção; Time recomendado, compatibilidade pendente | Verificar antes de fechar coleta |
| Recursos de IA | Claude Pro, GPT Plus e créditos OpenRouter confirmados pelos autores | Não exigir nova compra nem API para o núcleo |
| Trabalho externo à pasta | Autores confirmaram que não existe | Não esperar materiais externos; consolidar relatório a partir das fontes presentes |
| Documento de limitações citado e fundamentação completa | Referência quebrada encontrada; documento não localizado | Reconstruir documentação com fontes/dados verificáveis; marcar o que não puder ser recuperado |
| Regras da feira | Consultadas e resumidas na seção 8 | Conferir atualizações antes da entrega |
| Uso assistido de IA | Necessário esclarecer alcance da regra oficial | Pesquisadores consultam orientador/organização e registram resposta |
| Inscrição e eventual continuidade formal | Não verificados | Conferir no portal/orientador; classificação não substitui documentação |
| Equipamento e autorização para eventual internet | Não confirmados | Preparar apresentação offline desde o início |

Quando houver respostas, registrar a data, atualizar as decisões afetadas e preservar no diário a mudança de escopo. Não preencher lacunas com resultados presumidos.
