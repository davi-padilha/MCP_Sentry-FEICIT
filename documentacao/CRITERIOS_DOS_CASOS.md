# Criterios para cenarios de teste

Cada cenario deve ser claro o suficiente para que o gabarito seja defensavel.

## Campos recomendados

- `id`: identificador unico.
- `nome_ferramenta`: ferramenta avaliada.
- `descricao_original`: descricao aprovada.
- `descricao_atualizada`: descricao apos mudanca.
- `gabarito_bloquear`: `true` para mudanca perigosa, `false` para benigna.
- `justificativa_gabarito`: explicacao curta.
- `categoria`: tipo de mudanca.

## Categorias uteis

- Exfiltracao de dados.
- Telemetria remota sem necessidade clara.
- Acesso ampliado.
- Alteracao destrutiva.
- Mudanca benigna de filtro, ordenacao ou validacao.
- Mudanca ambigua para revisao.

## Regra para bateria oficial

Cenarios ambiguos nao devem entrar na primeira bateria oficial. Eles podem ser
guardados como conjunto exploratorio separado.
