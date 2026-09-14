# Planilhas derivadas dos resultados M2.3 — candidata v1

**Data da cópia:** 2026-09-12
**Classificação:** resultado derivado para leitura humana
**Estado:** candidata local, aguardando reconferência independente; commit/push
já autorizados pelo pesquisador caso o parecer final seja apto
**Base Git da cópia:** `bf4b52acb0ce5843e5f22624cac4bccc9e1af48f`

## Conteúdo

- `Resultados_M2_3_Resumo_Humano_v4_com_extensao.xlsx`: resumo navegável da
  campanha M2.3 original e da extensão multimodelo.
- `Resultados_M2_3_Consolidado.xlsx`: apresentação consolidada dos resultados,
  fontes e limites.
- `Resultados_M2_3_Consolidado_Detalhado.xlsx`: variante detalhada da
  apresentação consolidada.
- `Resultados_M2_3_Consolidado_por_Superficie.xlsx`: visão consolidada dos
  resultados organizada por superfície de observação, com fontes e limites.

## Proveniência científica

As planilhas são produtos derivados. Elas não substituem, alteram nem ampliam
as evidências e análises oficiais que permanecem nas raízes canônicas:

- evidência primária da campanha original:
  `logs_resultados/evidencias/m2_3_campaign_20260907_01/`;
- análise final da campanha original: `baterias_finais/m2_3_analise_v3/`;
- evidência primária da extensão:
  `logs_resultados/evidencias/m2_3_extension_campaign_20260911_221516/`;
- análise descritiva da extensão:
  `baterias_finais/m2_3_extensao_multimodelo_analise_v1_candidate/`.

## Procedimento de preservação

Os quatro arquivos foram copiados byte a byte das fontes locais, sem
edição, reserialização ou nova execução de bateria. `sha256.tsv` registra o
SHA-256 de cada planilha. A regra específica em `.gitattributes` aplica
`-text` aos arquivos XLSX para impedir conversão de bytes pelo Git.

Os diretórios `node_modules` presentes nas saídas locais são dependências do
runtime de geração, não resultados experimentais, e não integram esta unidade.
