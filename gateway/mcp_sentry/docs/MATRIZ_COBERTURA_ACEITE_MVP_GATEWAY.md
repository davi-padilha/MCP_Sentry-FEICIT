# Matriz de cobertura dos critérios de aceite do MVP gateway

**Data:** 2026-08-31
**Atualização sucessora:** T6-R, 2026-09-01
**Escopo:** somente `aplicacoes/mcp_sentry/`; não mede nem altera A/B/C1/C2/D
**Estado:** T1--T5 e T6-A preservadas em `a29b3b9`; T6-B em `7675597`, T6-C
em `5a1dd0e` e T6-D em `edb39dd`. A prova T6-D é interoperabilidade técnica
local com fallback explícito; o estado sucessor e o bloqueio de T7 estão em
`ADENDO_ESTADO_T6_D_E_PORTAO_T7_2026-09-01.md`.

## Leitura

`Coberto` significa que há teste automatizado diretamente pertinente;
`Parcial` significa que a propriedade foi exercitada, mas falta pelo menos uma
parte expressa do critério; `Lacuna` significa que não há demonstração
automatizada ou ensaio manual suficiente. O ensaio manual não substitui testes
de regressão.

| # | Critério do plano | Evidência automatizada | Ensaio manual | Estado / lacuna honesta |
| --- | --- | --- | --- | --- |
| 1 | Sem baseline não executa backend | `test_t6_a...test_gateway_without_baseline_fails_closed_before_spawn` | — | Coberto na candidata T6-A. |
| 2 | Baseline igual permite `ping` | `test_t3.T3Tests.test_unchanged_backend_runs_from_verified_copy`; testes T5 `test_clean_checkout_uses_suite_interpreter_instead_of_skipping` e `test_simulated_donna_runs_only_from_verified_copy` | Donna: `descrever_donna` passou | Coberto para MCP mínimo e Donna simulada; o teste exige `mcp==1.29.0` e falha, sem skip, se o runtime não estiver preparado. |
| 3 | Mudança pede revisão e não executa | `test_t2...test_rug_pull_needs_review_and_dossier_is_redacted` | — | Coberto. |
| 4 | Dossiê traz código, metadados e configuração | `test_t2...test_rug_pull_needs_review_and_dossier_is_redacted` | — | Coberto. |
| 5 | Sem continuação, bloqueia e oferece A | `test_t4...test_b_without_fixture_keeps_pending_and_offers_explicit_fallback` | — | Coberto por fixture, não por agente real. |
| 6 | `allow` inválido/expirado/schema inválido rejeitado | testes T2 anteriores; `test_t6_a...test_pending_review_expires_and_rejects_verdict`; `...test_authorization_expires_before_spawn` | — | Coberto na candidata T6-A; revisão expira em 30 minutos e autorização em 5 minutos. |
| 7 | `allow` exato, reconexão e uso único | `test_t3...test_allowed_once_is_consumed_before_single_spawn` | — | Coberto no fluxo mínimo. |
| 8 | Mudança após veredito invalida autorização | teste T3 anterior; `test_t6_a...test_mutation_after_allow_invalidates_authorization_before_spawn` | — | Coberto na candidata T6-A. |
| 9 | Arquivo novo omitido é detectado | `test_t6_a...test_new_file_omitted_by_current_manifest_is_detected_from_baseline_roots` | — | Coberto na candidata T6-A pelas raízes fixadas no baseline. |
| 10 | `block` persiste e não inicia | `test_t2...test_invalid_schema_and_block_persist` | — | Coberto. |
| 11 | `approve` não sobrescreve; promoção é separada | teste T1 anterior; `test_t6_a...test_accept_current_is_a_separate_explicit_promotion` | — | Coberto na candidata T6-A. |
| 12 | `stdout` somente MCP | `test_t3...test_stdio_output_contains_only_jsonrpc` | Ensaio UTF-8 sem erro | Coberto para linhas JSON-RPC; ensaio não é teste de ruído completo. |
| 13 | Falha de backend, relatório ou store bloqueia | teste T3 anterior; `test_t6_a...test_report_write_failure_keeps_gateway_closed`; `...test_review_store_failure_does_not_activate_authorization`; `...test_missing_final_decision_report_never_authorizes_spawn`; `...test_concurrent_verdicts_cannot_both_commit` | — | Coberto na candidata T6-A, inclusive transição concorrente e relatório final ausente. |
| 14 | Conteúdo malicioso fica como dado | `test_t2...test_rug_pull_needs_review_and_dossier_is_redacted` | — | Coberto no fixture. |
| 15 | Segredos fictícios não aparecem em artefatos | testes T1/T2 anteriores; `test_t6_a...test_text_reports_reconstruct_inspection_and_decision_without_fixture_secret`; `...test_oauth_and_pem_private_key_material_is_redacted_from_every_artifact`; testes T6-B de observação | — | Coberto para as famílias sintéticas exercitadas, inclusive OAuth snake/camel, `Authorization` Bearer/Basic e PEM comum/criptografado. A redação continua heurística e não é garantia universal de DLP. |
| 16 | JSON e texto reconstituem o fluxo | `test_t6_a...test_text_reports_reconstruct_inspection_and_decision_without_fixture_secret` | — | Coberto na candidata T6-A por resumos de inspeção e decisão vinculados aos hashes. |

## Conclusão de cobertura

