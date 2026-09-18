# Resultados visuais para a FEICIT

Use **`RESULTADOS_FEICIT_COMPLETOS_V4.pptx`** na apresentação. É a versão de 16 slides que apresenta o núcleo controlado e a ampliação multimodelo como evidências complementares da mesma bateria, com dois guias de leitura das métricas. As versões anteriores permanecem para comparação.

| Resultado que você procura | Slide |
| --- | ---: |
| Escopo integrado, casos e denominadores | 2 |
| O que significam VP, VN, FN e FP | 3 |
| FN, FP e ausência de classificação binária no N-INT | 4 |
| Transições pareadas de C1 para C2 | 5 |
| Diferenças entre classes de casos | 6 |
| Dois exemplos reais com gabarito e decisões | 7 |
| MCPTox por posição e repetição | 8 |
| Connor por posição e repetição | 9 |
| Como ler concordância, latência, falhas e custos | 10 |
| Latências de MCPTox e Connor | 11–12 |
| Repetição e custo no núcleo controlado | 13 |
| Decisões, falhas e repetição na ampliação multimodelo | 14 |
| Custos, falhas e tempos por posição na ampliação | 15 |
| Conclusões e limites | 16 |

**Sentido das métricas.** VP (ameaça bloqueada corretamente) e VN (benigno permitido corretamente): mais é melhor. FN (ameaça permitida por engano) e FP (benigno bloqueado por engano): menos é melhor. A taxa de FN divide FN pelo total de ameaças; a taxa de FP divide FP pelo total de benignos. Essas taxas também devem cair. Respostas sem classificação binária não deram uma decisão direta; menos facilita a operação, mas o bloqueio de segurança aplicado a elas aparece separado da classificação do modelo. O sentido de melhor/pior também aparece nos cabeçalhos e legendas de todos os gráficos e tabelas relevantes.

Concordância R1/R2 compara as duas execuções do mesmo caso: mais significa decisões mais consistentes, **não** necessariamente corretas. Mediana é o tempo do meio; p95 é o tempo sob o qual terminaram 95% das respostas. Menor latência, custo e número de falhas terminais são desejáveis sob os mesmos requisitos. Mais respostas válidas indica maior completude, sem assegurar acerto. R3 é uma repetição diagnóstica extra; seu número não tem sentido de melhor/pior sem analisar os gatilhos. A taxa de bloqueio mede a frequência da ação “bloquear”; por si só, nem mais nem menos indica qualidade.

As contagens da campanha principal vêm da **decisão operacional** dos casos aplicáveis em `../pesquisa/02_resultados/01_campanha_principal/analise_final/RESULTADOS_POR_CASO.csv`. A extensão distingue custo observado (registrado) e custo contabilizado (inclui reservas ou tentativas de custo incerto). O custo externo oficial da campanha principal aparece no fechamento; suas linhas por posição contabilizadas por reserva não equivalem a valores pagos por modelo.

As fontes específicas aparecem no rodapé e nas notas de cada slide. As fontes principais estão em `../pesquisa/02_resultados/01_campanha_principal/analise_final/`, `../pesquisa/02_resultados/02_extensao_multimodelo/analise_descritiva/` e `../documentacao/RESULTADOS_E_LIMITACOES.md`.

A comparação C1/C2/D pertence ao núcleo N-INT. MCPTox e Connor medem superfícies diferentes. A ampliação multimodelo complementa essa evidência, mas suas métricas não devem ser somadas às do núcleo nem usadas para comparação causal entre coortes. Os gráficos e tabelas são objetos vetoriais editáveis, sem imagens rasterizadas: permanecem nítidos em tela cheia e em exportações. Gateway e Donna ficam fora da bateria científica.
