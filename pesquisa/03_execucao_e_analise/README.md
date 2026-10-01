# Material de reprodução

Esta pasta preserva somente a configuração mínima e o código diretamente
relacionado às campanhas incluídas nesta edição.

- `pacote_campanha_principal/`: configuração, modelos e origem da campanha;
- `pacote_extensao_multimodelo/`: configuração, formato dos resultados,
  modelos e origem;
- `codigo_execucao_extensao/`: executor e verificador da extensão;
- `codigo_analise_extensao/`: geração da análise descritiva.

Os resultados existentes são evidência preservada. Reexecutar modelos ou APIs
produz uma nova campanha e não substitui os dados incluídos aqui.

## Limite de execução desta cópia

Os scripts foram preservados como referência da execução científica original.
Eles ainda usam caminhos como `baterias_finais/`, `logs_resultados/` e módulos
`tools.*` da estrutura original, que não estão completos neste repositório.
Portanto, esta pasta não é uma instalação autossuficiente para repetir as
campanhas. Não execute os launchers supondo que os novos nomes de pastas já
foram incorporados. Uma reprodução exige restaurar as dependências e a estrutura
original ou realizar uma adaptação explícita, mantendo os dados oficiais intactos.

Os caminhos e hashes em `ARQUIVOS_DE_ORIGEM.json` e nas listas de casos são
registros da origem; não devem ser reescritos apenas por uma reorganização.
