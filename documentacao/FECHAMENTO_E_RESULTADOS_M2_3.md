# Fechamento quantitativo das campanhas M2.3

**Data:** 2026-09-12
**Classe:** crítica
**Estado desta unidade:** revisada independentemente como `APTO`, com P0=0,
P1=0 e P2=0; commit/push autorizado pelo pesquisador

## 1. Escopo do fechamento

Este documento propõe encerrar a execução, preservação e análise quantitativa
das campanhas M2.3 já realizadas. Ele não reabre bateria, não produz resultado
novo, não altera evidência existente e não autoriza modelo, API, rede ou gasto.

O fechamento é quantitativo e delimitado. A codificação humana qualitativa E02
permanece uma decisão separada, e a comunicação científica continua na Fase
10.10.

## 2. Marcos publicados

| Objeto | Raiz principal | Commit publicado |
| --- | --- | --- |
| Evidência primária da campanha original | `logs_resultados/evidencias/m2_3_campaign_20260907_01/` | `81c16b5043aea62f69fb503c80223fa766dd23f4` |
| Autorização portátil da campanha original | `logs_resultados/evidencias/m2_3_campaign_20260907_01_autorizacao_portatil/` | `fdfbf6473bf3b779f841b9b32984d4e22b097863` |
| Análise final da campanha original | `baterias_finais/m2_3_analise_v3/` | `df11752b8626e688011edfe6bad7abd5f12775a1` |
| Evidência primária da extensão multimodelo | `logs_resultados/evidencias/m2_3_extension_campaign_20260911_221516/` | `faa343e0f9fea85ddcd9889a1817e99987cf0a4c` |
| Análise descritiva da extensão | `baterias_finais/m2_3_extensao_multimodelo_analise_v1_candidate/` | `bf4b52acb0ce5843e5f22624cac4bccc9e1af48f` |
| Quatro planilhas derivadas para leitura humana | `baterias_finais/m2_3_planilhas_resultados_v1_candidate/` | `007343c1917af9f23110680d21178b1e7f96ee50` |

Os seis commits integram `origin/main`. No início desta unidade,
`HEAD=origin/main=007343c1917af9f23110680d21178b1e7f96ee50` e a árvore estava limpa.

## 3. Universos encerrados

### Campanha original

- 1.500 unidades primárias;
- 750 pares R1/R2;
- 1.514 intenções e checkpoints;
- 1.527 tentativas, incluindo 13 retries de transporte recuperáveis;
- 14 diagnósticos R3;
- custo externo registrado de US$ 0,175854933.

### Extensão multimodelo

- 900 unidades primárias e 450 pares R1/R2;
- 877 respostas primárias semanticamente válidas e 23 falhas terminais;
- 905 tentativas;
- 5 diagnósticos R3;
- custo observado de US$ 5,14043240 e contabilizado de US$ 5,80164740.

As duas coortes não são somadas como uma única amostra e não sustentam uma
comparação histórica causal.

## 4. Limites de interpretação

1. A comparação C1/C2/D pertence ao núcleo N-INT, onde as leituras observam os
   mesmos casos pareados.
2. MCPTox/C1 e Connor/C2 permanecem braços externos estratificados; diferenças
   entre eles não demonstram superioridade de C1 ou C2.
3. A extensão estima sensibilidade de configuração dentro de uma nova coorte
   temporal. Não demonstra superioridade causal de modelo ou provedor.
4. R3 é diagnóstico e não substitui R1/R2.
5. Falhas terminais permanecem nos denominadores definidos pelos contratos.
6. Nenhum resultado autoriza alegação de ranking ou eficácia universal.

## 5. Pendência qualitativa preservada

`baterias_finais/m2_3_analise_v3/codificacao_justificativas_e02.csv` contém 744
linhas de dados marcadas `pendente_codificacao_humana`. Este fechamento não as
codifica, não as descarta e não as apresenta como concluídas.

A codificação E02 só deve ser aberta por decisão humana específica caso seja
necessária para a narrativa final. Ela não bloqueia o encerramento quantitativo
dos resultados já calculados e preservados.

## 6. Próxima rota

Após a preservação desta unidade, a frente recomendada é a Fase 10.10:
incorporar resultados e limites ao relatório, resumo, apresentação e caderno de
campo. A Fase 11 de reprodutibilidade e entrega vem depois do fechamento da
comunicação científica.

Não existe fundamento técnico registrado para reexecutar as campanhas já
encerradas.
