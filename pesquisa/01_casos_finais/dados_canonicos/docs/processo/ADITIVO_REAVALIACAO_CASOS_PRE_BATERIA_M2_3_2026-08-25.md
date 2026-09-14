# Aditivo de reavaliação dos casos pré-bateria — M2.3

**Data da decisão:** 2026-08-25
**Estado:** escopo autorizado; candidata, revisão humana e verificação
independente pendentes
**Natureza:** mudança crítica, prospectiva e aditiva
**Base:** `1d4a60fe1e2093525e582b572a8a8c71a0ee01d0`

## 1. Motivo e decisão do pesquisador

Na revisão anterior às baterias finais, o pesquisador constatou que:

1. os 24 casos não `S0` do braço MCPTox não possuíam uma versão da mesma
   ferramenta anterior à alteração; a montagem vigente representava
   `ferramenta ausente -> ferramenta adicionada` e, portanto, não sustentava
   uma avaliação de mudança após aprovação;
2. quatro casos N-INT precisavam de correção ou substituição:
   `M23-NINT-B1-05`, `M23-NINT-B1-06`, `M23-NINT-P1-02` e
   `M23-NINT-P1-05`;
3. oito casos Connor precisavam ser substituídos:
   `M23-CN-002`, `M23-CN-005`, `M23-CN-010`, `M23-CN-012`,
   `M23-CN-026`, `M23-CN-028`, `M23-CN-029` e `M23-CN-030`;
4. os oito substitutos Connor deveriam ser casos materialmente diferentes,
   e não renomeações ou cópias estruturais dos casos retirados.

O pesquisador autorizou prospectivamente:

- reconstruir os 24 casos MCPTox não `S0` com predecessores sintéticos da
  mesma ferramenta, explicitamente rotulados;
- manter invariantes os seis casos MCPTox `S0`;
- manter `CN-007/CN-025` como o único par representativo do mecanismo Connor
  anterior e substituir somente os oito slots listados;
- substituir os quatro casos N-INT listados por estados aprovados funcionais e
  deltas avaliáveis.

## 2. Regra de preservação

O congelamento `baterias_finais/m2_3_congelamento_casos_v1/` e o pacote
`baterias_finais/m2_3_execucao_v2/` são registros históricos e não podem ser
alterados retroativamente. Esta decisão cria uma candidata aditiva em
`testes_cenarios/m2_3_campanha_v1/reavaliacao_pre_bateria_v1/`.

A candidata não substitui o congelamento vigente até que sejam satisfeitos:

1. revisão humana dos casos novos;
2. verificação independente dos arquivos e do diff reais;
3. OK explícito do pesquisador para o fechamento científico;
4. criação posterior de novo congelamento e novo pacote executável, sob portão
   próprio.

### Exceção operacional para handoff entre máquinas

Depois da materialização e da autorrevisão, o pesquisador determinou em
2026-08-25 que a candidata e o prompt único de verificação/continuidade fossem
commitados e enviados a `origin/main` **antes** da verificação independente,
para permitir o handoff à outra máquina no dia seguinte. Essa decisão altera
somente a ordem de transporte e preservação provisória desta unidade.

O commit/push antecipado:

- não constitui verificação independente;
- não aprova, congela ou promove a candidata;
- não abre preflight, modelo, API, Ollama, benchmark ou bateria;
- não dispensa o parecer de outro agente sobre os arquivos e o diff reais;
- não dispensa o OK explícito do pesquisador após o parecer para qualquer
  continuidade científica.

Se a verificação devolver a unidade para correção, as correções serão aditivas
em novo commit. Se aprovar, a continuidade começará somente depois do OK humano
pós-parecer previsto no prompt de handoff.

Nenhuma bateria, preflight, modelo, API, Ollama, rede ou snippet transportado
está autorizada por este aditivo.

## 3. Contrato MCPTox

Para cada um dos 24 casos MCPTox não `S0`:

- o objeto da ferramenta atual deve ser preservado literalmente da vista C1
  já ancorada no congelamento v1;
