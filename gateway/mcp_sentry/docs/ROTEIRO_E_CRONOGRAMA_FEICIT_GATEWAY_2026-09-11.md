# Roteiro e cronograma otimizado do gateway para a FEICIT

**Data:** 2026-09-11
**Estado:** plano de comunicação e desenvolvimento; não autoriza backend,
OAuth, Google, evento, pista B ou execução T7
**Autoridade operacional:** complementa o plano executivo T7; em conflito de
segurança, prevalece o plano T7

## 1. Resultado mínimo para a FEICIT

O gateway é um protótipo aplicado adjacente à pesquisa principal. A
apresentação deve demonstrar somente quatro fatos:

1. a Donna está exposta ao cliente por sua entrada Sentry, sem entrada direta;
2. a versão aprovada pode executar um efeito pequeno, previamente visualizado
   e confirmado por uma pessoa;
3. uma alteração inerte e não aprovada é detectada antes da fronteira de
   processo;
4. o bloqueio deixa evidência sanitizada de `spawn_attempts: 0` para a sessão.

O Sentry não é apresentado como sandbox do cliente, antivírus, autenticação do
operador, proteção geral de MCP ou produto pronto para produção. Shell,
navegador, rede e outras ferramentas que o host entregue ao cliente ficam fora
de seu controle e devem ser declarados como limitação.

## 2. Escopo congelado

### Caminho crítico

- estabilizar a evidência de ciclo de vida do backend;
- preservar a preparação T7 já revista;
- recarregar a configuração e repetir o preflight `interoperability`;
- obter o segundo OK humano;
- executar uma única vez as pistas A e B do T7;
- sanitizar, revisar e congelar o pacote da FEICIT;
- ensaiar a fala e testar a contingência offline.

### Fora do caminho crítico

- isolamento integral do host;
- execução ou resultados T8;
- envio de e-mail;
- interface gráfica nova;
- suporte a múltiplos backends por instância;
- autenticação criptográfica do operador;
- novas integrações, modelos ou alegações de eficácia.

Esses itens não entram durante a janela FEICIT, salvo correção indispensável de
segurança ou decisão humana que substitua explicitamente este congelamento.

## 3. Processo de desenvolvimento até a feira

As unidades abaixo organizam mudanças de produto e de contrato, não o
diagnóstico rotineiro da execução. Cada mudança termina com testes
proporcionais; revisão independente é exigida quando ela tocar a fronteira de
segurança, e o OK humano antes de commit/push segue o protocolo do repositório.
Só uma mudança crítica fica em andamento por vez.

| Unidade | Saída verificável | Condição de encerramento |
| --- | --- | --- |
| F1 — fecho técnico | contador persistido antes de `Popen`, testes e documentos alinhados | suíte verde, revisão independente e OK humano |
| F2 — preflight carregado | configuração efetiva Sentry-only e preflight `interoperability` | sem Donna direta, baseline `unchanged`, evidência inicial em zero |
| F3 — T7 oficial | pista A concluída e limpa; pista B bloqueada sem spawn | segundo OK prévio, evento removido, token revogado e evidências sanitizadas |
| F4 — pacote da feira | vídeo offline, quadro de quatro estados e fala cronometrada | revisão final, varredura de segredos e congelamento |

Não se altera código, configuração aprovada ou contrato de segurança
improvisadamente dentro do ensaio oficial. Falha local anterior ao spawn do
backend e sem efeito externo pode ser diagnosticada, corrigida e reverificada no
mesmo fluxo quando a correção se limitar ao modo de invocação, permissão do
sandbox, diretório de trabalho ou captura sanitizada de saída. Isso não abre
nova unidade, não exige revisão independente nem renova um OK humano ainda
válido. Nova unidade e revisão proporcional ficam reservadas a mudanças reais
de código, configuração aprovada, manifesto, baseline, envelope ou fronteira de
segurança; dúvida sobre efeito externo continua produzindo `NO_GO` imediato.

## 4. Cronograma realista

A data oficial registrada para a FEICIT é 22--24/09/2026. Embora a janela tenha
sido estimada informalmente em aproximadamente três semanas, em 11/09 restam
cerca de onze dias corridos, ou sete dias úteis, antes da abertura. O plano usa
três ciclos curtos, com margem explícita e sem desenvolvimento funcional nos
dois dias anteriores à feira.

