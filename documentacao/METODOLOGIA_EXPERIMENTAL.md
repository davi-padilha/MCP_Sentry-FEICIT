# Metodologia experimental

## Pergunta de pesquisa

Quais estrategias sao mais eficazes para detectar mudancas perigosas em
ferramentas MCP previamente aprovadas, considerando falsos negativos, falsos
positivos, falhas de execucao e latencia?

## Hipotese

A analise combinada pode apresentar o melhor equilibrio entre seguranca e
utilidade quando descricao/metadados e codigo contiverem sinais
complementares, mas pode apenas aumentar custo e latencia quando uma unica
superficie ja for suficiente. B deve detectar mudancas com baixo custo, sem
classificar se sao benignas ou perigosas. C1 pode aceitar perigo quando a
descricao permanece enganosa. C2 deve ajudar principalmente quando a
capacidade perigosa aparece no codigo e nao nos metadados.

Essa hipotese vale apenas para ferramentas simuladas locais e com codigo
Python observavel; os modelos classificadores podem ser locais ou em nuvem.

## Condicoes experimentais

### Condicao A: baseline sem protecao

O fluxo aceita a ferramenta simulada sem verificacao. Esta condicao mede a
referencia sem defesa do MCP Sentry.

### Condicao B: verificacao por hash

O MCP Sentry calcula hashes SHA-256 do conteudo aprovado e atual e informa se
houve mudanca. Para a comparacao experimental, hash diferente corresponde a
mudanca detectada e nao constitui, por si so, classificacao de risco.

Quando for necessario mapear B para `permitir/bloquear`, a politica conservadora
usa `hash igual -> permitir` e `hash diferente -> bloquear`. O bloqueio apenas
encaminha a mudanca para revisao; nao afirma que ela e maliciosa.

Forca: simples e reproduzivel.

Limite: pode bloquear mudancas benignas.

### Condicao C1: descricao e metadados

Um LLM classificador compara a descricao original e a descricao atualizada para
decidir se a intencao mudou de forma perigosa.

Forca: distingue mudancas benignas de maliciosas.

Limite: pode errar, variar ou falhar no formato de resposta.

### Condicao C2: codigo observavel

Um LLM classificador recebe o codigo ou uma representacao observavel extraida
dele, sem receber a descricao usada por C1.

Forca: pode observar capacidades que os metadados nao declaram.

Limite: depende de codigo observavel ou inspecionavel e pode ter maior custo de
latencia.

### Condicao D: analise combinada

Um LLM classificador recebe, para a mesma mudanca, tanto a descricao/metadados
quanto o codigo ou sua representacao observavel. Modelo, politica e parametros
devem permanecer iguais aos de C1 e C2 dentro da comparacao controlada.

Forca: pode reunir sinais complementares presentes em superficies diferentes.

Limite: depende das duas vistas e pode aumentar custo, latencia e volume de
contexto sem melhorar a decisao.

Esta definicao e prospectiva para a campanha M2.3. Fases historicas em que D
significava `hash + C2` permanecem validas sob o contrato usado na epoca. Um
possivel gatilho de hash para evitar inferencias quando nada mudou e objeto de
otimizacao futura, separado da Condicao D atual.

## Estrutura da campanha M2.3

- `N-INT`: 30 casos internos controlados, seis por classe, principal contraste
  pareado entre C1, C2 e D;
- `E-C1-MT`: ate 30 casos ancorados no MCPTox, validacao externa especifica de
  C1;
- `E-C2-CN`: ate 30 casos ancorados no Connor, validacao externa especifica de
  C2.

Os bracos externos nao sao comparados entre si para declarar superioridade de
C1 ou C2. D so se aplica quando o mesmo caso possui descricao/metadados e
codigo suficientes. A e B so se aplicam quando existem estados aprovado e
atual comparaveis. Os bracos externos tem teto de 30; a ausencia de casos
elegiveis deve reduzir apenas o denominador externo e ser declarada como
limitacao, nunca ser compensada com preenchimento artificial. Se o nucleo nao
sustentar seus 30 casos, a campanha volta aos pesquisadores antes do
congelamento.

## Metricas

- Acuracia geral.
- Verdadeiro positivo, verdadeiro negativo, falso positivo e falso negativo.
- Precisao, recall e F1-score.
- Taxa de falso positivo.
- Taxa de falso negativo.
- Falha de formato JSON.
- Falha de sistema.
- Casos sem decisao valida ou enviados para revisao humana.
- Latencias media e mediana.
- Resposta bruta para auditoria.

## Prioridade de interpretacao

1. Menor falso negativo.
2. Menor falha de formato JSON.
3. Maior acuracia geral.
4. Menor latencia.

Falso negativo e o erro mais grave: significa que uma mudanca maliciosa passou
sem bloqueio.

## Cuidados metodologicos

- Nao alterar cenarios no meio de uma rodada.
- Nao alterar parametros no meio de uma rodada.
- Registrar versoes de modelos e dependencias.
- Preservar cada CSV oficial com nome datado.
- Separar resultados de teste exploratorio e rodada oficial.
- Nao misturar datasets diferentes na mesma comparacao.
- Definir a aplicabilidade de cada condicao antes de executar os modelos.
- Tratar `S0` como controle de estabilidade e apresentar seus resultados
  separadamente das metricas principais de mudanca.
- Tratar metricas por classe com poucos casos como descritivas e
  exploratorias.
