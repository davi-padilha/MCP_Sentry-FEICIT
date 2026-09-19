# MCP Sentry — pesquisa, protótipo e materiais FEICIT

Este repositório reúne uma pesquisa sobre a confiabilidade de decisões e
controles de segurança em cenários MCP (*Model Context Protocol*), além de um
protótipo aplicado chamado **MCP Sentry**. O problema investigado é simples: uma
ferramenta MCP previamente aprovada pode ser alterada depois; por isso, o
cliente precisa de uma forma de detectar mudanças antes de iniciar o serviço.

## Principais contribuições

- **Bateria de 90 casos:** casos completos, entradas controladas e hashes para
  verificar a integridade do material experimental.
- **Campanha experimental principal:** 1.500 unidades primárias, com
  persistência de intenção e desfecho terminal reproduzível, comparando as
  condições C1, C2 e D.
- **Extensão multimodelo:** coorte de 450 pares (900 unidades) para descrever a
  sensibilidade a configurações e modelos. Os resultados são descritivos e não
  alegam superioridade causal entre modelos ou provedores.
- **MCP Sentry:** gateway local que compara código, configuração e metadados
  atuais com uma versão aprovada antes de iniciar o backend MCP; ao detectar
  divergência, mantém o backend parado e produz evidências para revisão.
- **Demonstração Donna:** aplicação MCP de apoio, versões aprovada e alterada
  simuladamente, automação e testes para demonstrar o fluxo de proteção.

> Limites importantes: o gateway é um protótipo para MCP local via `stdio`.
> Ele protege somente serviços configurados atrás dele; conexões diretas
> paralelas, comprometimento do ambiente, sandboxing e autenticação estão fora
> de seu escopo.

## Guia rápido da estrutura

### `pesquisa/` — materiais da pesquisa

- `01_casos_finais/` — versão final da bateria de avaliação.
  - `arquivos_da_bateria/` — índice e arquivos JSON dos casos.
    - `casos_completos/` — definição integral dos casos, organizada por
      `nucleo_n_int`, `validacao_codigo_connor` e `validacao_texto_mcptox`.
    - `entradas_dos_modelos/` — versões dos casos fornecidas aos modelos nas
      condições `C1`, `C2` e `D`, separadas pelas mesmas famílias de caso.
  - `controle_de_integridade/` — lista oficial dos 90 casos e hashes dos
    arquivos, usados para conferir a reprodução da bateria.
- `02_resultados/` — dados e relatórios produzidos pelas execuções.
  - `01_campanha_principal/` — resultados da campanha C1/C2/D.
    - `dados_brutos/` — saídas completas e resumo da execução em JSON/JSONL.
    - `analise_final/` — tabelas de métricas, comparação entre camadas, custos,
      tempos e relatório inicial de leitura.
  - `02_extensao_multimodelo/` — resultados da extensão com múltiplos modelos.
    - `dados_brutos/` — registros completos e resumos da coorte.
    - `analise_descritiva/` — distribuição de decisões, métricas por condição,
      custos, tempos e relatório inicial de leitura.
  - `03_planilhas_para_leitura/` — planilhas consolidadas, em formato Excel,
    para consulta dos resultados resumidos e detalhados.
- `03_execucao_e_analise/` — código e pacotes usados para reproduzir as etapas
  de execução e análise.
  - `codigo_execucao_extensao/` — scripts de preparação, campanha, execução
    offline, verificações e testes da extensão.
  - `codigo_analise_extensao/` — análise programática e seus testes.
  - `pacote_campanha_principal/` — configurações, modelos e referência de
    arquivos da campanha principal.
  - `pacote_extensao_multimodelo/` — configurações, modelos, formato de saída
    e referência de arquivos da extensão.

### `gateway/` — protótipo aplicado MCP Sentry

- `codigo_gateway/` — pacote Python instalável do gateway.
  - `mcp_sentry_gateway/` — implementação do controle de integridade,
    ciclo de vida, interface MCP, revisão, CLI e verificações de demonstração.
  - arquivos `.backup-*` e diretórios de backup — cópias de trabalho
    preservadas durante a evolução do protótipo; não são a implementação ativa.
- `configuracao_demo/` — manifestos de configuração das demonstrações Donna e
  Donna/Google controlada.
- `documentacao/` — funcionamento, integração Claude–Sentry–Donna, revisão
  pelo cliente, roteiros, plano de teste e evidências da demonstração.
- `exemplo_mcp/` — servidor MCP mínimo e manifesto de exemplo.
- `testes_gateway/` — testes automatizados do gateway.
  - `support/` — fixtures e utilitários compartilhados pelos testes.

### `demonstracao-donna/` — MCP de apoio à demonstração

- `codigo-fonte-do-mcp/` — implementação da Donna MCP.
  - `donna_mcp/` — servidor, serviços, configuração, auditoria e mutações.
    - `providers/` — provedores simulado, de *rug pull*, Google e abstrações
      usadas para alterná-los.
- `configuracao-do-mcp/` — exemplos de variáveis de ambiente e de configuração
  do cliente MCP.
- `documentacao/` — documentação operacional.
  - `guias/` — prompts e roteiro para a demonstração.
- `ferramentas-para-demonstracao/` — automações auxiliares.
  - `scripts-em-python/` — ativação, autenticação, verificação e comparação
    de versões.
  - `scripts-em-powershell/` — preparação e execução das modalidades de demo,
    diagnóstico e painel.
- `inicializacao-do-mcp/` — pontos de entrada para as versões aprovada,
  demonstrativa, Google e alteração simulada.
- `testes-automatizados/` — testes da Donna, de configuração, isolamento,
  provedores, painel e mutações.
- `versoes-para-demonstracao/` — implementações congeladas para comparação.
  - `integracao-google/` — versões aprovada e alterada simuladamente para a
    integração Google.
  - `simulacao-controlada/` — versões aprovada e alterada simuladamente para a
    demonstração local controlada.

### `FEICIT/` — conteúdos usados para a FEICIT

Inclui o painel de resultados, os banners e os vídeos usados na apresentação.

## Por onde começar

1. Leia os arquivos `LEIA_PRIMEIRO_*` em `pesquisa/02_resultados/` para uma
   visão objetiva dos resultados.
2. Consulte `gateway/documentacao/COMO_FUNCIONA_O_GATEWAY.md` para entender o
   fluxo e os limites do MCP Sentry.
3. Para repetir a demonstração, siga os guias em
   `demonstracao-donna/documentacao/guias/` e os scripts de
   `demonstracao-donna/ferramentas-para-demonstracao/`.
