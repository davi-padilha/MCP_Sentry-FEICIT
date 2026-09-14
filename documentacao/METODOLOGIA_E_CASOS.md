# Metodologia e casos

A pesquisa mede como diferentes camadas respondem a mudanças em ferramentas
MCP previamente aprovadas.

| Condição | Informação usada |
| --- | --- |
| A | nenhuma proteção |
| B | comparação determinística por hash |
| C1 | descrição e metadados |
| C2 | código observável |
| D | descrição, metadados e código em conjunto |

A bateria final contém 90 casos:

- 30 casos internos N-INT, usados na comparação pareada C1/C2/D;
- 30 casos MCPTox, voltados à análise textual C1;
- 30 casos Connor, voltados à análise de código C2.

Os braços MCPTox e Connor medem superfícies diferentes e não devem ser
comparados entre si para declarar superioridade de C1 ou C2.

Os casos estão em `../pesquisa/01_casos_finais/`. Comece pelo índice CSV; os
JSONs preservam os conteúdos completos e as entradas entregues aos modelos.