T1--T5 demonstraram o caminho protegido principal e o ensaio Donna simulado.
T6-A, preservada em `a29b3b9`, fecha por teste as lacunas 1, 9 e 16 e os itens parciais 6,
8, 11, 13 e 15, além de reservar `sentry_*` ao gateway, inclusive diante de
baseline legado. T6-C e T6-D estão preservadas; T6-D sustenta somente prova
técnica local com fallback explícito. T7 e T8 permanecem fora desta unidade e
atrás de seus portões próprios.

T6-R reexecutou a suíte em 2026-09-01: 61 testes passaram, sem skip, incluindo
a Donna simulada com validação de `mcp==1.29.0`. A unidade também acrescenta
teste adversarial OAuth/PEM e torna falha de remoção da cópia verificada
observável sem mascarar a falha primária do backend.
Seu documento sucessor registra as limitações e os portões ainda fechados.

## Cobertura candidata T6-B — conformidade MCP/Codex

| Controle | Evidência automatizada | Estado / limite |
| --- | --- | --- |
| `instructions` no `initialize` | `test_t6_b...test_initialize_instructions_negotiates_and_records_observation_without_authentication_claim` | Instrução curta, com workflow e fallback; orientação não é enforcement. |
| Negociação MCP e observação não autenticante | testes T6-B de `initialize` válido, versão desconhecida, entrada inválida e versão selecionada no backend | Seleciona `2025-06-18` para versão cliente desconhecida e aceita `2025-03-26`; `clientInfo`/capacidades são registro observável, não prova de identidade. |
| Schema público de `sentry_submit_verdict` | `test_t6_b...test_control_tools_publish_complete_verdict_and_output_schemas` | Campos, enum, hashes e `additionalProperties: false` publicados no schema aninhado `verdict`. |
| `outputSchema` e fallback textual | testes T6-B de schemas, sucessos, erros e `test_every_control_response_has_matching_json_text_fallback` | Cada tool de controle declara variantes de sucesso e erro fechado, e retorna o mesmo objeto em `structuredContent` e JSON em `content`. |
| Paginação e fallback | `test_t6_b...test_pagination_is_explicit_and_out_of_range_fails_closed`; `...test_review_gate_keeps_same_turn_and_explicit_fallback_in_both_result_forms` | `total_pages`, `has_more` e `next_page`; página inexistente bloqueia fechado. |
| Sigilo nos registros de inicialização | testes T6-B para chave de segredo, `Authorization`, camelCase e segredo embutido em texto | Dados observáveis com formato de segredo são redigidos estruturalmente, sem corromper JSON; não há alegação de autenticação. |

T6-B não configura Codex, não executa cliente real, não chama rede e não prova
interoperabilidade. T6-D está preservada em `edb39dd`, mas não autoriza
integração Google, julgamento semântico correto ou T7/T8; ambos continuam
bloqueados.

## Cobertura candidata T6-C — preparação segura para efeito futuro

| Controle | Evidência automatizada | Estado / limite |
| --- | --- | --- |
| Envelope de execução promovido separadamente | `test_t6_c...test_execution_envelope_blocks_changed_command_until_separate_operator_attestation` | `command`, `cwd`, raízes, runtime paths e nomes de passthrough ficam em artefato confiado fora do manifesto; `accept-current` não o altera. A frase de confirmação é atestação operacional, não autenticação. |
| Ambiente mínimo e passthrough | `test_t6_c...test_backend_environment_is_minimal_and_secret_passthrough_value_never_enters_store` | Não herda `os.environ` integralmente. Apenas nomes confiados podem receber valores do ambiente; valores não entram no manifesto, hash, relatório ou store. Nenhuma credencial real é usada. |
| Falha limitada | `test_t6_c...test_stderr_is_drained_and_capped`; `...test_verified_copy_cleanup_failure_is_observable_and_path_is_retained`; `...test_cleanup_failure_does_not_mask_primary_backend_failure`; `...test_copy_failure_removes_partial_verified_tree_before_returning` | Leituras de resposta têm limite de 10 s; `stderr` é drenado e limitado a 16 KiB; falha de limpeza preserva o caminho, gera erro e não oculta a falha primária; falha de cópia remove imediatamente a árvore parcial. Não é sandbox de SO ou política de rede. |
| Configuração temporária e bypass | `test_t6_c...test_temporary_config_is_in_memory_sentry_only_and_detects_direct_bypass` | Gera e valida somente em memória a entrada `Donna_via_Sentry` (rótulo humano: Donna via Sentry); uma entrada direta `Donna` ou outra entrada é bypass e bloqueia. Não lê, escreve ou configura o Codex. |

T6-C foi preservada em `5a1dd0e`. Não habilita credenciais, rede, efeito
externo, Donna real nem a prova T6-D.

O envelope confiado protege contra promoção pelo veredito semântico, não contra
adulteração direta do store por quem já controla o host. O store e o host são
parte confiada do recorte científico controlado; essa limitação não bloqueia
T7, mas impede alegar proteção contra comprometimento local.

## T6-D — prova local preservada; limites mantidos

`PLANO_EXECUTIVO_T6_D_INTEROPERABILIDADE_2026-09-01.md` define a futura prova
Codex com fixture benigna/perigosa, leitura de todas as páginas, schema,
reconexão, fallback e não execução do caso perigoso. Há testes locais de
preparação das fixtures e do ciclo MCP benigno; a prova Codex real foi
executada com configuração efêmera e está registrada em
`RESULTADO_T6_D_INTEROPERABILIDADE_2026-09-01.md`. A preservação de T6-D no
commit `edb39dd` não constitui resultado científico, não demonstra integração
Google, correção semântica do veredito ou segurança de produção e não autoriza
T7/T8. O registro técnico não é reescrito; a sucessão de estado é declarada no
adendo correspondente.