| Período | Prioridade | Entrega |
| --- | --- | --- |
| 11--13/09 | fecho técnico | F1 revisada e preservada |
| 14--16/09 | execução controlada | F2 e F3, uma única execução Google oficial |
| 17--19/09 | evidência e comunicação | F4, gravação sanitizada e revisão final |
| 20--21/09 | congelamento | dois ensaios completos, teste offline e somente correções de comunicação |
| 22--24/09 | FEICIT | pesquisa principal no centro; gateway como protótipo aplicado |

Se F3 não terminar até 16/09, a apresentação usa T6-D/T6-R e a pista local
como protótipo validado, declarando T7 não concluída. Não se comprime limpeza,
revisão ou portão humano para manter a alegação Google.

## 5. Execução oficial e repetição no estande

O efeito Google oficial ocorre uma vez, antes da feira, conforme o plano T7:
prévia, confirmação, criação, verificação, remoção, nova verificação, revogação
e limpeza. A gravação correspondente é sanitizada e torna-se a contingência
principal.

No estande, a demonstração repetível usa somente fixtures locais sem
credenciais. Ela mostra o caminho aprovado e a mudança bloqueada. Repetir o
efeito Google ao vivo não é requisito de aceite; só pode ocorrer com preflight
verde no dia e nova decisão humana específica.

## 6. Roteiro de 3 a 4 minutos

| Tempo | Tela ou fala | Evidência |
| --- | --- | --- |
| 0:00--0:40 | problema: uma tool aprovada pode mudar depois | diagrama Cliente → Sentry → Donna |
| 0:40--1:10 | fronteira e limite: a Donna passa pelo Sentry | configuração sanitizada sem Donna direta |
| 1:10--2:10 | versão aprovada e efeito controlado | gravação da prévia, confirmação, criação e remoção |
| 2:10--3:10 | alteração simulada sem credenciais | hashes, arquivo alterado, `block`, `spawn_attempts: 0` |
| 3:10--3:40 | supervisão e limites | modelo recomenda; pessoa autoriza; gateway executa |

O portão humano de uma recomendação `allow` é explicado no quadro final ou em
clipe curto. Ele não cria uma terceira pista ao vivo. T8 é citado apenas como
trabalho futuro para medir acertos, erros e influência de texto manipulador.

## 7. Quadro visual mínimo

O material da banca deve conter quatro estados, sem terminal excessivo:

| Estado | Mostrar | Não mostrar |
| --- | --- | --- |
| aprovado | hash abreviado e `unchanged` | caminhos privados |
| mudança detectada | arquivo e tipo da mudança | conteúdo secreto ou dados pessoais |
| revisão/bloqueio | decisão e vínculo ao hash | alegação de que o modelo é infalível |
| efeito/ausência | evento removido ou `spawn_attempts: 0` | token, conta ou identificador real |

Hashes completos e versões ficam no relatório sanitizado; na tela, prefixos
curtos bastam para legibilidade. O `gateway_session_id` vincula o contador à
sessão demonstrada.

## 8. Critérios de prontidão

### GO para congelar o pacote

- branch `development_sentry` sincronizada e árvore limpa;
- suíte do gateway e verificador da Donna verdes no ambiente pinado;
- configuração efetiva sem Donna direta;
- T7 oficial concluída ou fallback T6 explicitamente escolhido;
- evento ausente e material OAuth revogado/removido após a pista A;
- pista B sem credencial e com `spawn_attempts: 0`;
- vídeo offline reproduzível e varredura de segredos limpa;
- revisão independente final favorável.

### NO_GO imediato

- segredo ou dado identificável em tela, log, Git ou gravação;
- dúvida sobre o estado do evento ou do token;
- contador de spawn ausente, inválido ou maior que zero na pista B;
- divergência de hash, configuração direta da Donna ou processo órfão;
- tentativa de adicionar função nova durante o congelamento.

## 9. Definição de concluído para a FEICIT

O gateway está pronto quando a banca consegue entender, em menos de quatro
minutos, a diferença entre detecção, recomendação, autorização humana e
execução; quando as duas pistas possuem evidência sanitizada; e quando a mesma
explicação funciona sem internet. T8 e isolamento não integram essa definição.
