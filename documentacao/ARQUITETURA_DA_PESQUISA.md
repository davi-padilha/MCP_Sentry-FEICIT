# Arquitetura do projeto

O MCP Sentry e dividido em componentes pequenos para manter o experimento
controlado e facil de auditar.

## Componentes

### Agente

Pasta: `agente/`

Responsavel por representar o agente que recebe uma tarefa do usuario e decide
qual ferramenta MCP chamar.

Estado atual: reservado para a evolucao do agente experimental.

### Servidores simulados

Pasta: `servidores_simulados/`

Contem ferramentas locais que simulam servidores MCP. O primeiro baseline
implementa leitura segura de arquivos `.txt` dentro de uma pasta controlada.

Essas ferramentas nao devem fazer chamadas reais perigosas, modificar o sistema
operacional ou acessar arquivos fora do ambiente controlado.

### MCP Guard

Pasta: `mcp_sentry/`

Camada intermediaria que deve interceptar chamadas entre agente e ferramentas.
E aqui que entram as condições B, C1, C2 e D.

Estado atual: a camada já possui implementações reais: `hash_guard.py` para a
Condição B, `hybrid_guard.py` para a Condição D v1 histórica (`hash + C2`) e
`ast_extractor.py` como suporte à Condição C2. A Condição D prospectiva da M2.3
(`descrição/metadados + código`) ainda precisa ser adaptada no runner futuro;
ela não deve ser confundida com `hybrid_guard.py` nem altera esse módulo
retroativamente.

No estagio atual do projeto, essa camada e experimental: compara cenarios,
gera evidencias, executa baterias e mede acertos, falsos positivos, falsos
negativos, falhas e latencia.

Em um estagio futuro, o MCP Guard poderia evoluir para um proxy/gateway MCP.
Nesse modelo, o agente nao falaria diretamente com o servidor MCP real. O fluxo
seria:

```text
Agente
  -> MCP Guard / MCP Sentry
    -> Servidor MCP real
```

O Guard manteria um registro de versoes aprovadas e verificaria, antes da
execucao, se a ferramenta atual ainda corresponde ao contrato aprovado. Essa
arquitetura operacional e trabalho futuro, nao entrega atual.

### Testes e cenarios

Pasta: `testes_cenarios/`

Deve guardar datasets padronizados com mudancas benignas e maliciosas. Cada
cenario precisa ter gabarito claro.

### Benchmarks

Pasta: `benchmarks/`

Guarda experimentos quantitativos. O benchmark Ollama mede modelos locais como
classificadores semânticos para C1, C2 e D.

### Logs e resultados

Pasta: `logs_resultados/`

Guarda CSVs, evidencias, diario de processo e notas metodologicas. Esta pasta
serve como trilha de auditoria do projeto.

## Mapa de módulos e condições

| Módulo ou diretório | Papel experimental |
| --- | --- |
| `servidores_simulados/tools.py` | Condição A |
| `mcp_sentry/hash_guard.py` | Condição B |
| `benchmarks/ollama/` | Condição C1 |
| `mcp_sentry/ast_extractor.py` + `benchmarks/c2_codigo_observavel/` | Condição C2 |
| `mcp_sentry/hybrid_guard.py` | Condição D v1 histórica (`hash + C2`) |
| runner futuro da M2.3 | Condição D prospectiva (descrição/metadados + código) |
| `servidores_mcp/` | Demonstração de MCP real, fora do desenho experimental A–D |

## Fluxo conceitual

```text
Usuario
  -> Agente
    -> MCP Guard opcional
      -> Ferramenta simulada
        -> Resultado
          -> Log experimental
```

Na Condicao A, o MCP Guard e pulado.

Nas Condicoes B, C e D, o MCP Guard decide permitir ou bloquear antes da
execucao da ferramenta.

## Modos de uso previstos

O projeto deve distinguir tres modos de uso:

```text
1. Script experimental
   Usado agora para baterias controladas e comparacao das condicoes A-D.

2. Scanner de instalacao ou atualizacao
   Possivel evolucao para verificar servidores MCP, pacotes ou imagens Docker
   quando forem instalados ou atualizados.

3. Proxy/gateway MCP
   Possivel etapa final, em que o agente chama o MCP Guard e o Guard encaminha
   ou bloqueia a chamada ao servidor real.
```

O modo proxy/gateway e o mais forte operacionalmente, mas tambem o mais caro em
complexidade: exige repasse de mensagens MCP, banco de aprovacoes, tratamento
de erros, suporte a servidores reais e politicas claras de reprovacao ou
reaprovacao.

## Estrategia contra latencia

Uma chamada LLM em toda invocacao de ferramenta nao e o desenho desejavel para
uso real. A arquitetura futura deve priorizar camadas baratas:

```text
1. hash e versao iguais -> permitir rapidamente;
2. metadados ou permissoes mudaram -> exigir analise;
3. codigo observavel mudou -> extrair evidencias AST;
4. regra deterministica clara -> bloquear ou permitir sem LLM;
5. caso ambiguo -> chamar LLM classificador;
6. decisao aprovada -> cachear para chamadas futuras.
```

Assim, o LLM fica reservado para diferencas que realmente exigem classificacao
semantica. Isso preserva a ideia da Condicao C/D sem transformar a latencia do
modelo em custo obrigatorio de toda chamada.
