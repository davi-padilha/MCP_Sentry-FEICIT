# MCP Sentry — pesquisa, gateway e demonstrações

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

**Para entregar o MCP Sentry a um usuário, envie somente a pasta
[pacote-usuario/](pacote-usuario/README.md).** Ela contém:

- `mcp_sentry_gateway-0.8.0-py3-none-any.whl`: instalador Python do gateway.
- `README.md`: requisitos, instalação, configuração e uso.

O usuário precisa ter Python 3.11+ e o runtime do servidor protegido. Os MCPs,
suas credenciais e dados são específicos de cada usuário e não integram este pacote.

| Pasta | Finalidade |
| --- | --- |
| `pacote-usuario/` | Os arquivos que o usuário recebe. |
| `desenvolvimento/gateway/` | Código, testes e empacotamento da versão atual. |
| `prototipo-feicit/` | Versão anterior e cenários da FEICIT, preservados para reprodução. |
| `documentacao/` | Guias do piloto e registros técnicos. |
| `laboratorio/` | Instalações e execuções descartáveis dos testes. |
| `demonstracao-donna/` | Servidor Donna e cenários reutilizáveis. |
| `pesquisa/` | Casos, dados oficiais, análises e referência dos scripts científicos. |
| `materiais-apresentacao/` | Painéis e banners organizados por evento. |

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

### `prototipo-feicit/` — versão anterior usada na FEICIT

- `codigo_gateway/` — pacote Python instalável do gateway.
  - `mcp_sentry_gateway/` — implementação do controle de integridade,
    ciclo de vida, interface MCP, revisão, CLI e verificações de demonstração.
- `configuracao_demo/` — manifestos de configuração das demonstrações Donna e
  Donna/Google controlada.
- `documentacao/` — funcionamento, integração Claude–Sentry–Donna, revisão
  pelo cliente e descrição da demonstração anterior.
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
- `documentacao/` — documentação operacional e roteiro de demonstração.
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

### `materiais-apresentacao/` — materiais das feiras

[Índice dos materiais](materiais-apresentacao/README.md). `feicit/paineis/`
contém o painel original e a variante complementar; `feicit/banners/` contém
os três PDFs. Não há vídeos nesta cópia. Os materiais da MOSTRATEC serão
produzidos ao longo da etapa 5.

### `laboratorio/` — área organizada para futuros testes locais

O [guia do laboratório](laboratorio/README.md) define onde colocar instalações,
dados e execuções descartáveis. A pasta contém apenas esse guia até que novos
testes sejam preparados. As instalações e evidências brutas dos testes técnicos
anteriores em `.lab-smoke` foram removidas na limpeza autorizada; os registros
textuais em `documentacao/VALIDACAO_*.md` foram mantidos como histórico.

## Por onde começar

1. Para instalar e usar o gateway, consulte [pacote-usuario/](pacote-usuario/README.md).
2. Para continuar o projeto, siga o [plano MOSTRATEC](documentacao/PLANO_MOSTRATEC.md):
   etapa 2 encerrada por enquanto; sequência 1 → 3 → 4 e etapa 5 em paralelo.
3. Para consultar a pesquisa, comece por [pesquisa/02_resultados/](pesquisa/02_resultados/README.md).
   Os scripts preservados têm dependências da estrutura original, descritas em
   [material de execução e análise](pesquisa/03_execucao_e_analise/README.md).
4. Para repetir os cenários da Donna, consulte [seu README](demonstracao-donna/README.md).

O protótipo FEICIT permanece separado do gateway atual. Os dados científicos,
casos, listas de integridade e hashes foram preservados nesta reorganização.