- o predecessor aprovado deve ter o mesmo nome da ferramenta atual;
- o predecessor deve ser benigno, funcional como descrição de interface e
  construído pelo projeto;
- a transição deve ser declarada como uma modificação de uma ferramenta
  persistente (`added=0`, `modified=1`, `removed=0`);
- a origem sintética deve permanecer visível no caso, no manifesto e no
  relatório.

Os predecessores não foram fornecidos pelo MCPTox nem observados
historicamente. A alegação permitida é somente: **aprovação prévia simulada e
controlada da mesma ferramenta**. É proibido afirmar que o MCPTox documentou
uma história real de rug pull da mesma ferramenta.

Os seis slots `S0` devem conservar os mesmos identificadores, caminhos e hashes
do congelamento v1.

## 4. Contrato N-INT

Os quatro substitutos devem manter slot, classe e ground truth do desenho, mas
receber novos identificadores e estados próprios:

| slot | mecanismo candidato | requisito |
| --- | --- | --- |
| `M23-NINT-B1-05` | resumo de campos após redação segura | o estado aprovado redige valores de verdade; o delta não revela segredos |
| `M23-NINT-B1-06` | endurecimento de parsing de URL HTTPS | o estado aprovado já aplica allowlist funcional; não há acesso de rede |
| `M23-NINT-P1-02` | seleção de escopo pelo chamador | o delta transfere indiretamente controle antes reservado à política |
| `M23-NINT-P1-05` | troca de operador no teto de retenção | o delta remove o limite sem depender de evento artificial de aprovação |

Os snippets são artefatos inertes para inspeção; não devem ser executados nesta
unidade.

## 5. Contrato Connor

`CN-007/CN-025` permanece sem alteração como o único exemplar do mecanismo
anterior. Os oito slots substitutos formam quatro pares `P1/B1`, com âncoras
Connor `P18` distintas e mecanismos encadeados materialmente diferentes:

| par de slots | âncora | mecanismo P1 |
| --- | --- | --- |
| `CN-002/CN-026` | `PE-P18` | rota alternativa não aprovada incorporada entre preparação e decisão |
| `CN-005/CN-029` | `SB-P18` | capacidade pendente contada como capacidade saudável |
| `CN-010/CN-028` | `RS-P18` | prefixo de canal controlado pelo chamador aceito como compatibilidade |
| `CN-012/CN-030` | `ST-P18` | anotações mescladas depois do filtro de campos públicos |

Cada par deve ter código aprovado, código atual, diff e identificador de
mecanismo próprios. Os quatro códigos perigosos e os quatro controles devem ser
estruturalmente distintos entre si. Nenhum substituto pode reutilizar o padrão
de guarda inalcançável retirado dos oito casos anteriores.

As reconstruções permanecem seguras e inertes: trabalham somente sobre
registros sintéticos em memória, não incorporam sinks operacionais das PoCs e
não executam o conteúdo-fonte Connor.

## 6. Critérios de aceitação da candidata

- composição 90 = 30 casos por braço e 6 casos por classe em cada braço;
- 36 casos novos (4 N-INT, 8 Connor, 24 MCPTox) e 54 carregados;
- 150 superfícies aplicáveis no total, preservando o desenho C1/C2/D;
- quatro mecanismos Connor novos e distintos, com quatro controles distintos;
- 24 objetos atuais MCPTox literalmente iguais aos objetos atuais ancorados;
- seis `S0` MCPTox invariantes;
- todos os hashes, referências, baselines determinísticos e pacotes cegos
  consistentes;
- todos os portões de congelamento e execução fechados;
- zero chamadas a modelo e zero chamadas de rede.

## 7. Arquivos autorizados nesta unidade

- esta autoridade aditiva;
- o gerador e os validadores em
  `tools/m2_3_reavaliacao_casos_v1/`;
- a árvore candidata
  `testes_cenarios/m2_3_campanha_v1/reavaliacao_pre_bateria_v1/`.

Não estão autorizadas nesta unidade alterações nos congelamentos, resultados,
gabaritos, matrizes, políticas ou prompts experimentais já existentes.
