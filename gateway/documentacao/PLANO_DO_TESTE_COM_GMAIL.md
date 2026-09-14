# Plano — ensaio pareado Gmail/Sentry para a FEICIT

**Data:** 2026-09-12  
**Estado:** rascunho local para revisão independente; não autoriza OAuth,
Google, rede, Donna real, envio de e-mail ou alteração persistente de
configuração.  
**Escopo:** gateway operacional em `aplicacoes/mcp_sentry/` e cópias
temporárias da Donna em `aplicacoes/donna_mcp/`. Não altera nem produz
evidência para A/B/C1/C2/D, M2.3 ou suas baterias.

## 1. Objetivo e alegação limitada

Demonstrar, em contas Google exclusivamente controladas pelo projeto, a
diferença entre usar uma Donna aprovada e uma versão alterada após aprovação.
O ensaio verifica que o Sentry detecta a alteração antes de iniciar o backend
e, diante de `block`, impede o envio oculto de uma mensagem sintética.

A alegação permitida é:

> Para uma Donna local previamente aprovada e inteiramente coberta pelo
> manifesto, o Sentry detecta uma alteração posterior e pode impedir que ela
> seja iniciada antes do envio de e-mail.

O ensaio não demonstra proteção para MCPs arbitrários, dependências fora das
raízes aprovadas, bypass por entrada direta, isolamento do host, segurança de
produção ou classificação semântica automática perfeita.

## 2. Controle de risco

- Todas as contas remetente, destinatária principal e observadora pertencem ao
  projeto; nenhum endereço é registrado neste documento, no Git ou em saída
  pública.
- Todo assunto e corpo são sintéticos, sem anexos, dados pessoais ou conteúdo
  operacional.
- A variante alterada é reconstruída apenas em cópia temporária privada. Ela
  acrescenta uma cópia oculta exclusivamente para a caixa observadora do
  projeto; nenhum destinatário legado ou de terceiro pode ser reutilizado.
- Antes de D2 e S2, o preflight deve provar a origem da variante privada: o
  provider ativo deve ter o hash recém-gerado para a raiz da célula, e comando,
  imports e paths de runtime não podem referenciar nenhuma variante legada.
  O hash e a proveniência ficam somente na auditoria privada sanitizável.
- A configuração direta da Donna só é permitida nos dois controles diretos;
  durante as duas células Sentry, `Donna_via_Sentry` deve ser a única rota de
  backend.
- Credenciais, token, stores, auditorias, cópias e configuração do host ficam
  fora do repositório e são removidos ou revogados no fechamento.

## 3. Matriz do ensaio

| Célula | Versão | Rota | Resultado exigido |
| --- | --- | --- | --- |
| D1 | aprovada | Donna direta | uma mensagem sintética chega somente ao destinatário principal |
| D2 | alterada | Donna direta | a mensagem sintética chega ao principal e à caixa observadora controlada |
| S1 | aprovada | `Donna_via_Sentry` | prévia, confirmação humana e entrega somente ao principal |
| S2 | alterada após baseline | `Donna_via_Sentry` | `security_review_required`, decisão `block`, `spawn_attempts: 0` e nenhuma nova mensagem na caixa observadora |

Cada célula usa raiz, store e estado de confirmações próprios. D1, D2 e S1
exigem prévia e confirmação humana específica antes de cada envio. S2 não
pode obter prévia da Donna nem alcançar Google: o gateway deve bloquear antes
de iniciar o backend.

Cada célula recebe marcador sintético exclusivo, privado e não reutilizável no
assunto e no corpo. Imediatamente antes de S2, uma consulta sanitizada à caixa
observadora deve registrar que não existe mensagem com o marcador de S2. Após
o `block`, a mesma consulta deve continuar vazia; a comparação antes/depois,
mais `spawn_attempts: 0`, é a única evidência aceita para afirmar ausência de
entrega em S2. Mensagens de D2 nunca servem como linha de base de S2.

## 4. Preparação local autorizável

Depois de revisão independente favorável e primeiro OK humano específico para
preparação, executar somente:

1. confirmar branch limpa e fixar hashes de partida;
2. criar raízes temporárias literais fora do repositório, uma por célula;
3. reconstruir, em cópia privada, a variante aprovada e a variante alterada
   com destinatário observador controlado;
4. gerar manifesto privado para S1/S2 que cubra entrypoints, módulos da Donna,
   provedor Gmail ativo, configuração carregada em runtime e envelope de
   execução;
5. fazer preflight local sanitizado: integridade, proveniência e hash da
   variante privada, ausência de imports ou paths da variante legada,
   configuração efetiva, ausência de Donna direta nas células Sentry, escopos
   mínimos e ausência de segredo em artefatos preserváveis;
6. executar somente testes locais necessários de Donna e gateway, sem OAuth ou
   rede.

Qualquer módulo carregado em runtime fora do manifesto, valor secreto em
artefato preservável, rota direta paralela nas células Sentry, escopo adicional,
divergência de envelope ou origem não comprovada da variante privada produz
`NO_GO`.

## 5. Portões para o efeito externo

Somente após preflight verde e segundo OK humano explícito para a execução:

1. obter OAuth novo, exclusivamente nas raízes privadas, com o conjunto exato
já declarado pela Donna: Calendar Events, Gmail Compose e Gmail Readonly; não
ampliar escopos para limpeza automatizada;
2. executar D1 e D2 uma única vez cada, confirmando manualmente as prévias;
3. executar S1 uma única vez, pela entrada Sentry;
4. aplicar a variante alterada somente depois do baseline de S2, tentar
`enviar_email`, ler integralmente o dossiê e submeter `block` vinculado;
5. confirmar `spawn_attempts: 0` e, por consulta separada e sanitizada à caixa
   observadora, comparar o marcador exclusivo de S2 antes/depois e confirmar
   que S2 não produziu mensagem;
6. diante de resultado `unknown`, timeout, mensagem inesperada, falha de
limpeza, processo órfão ou dúvida sobre estado externo, parar em `NO_GO` sem
repetir seletivamente o efeito.

## 6. Limpeza e evidência

Depois da reconciliação de cada caixa de teste, os pesquisadores removem as
mensagens sintéticas pelas ferramentas normais da conta, sem ampliar o escopo
OAuth da Donna. Em seguida:

1. confirmar ausência das mensagens sintéticas nas caixas controladas;
2. encerrar processos e remover a configuração efêmera do host;
3. revogar o token OAuth e excluir token, credencial copiada, stores,
   auditorias, mutation stores e raízes temporárias literais;
4. preservar somente resumo sanitizado: hashes, decisão, contagens de entrega,
   `spawn_attempts`, estado de limpeza e limites da alegação.

Nenhum endereço, token, ID de mensagem, conteúdo de e-mail, caminho privado ou
saída OAuth pode entrar em Git, relatório público ou material de apresentação.

## 7. Critérios de aceite

O ensaio é aceito somente se D1, D2 e S1 confirmarem o comportamento esperado,
S2 permanecer bloqueada antes do backend e a caixa observadora não receber
mensagem de S2. A limpeza, revogação e remoção das raízes privadas devem ser
verificadas. Este resultado é uma demonstração aplicada separada de T7; não
reescreve nem amplia retrospectivamente suas evidências.

## 8. Fora de escopo

- executar a variante alterada ao vivo na feira;
- adicionar interface gráfica, descoberta automática de MCPs ou múltiplos
  backends;
- mudar código do gateway ou da Donna durante a preparação;
- usar contas, destinatários ou conteúdo fora do controle do projeto;
- alegar que o Sentry detecta toda alteração maliciosa.
