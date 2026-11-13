````{test} test_intent_decomposition_dag
:id: TEST-01
:entrega: DSM2
:status: executado
:verifies: REQ-F01
:derived_from: PROT-DEL

`test_intent_decomposition_dag()` — tipo *protocolo-nominal*.  
**Resultado esperado:** 'fechar o mês' gera DAG AG-CUS∥AG-ORC → AG-RES → AG-CIN → AG-REL e resposta final inform  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_unknown_intent_not_understood
:id: TEST-02
:entrega: DSM2
:status: executado
:verifies: REQ-F01
:derived_from: PROT-SOL

`test_unknown_intent_not_understood()` — tipo *protocolo-negativo*.  
**Resultado esperado:** intenção fora do catálogo termina em RECUSADA com not-understood  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_delegation_rejects_inform_before_agree
:id: TEST-03
:entrega: DSM2
:status: executado
:verifies: REQ-F01
:derived_from: PROT-DEL

`test_delegation_rejects_inform_before_agree()` — tipo *protocolo-negativo*.  
**Resultado esperado:** inform em AGUARDANDO levanta ProtocolViolation  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_contribution_margin_matches_gold
:id: TEST-04
:entrega: DSM2
:status: executado
:verifies: REQ-F02
:derived_from: ROLE-CUS

`test_contribution_margin_matches_gold()` — tipo *cenario*.  
**Resultado esperado:** margens por produto/UN iguais ao gabarito com proveniência  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_budget_variance_flags_threshold
:id: TEST-05
:entrega: DSM2
:status: executado
:verifies: REQ-F03
:derived_from: ROLE-ORC

`test_budget_variance_flags_threshold()` — tipo *cenario*.  
**Resultado esperado:** somente desvios plantados acima do limiar são sinalizados  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_results_query_ref_to_costs
:id: TEST-06
:entrega: DSM2
:status: executado
:verifies: REQ-F04
:derived_from: PROT-QRY

`test_results_query_ref_to_costs()` — tipo *protocolo-nominal*.  
**Resultado esperado:** query-ref → inform antes do inform final de AG-RES; DRE igual ao gabarito  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_query_ref_rejects_unsolicited_inform
:id: TEST-07
:entrega: DSM2
:status: executado
:verifies: REQ-F04
:derived_from: PROT-QRY

`test_query_ref_rejects_unsolicited_inform()` — tipo *protocolo-negativo*.  
**Resultado esperado:** inform com conversation_id desconhecido é rejeitado  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_critical_nonconformity_vetoes_close
:id: TEST-08
:entrega: DSM2
:status: executado
:verifies: REQ-F05
:derived_from: PROT-CMP

`test_critical_nonconformity_vetoes_close()` — tipo *protocolo-negativo*.  
**Resultado esperado:** publicar em VETADO é rejeitado; waiver humano libera com ressalva  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_planted_nonconformities_detected
:id: TEST-09
:entrega: DSM2
:status: executado
:verifies: REQ-F05
:derived_from: NORM-04

`test_planted_nonconformities_detected()` — tipo *cenario*.  
**Resultado esperado:** recall 100% das críticas plantadas (alçada, SoD, duplicidade)  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_report_template_without_llm
:id: TEST-10
:entrega: DSM2
:status: executado
:verifies: REQ-F06, REQ-NF01
:derived_from: ROLE-REL

`test_report_template_without_llm()` — tipo *cenario*.  
**Resultado esperado:** relatório completo com flag desligada e rede bloqueada  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_memory_only_approved_with_provenance
:id: TEST-11
:entrega: DSM3
:status: executado
:verifies: REQ-F07
:derived_from: NORM-08

`test_memory_only_approved_with_provenance()` — tipo *seguranca*.  
**Resultado esperado:** saída não aprovada não é indexada; aprovada é recuperada com fonte  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_external_action_requires_approval
:id: TEST-12
:entrega: DSM3
:status: executado
:verifies: REQ-S01
:derived_from: PROT-APR

`test_external_action_requires_approval()` — tipo *seguranca*.  
**Resultado esperado:** ajuste no ERP fica PENDENTE; execute sem approve levanta ApprovalRequired  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_denied_action_never_executes
:id: TEST-13
:entrega: DSM3
:status: executado
:verifies: REQ-S01
:derived_from: NORM-02

`test_denied_action_never_executes()` — tipo *seguranca*.  
**Resultado esperado:** ação fora da allowlist nunca chega ao conector MCP  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_period_lock_conflict_rejected
:id: TEST-14
:entrega: DSM2
:status: executado
:verifies: REQ-S02
:derived_from: PROT-LCK

`test_period_lock_conflict_rejected()` — tipo *concorrencia*.  
**Resultado esperado:** segunda reserva sobreposta recebe reserve-failure; TTL libera  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_llm_numeric_mismatch_falls_back
:id: TEST-15
:entrega: DSM3
:status: executado
:verifies: REQ-S03, REQ-F06
:derived_from: NORM-05

`test_llm_numeric_mismatch_falls_back()` — tipo *seguranca*.  
**Resultado esperado:** mock LLM com número alterado aciona template e log de fallback  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_trace_causal_reconstruction
:id: TEST-16
:entrega: DSM2
:status: executado
:verifies: REQ-O01
:derived_from: SVC-AUD

`test_trace_causal_reconstruction()` — tipo *observabilidade*.  
**Resultado esperado:** sequência causal completa reconstruída pelo conversation_id  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_prompt_log_only_when_llm_enabled
:id: TEST-17
:entrega: DSM3
:status: executado
:verifies: REQ-O02
:derived_from: NORM-07

`test_prompt_log_only_when_llm_enabled()` — tipo *observabilidade*.  
**Resultado esperado:** registro de prompt existe sse flag ligada  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_cost_log_per_call_and_task
:id: TEST-18
:entrega: DSM3
:status: executado
:verifies: REQ-O03
:derived_from: SVC-AUD

`test_cost_log_per_call_and_task()` — tipo *observabilidade*.  
**Resultado esperado:** soma por chamada = total da tarefa; zero com flag desligada  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_dashboard_filters_and_auth
:id: TEST-19
:entrega: DSM3
:status: executado
:verifies: REQ-O04
:derived_from: SVC-AUD

`test_dashboard_filters_and_auth()` — tipo *integracao*.  
**Resultado esperado:** filtros retornam o recorte exato; acesso anônimo negado  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_model_swap_without_redeploy
:id: TEST-20
:entrega: DSM3
:status: executado
:verifies: REQ-C01
:derived_from: SVC-MOD

`test_model_swap_without_redeploy()` — tipo *configuracao*.  
**Resultado esperado:** troca de modelo vale na próxima tarefa sem reiniciar agentes  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_llm_not_allowed_roles_rejected
:id: TEST-21
:entrega: DSM3
:status: executado
:verifies: REQ-C01
:derived_from: NORM-07

`test_llm_not_allowed_roles_rejected()` — tipo *configuracao*.  
**Resultado esperado:** habilitar LLM em AG-ORQ, AG-CUS ou AG-CIN é rejeitado na validação  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_token_limit_exceeded_fallback
:id: TEST-22
:entrega: DSM3
:status: executado
:verifies: REQ-C01, REQ-O03
:derived_from: NORM-07

`test_token_limit_exceeded_fallback()` — tipo *configuracao*.  
**Resultado esperado:** cota esgotada bloqueia chamada e usa template  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_redaction_fail_closed
:id: TEST-23
:entrega: DSM3
:status: executado
:verifies: REQ-P01
:derived_from: NORM-06

`test_redaction_fail_closed()` — tipo *seguranca*.  
**Resultado esperado:** segredo/CPF sintético sanitizado; falha de sanitização recusa gravação  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_offline_seeded_reproducibility
:id: TEST-24
:entrega: DSM2
:status: executado
:verifies: REQ-NF01
:derived_from: SVC-MCP

`test_offline_seeded_reproducibility()` — tipo *reprodutibilidade*.  
**Resultado esperado:** mesmo seed → mesmo hash de saída, sem rede  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_versions_recorded_in_logs
:id: TEST-25
:entrega: DSM3
:status: executado
:verifies: REQ-NF02
:derived_from: SVC-AUD

`test_versions_recorded_in_logs()` — tipo *observabilidade*.  
**Resultado esperado:** todo log contém versões de prompt, regras e configuração  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_specialist_failure_retry_then_abort
:id: TEST-26
:entrega: DSM2
:status: executado
:verifies: REQ-F01
:derived_from: PROT-DEL

`test_specialist_failure_retry_then_abort()` — tipo *protocolo-negativo*.  
**Resultado esperado:** especialista que expira duas vezes: um reenvio, depois failure ao solicitante, reserva liberada e nada publicado  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_budget_agent_queries_controls_and_reconsiders
:id: TEST-27
:entrega: DSM2
:status: executado
:verifies: REQ-F03, REQ-F04
:derived_from: ROLE-ORC

`test_budget_agent_queries_controls_and_reconsiders()` — tipo *cenario*.  
**Resultado esperado:** AG-ORC consulta o AG-CIN por PROT-QRY sem o Orquestrador, revisa a crença e abandona a intenção de sinalizar; classificação igual ao gabarito e o baseline erra  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_budget_plan_failure_replans_on_timeout
:id: TEST-28
:entrega: DSM2
:status: executado
:verifies: REQ-F03, REQ-F01
:derived_from: PROT-QRY

`test_budget_plan_failure_replans_on_timeout()` — tipo *protocolo-negativo*.  
**Resultado esperado:** query-ref perdida expira; o plano falha e o AG-ORC replaneja para o fallback com ressalva, sem deixar de responder  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_source_divergence_revises_belief
:id: TEST-29
:entrega: DSM2
:status: executado
:verifies: REQ-F03
:derived_from: ROLE-ORC

`test_source_divergence_revises_belief()` — tipo *cenario*.  
**Resultado esperado:** planilha diverge do ERP: crença revisada a partir do ERP, sem falso desvio, com ressalva no relatório  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_veto_correction_reconsidered_by_controls
:id: TEST-30
:entrega: DSM2
:status: executado
:verifies: REQ-F05
:derived_from: PROT-CMP

`test_veto_correction_reconsidered_by_controls()` — tipo *protocolo-nominal*.  
**Resultado esperado:** veto com correção sugerida vence por utilidade; correção humana percebida via MCP; intenção reconsiderada; publicado sem ressalva  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_partial_correction_keeps_veto_then_blocks
:id: TEST-31
:entrega: DSM2
:status: executado
:verifies: REQ-F05
:derived_from: NORM-04

`test_partial_correction_keeps_veto_then_blocks()` — tipo *protocolo-negativo*.  
**Resultado esperado:** correção parcial: AG-CIN mantém o veto sem novo ciclo e o prazo esgotado bloqueia a publicação  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_completion_metric_excludes_failures
:id: TEST-32
:entrega: DSM2
:status: executado
:verifies: REQ-F01
:derived_from: PROT-SOL

`test_completion_metric_excludes_failures()` — tipo *cenario*.  
**Resultado esperado:** MET-01 não conta failure como conclusão; MET-13 mede a resposta explícita  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_mas_vs_centralized_baseline
:id: TEST-33
:entrega: DSM2
:status: executado
:verifies: REQ-F03, REQ-F05
:derived_from: SVC-AUD

`test_mas_vs_centralized_baseline()` — tipo *experimento*.  
**Resultado esperado:** mesmas seeds: o SMA não publica crítica sem tratamento e acerta desvios atribuídos; custa mais mensagens; com perda de mensagens o workflow publica e o SMA falha  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_live_operator_controls_and_human_decision
:id: TEST-34
:entrega: DSM2
:status: executado
:verifies: REQ-O04, REQ-F05
:derived_from: SVC-AUD

`test_live_operator_controls_and_human_decision()` — tipo *integracao*.  
**Resultado esperado:** execução ao vivo pausa, desliga agentes e aguarda a decisão humana do dashboard; o snapshot expõe crenças e intenções  
**Execução:** DSM2 (status atual: executado).
````

````{test} test_sma_office_day_answers_every_request
:id: TEST-35
:entrega: DSM3
:status: executado
:verifies: REQ-F01, REQ-S02
:derived_from: PROT-LCK

`test_sma_office_day_answers_every_request()` — tipo *cenario*.  
**Resultado esperado:** expediente da SMA com três competências: toda solicitação tem resposta explícita e só o fechamento concorrente do mesmo mês é recusado  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_rules_and_bdi_follow_company_size
:id: TEST-36
:entrega: DSM3
:status: executado
:verifies: REQ-F05, REQ-F03
:derived_from: NORM-04

`test_rules_and_bdi_follow_company_size()` — tipo *cenario*.  
**Resultado esperado:** em micro, pequena, média e grande o porte vem da base normativa (normas.perfil): alçadas, severidades e pesos dos desejos mudam; todas as inconformidades do gabarito são detectadas  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_micro_company_has_no_erp_and_compensating_control
:id: TEST-37
:entrega: DSM3
:status: executado
:verifies: REQ-F03, REQ-F05
:derived_from: SVC-MCP

`test_micro_company_has_no_erp_and_compensating_control()` — tipo *cenario*.  
**Resultado esperado:** microempresa sem ERP: tool do ERP indisponível, realizado da planilha, SoD inevitável vira ressalva com controle compensatório  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_large_company_treats_cutoff_as_critical
:id: TEST-38
:entrega: DSM3
:status: executado
:verifies: REQ-F05
:derived_from: NORM-04

`test_large_company_treats_cutoff_as_critical()` — tipo *cenario*.  
**Resultado esperado:** grande empresa veta competência errada (corte material) e reavalia após reclassificação; na média é só ressalva  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_spreadsheet_templates_validate_and_report_errors
:id: TEST-39
:entrega: DSM3
:status: executado
:verifies: REQ-NF01, REQ-F02
:derived_from: SVC-MCP

`test_spreadsheet_templates_validate_and_report_errors()` — tipo *integracao*.  
**Resultado esperado:** modelos Excel gerados; planilha com erro de digitação é recusada com aba, coluna e linha  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_agents_close_month_from_filled_spreadsheet_and_write_back_correction
:id: TEST-40
:entrega: DSM3
:status: executado
:verifies: REQ-F01, REQ-F05
:derived_from: SVC-MCP

`test_agents_close_month_from_filled_spreadsheet_and_write_back_correction()` — tipo *integracao*.  
**Resultado esperado:** agentes fecham o mês sobre a planilha preenchida com proveniência arquivo#aba; a correção aprovada é gravada na planilha  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_excel_mcp_server_over_stdio
:id: TEST-41
:entrega: DSM3
:status: executado
:verifies: REQ-S01, REQ-NF01
:derived_from: NORM-02

`test_excel_mcp_server_over_stdio()` — tipo *integracao*.  
**Resultado esperado:** servidor MCP de Excel por stdio: initialize, tools/list, leitura de aba, acesso fora da pasta negado e sem sobrescrita  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_dashboard_downloads_template_uploads_spreadsheet_and_runs
:id: TEST-42
:entrega: DSM3
:status: executado
:verifies: REQ-O04, REQ-F01
:derived_from: SVC-AUD

`test_dashboard_downloads_template_uploads_spreadsheet_and_runs()` — tipo *integracao*.  
**Resultado esperado:** dashboard baixa modelo, recusa planilha inválida, aceita a válida e reinicia o escritório sobre ela  
**Execução:** DSM3 (status atual: executado).
````

````{test} veto vira notificação; o humano corrige no ERP e o AG-CIN reconsidera
:id: TEST-43
:entrega: DSM2
:status: executado
:verifies: REQ-O04, REQ-F05
:derived_from: PROT-CMP

`veto vira notificação; o humano corrige no ERP e o AG-CIN reconsidera()` — tipo *uso-real*.  
**Resultado esperado:** no navegador, o sino mostra o veto, o humano corrige e a mente do AG-CIN mostra a reconsideração  
**Execução:** DSM2 (status atual: executado).
````

````{test} desligar o AG-CIN gera perdas, timeout, replanejamento do AG-ORC e falha explícita
:id: TEST-44
:entrega: DSM2
:status: executado
:verifies: REQ-F01, REQ-O04
:derived_from: PROT-QRY

`desligar o AG-CIN gera perdas, timeout, replanejamento do AG-ORC e falha explícita()` — tipo *uso-real*.  
**Resultado esperado:** operador desliga um agente pelo dashboard; perdas, timeout e replanejamento aparecem e o pedido falha explicitamente  
**Execução:** DSM2 (status atual: executado).
````

````{test} empresa sem ERP: baixa o modelo, envia a planilha e o escritório roda sobre ela
:id: TEST-45
:entrega: DSM3
:status: executado
:verifies: REQ-F01, REQ-O04
:derived_from: SVC-MCP

`empresa sem ERP: baixa o modelo, envia a planilha e o escritório roda sobre ela()` — tipo *uso-real*.  
**Resultado esperado:** usuário baixa o modelo, envia a planilha pelo navegador e os agentes leem mcp://excel/arquivo#aba  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_forged_human_decision_from_unknown_sender_is_rejected
:id: TEST-46
:entrega: DSM3
:status: executado
:verifies: REQ-S04, REQ-F05
:derived_from: PROT-APR

`test_forged_human_decision_from_unknown_sender_is_rejected()` — tipo *seguranca*.  
**Resultado esperado:** decisao_humana de remetente inexistente é rejeitada; o fechamento vetado termina bloqueado e nada é publicado  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_spoofed_approver_identity_without_credential_is_rejected
:id: TEST-47
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: PROT-APR

`test_spoofed_approver_identity_without_credential_is_rejected()` — tipo *seguranca*.  
**Resultado esperado:** approve em nome do APR sem a credencial dele, ou com a de outro agente, é rejeitado; o ticket segue pendente  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_registered_agent_without_role_cannot_approve
:id: TEST-48
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: NORM-09

`test_registered_agent_without_role_cannot_approve()` — tipo *seguranca*.  
**Resultado esperado:** AG-REL e AG-ORQ não podem emitir approve: papel sem permissão  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_local_transition_by_unauthorized_identity_is_rejected
:id: TEST-49
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: PROT-CMP

`test_local_transition_by_unauthorized_identity_is_rejected()` — tipo *seguranca*.  
**Resultado esperado:** advance por identificador desconhecido, sem credencial, por papel sem permissão ou fora da FSM é rejeitado  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_reply_to_non_participant_receiver_is_rejected
:id: TEST-50
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: PROT-DEL

`test_reply_to_non_participant_receiver_is_rejected()` — tipo *seguranca*.  
**Resultado esperado:** resposta endereçada a quem não é a contraparte da conversa é rejeitada  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_malformed_request_does_not_crash_simulation
:id: TEST-51
:entrega: DSM3
:status: executado
:verifies: REQ-S04, REQ-F01
:derived_from: PROT-SOL

`test_malformed_request_does_not_crash_simulation()` — tipo *seguranca*.  
**Resultado esperado:** pedido sem campos, com tipo errado, prazo no passado ou outra ontologia é rejeitado sem KeyError; a simulação segue  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_agent_exception_is_isolated_and_answered
:id: TEST-52
:entrega: DSM3
:status: executado
:verifies: REQ-S04, REQ-F01
:derived_from: PROT-DEL

`test_agent_exception_is_isolated_and_answered()` — tipo *robustez*.  
**Resultado esperado:** exceção de um agente vira erro_agente e resposta explícita (refuse); o solicitante recebe failure  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_content_tampering_after_send_is_detected
:id: TEST-53
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: SVC-A2A

`test_content_tampering_after_send_is_detected()` — tipo *seguranca*.  
**Resultado esperado:** conteúdo copiado no envio; alteração da mensagem enfileirada é detectada pelo hash e descartada  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_identity_impersonation_on_register_is_rejected
:id: TEST-54
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: SVC-A2A

`test_identity_impersonation_on_register_is_rejected()` — tipo *seguranca*.  
**Resultado esperado:** registrar identidade já existente, papel fora do diretório ou papel desconhecido é recusado  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_adversarial_scenario_rejects_every_attack
:id: TEST-55
:entrega: DSM3
:status: executado
:verifies: REQ-S04, REQ-S01
:derived_from: PROT-APR

`test_adversarial_scenario_rejects_every_attack()` — tipo *seguranca*.  
**Resultado esperado:** cenário ataque_decisao_forjada: 13 ataques, 0 aceitos, todos auditados; publicação bloqueada no prazo  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_nominal_scenarios_have_no_rejection_or_agent_error
:id: TEST-56
:entrega: DSM3
:status: executado
:verifies: REQ-S04, REQ-NF01
:derived_from: NORM-09

`test_nominal_scenarios_have_no_rejection_or_agent_error()` — tipo *regressao*.  
**Resultado esperado:** nos cenários nominais os agentes cumprem esquema, papel e FSM: nenhuma rejeição nem erro  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_approval_bound_to_request_veto_and_ticket
:id: TEST-57
:entrega: DSM3
:status: executado
:verifies: REQ-S01, REQ-S04
:derived_from: PROT-APR

`test_approval_bound_to_request_veto_and_ticket()` — tipo *seguranca*.  
**Resultado esperado:** approve com hash de veto, solicitação ou ticket diferentes, ou sem o hash, é rejeitado  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_duplicate_approval_is_rejected
:id: TEST-58
:entrega: DSM3
:status: executado
:verifies: REQ-S01, REQ-S04
:derived_from: PROT-APR

`test_duplicate_approval_is_rejected()` — tipo *seguranca*.  
**Resultado esperado:** segunda decisão para o mesmo ticket é rejeitada; o waiver vale uma vez  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_late_approval_after_deadline_is_discarded
:id: TEST-59
:entrega: DSM3
:status: executado
:verifies: REQ-S01
:derived_from: PROT-APR

`test_late_approval_after_deadline_is_discarded()` — tipo *seguranca*.  
**Resultado esperado:** decisão após o prazo do ticket é descartada; bloqueio por expiração  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_approval_reuse_across_veto_cycles_is_rejected
:id: TEST-60
:entrega: DSM3
:status: executado
:verifies: REQ-S01, REQ-S04
:derived_from: NORM-10

`test_approval_reuse_across_veto_cycles_is_rejected()` — tipo *seguranca*.  
**Resultado esperado:** aprovação do 1º ciclo de veto não serve para o 2º (correção nem waiver)  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_approver_role_limits_decisions
:id: TEST-61
:entrega: DSM3
:status: executado
:verifies: REQ-S01
:derived_from: NORM-10

`test_approver_role_limits_decisions()` — tipo *seguranca*.  
**Resultado esperado:** aprovador cadastrado como analista não concede waiver, mas pode aprovar correção  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_approver_involved_in_vetoed_entry_cannot_decide
:id: TEST-62
:entrega: DSM3
:status: executado
:verifies: REQ-S01
:derived_from: NORM-10

`test_approver_involved_in_vetoed_entry_cannot_decide()` — tipo *seguranca*.  
**Resultado esperado:** pessoa que criou ou aprovou o lançamento vetado não decide sobre ele (SoD da aprovação)  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_waiver_requires_justification_and_correction_must_be_suggested
:id: TEST-63
:entrega: DSM3
:status: executado
:verifies: REQ-S01
:derived_from: NORM-10

`test_waiver_requires_justification_and_correction_must_be_suggested()` — tipo *seguranca*.  
**Resultado esperado:** waiver sem justificativa mínima e correção fora das sugeridas pelo AG-CIN são rejeitados  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_reject_blocks_publication_and_is_audited
:id: TEST-64
:entrega: DSM3
:status: executado
:verifies: REQ-S01, REQ-F05
:derived_from: PROT-APR

`test_reject_blocks_publication_and_is_audited()` — tipo *protocolo-nominal*.  
**Resultado esperado:** reject bloqueia a publicação; ticket guarda aprovador, justificativa e decisão  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_recurring_violation_after_waiver_denies_new_waiver
:id: TEST-65
:entrega: DSM3
:status: executado
:verifies: REQ-F07, REQ-S01
:derived_from: SVC-MEM

`test_recurring_violation_after_waiver_denies_new_waiver()` — tipo *cenario*.  
**Resultado esperado:** reincidência do padrão após waiver: AG-CIN cita MEM-0001, a política nega novo waiver e o humano corrige  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_memory_retention_expires_old_entries
:id: TEST-66
:entrega: DSM3
:status: executado
:verifies: REQ-F07, REQ-P01
:derived_from: SVC-MEM

`test_memory_retention_expires_old_entries()` — tipo *seguranca*.  
**Resultado esperado:** entradas mais antigas que a retenção expiram na consulta  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_memory_persists_across_runs_and_flags_recidivism
:id: TEST-67
:entrega: DSM3
:status: executado
:verifies: REQ-F07
:derived_from: SVC-MEM

`test_memory_persists_across_runs_and_flags_recidivism()` — tipo *integracao*.  
**Resultado esperado:** memória gravada num processo é carregada no seguinte e muda a decisão (POL-06)  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_memory_file_has_no_personal_names
:id: TEST-68
:entrega: DSM3
:status: executado
:verifies: REQ-P01
:derived_from: NORM-06

`test_memory_file_has_no_personal_names()` — tipo *seguranca*.  
**Resultado esperado:** arquivo de memória usa pseudônimos; nomes de pessoas não aparecem  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_trace_tampering_is_detected
:id: TEST-69
:entrega: DSM3
:status: executado
:verifies: REQ-O01, REQ-P01
:derived_from: SVC-AUD

`test_trace_tampering_is_detected()` — tipo *seguranca*.  
**Resultado esperado:** linha alterada ou removida do JSONL quebra a cadeia de hashes (TraceAdulterado)  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_credentials_never_appear_in_the_trace
:id: TEST-70
:entrega: DSM3
:status: executado
:verifies: REQ-P01, REQ-S04
:derived_from: NORM-06

`test_credentials_never_appear_in_the_trace()` — tipo *seguranca*.  
**Resultado esperado:** credenciais do barramento nunca aparecem no trace gravado  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_real_provider_unavailable_falls_back_offline
:id: TEST-71
:entrega: DSM3
:status: executado
:verifies: REQ-F06, REQ-NF01
:derived_from: SVC-MOD

`test_real_provider_unavailable_falls_back_offline()` — tipo *configuracao*.  
**Resultado esperado:** provedor real sem SDK ou rede registra fallback e entrega o template; a suíte segue offline  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_invalid_period_or_unknown_entity_is_refused
:id: TEST-72
:entrega: DSM3
:status: executado
:verifies: REQ-S04, REQ-F01
:derived_from: PROT-SOL

`test_invalid_period_or_unknown_entity_is_refused()` — tipo *seguranca*.  
**Resultado esperado:** competência fora de AAAA-MM barrada na entrada; entidade desconhecida recebe refuse sem delegar nem erro de agente  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_dashboard_mutations_require_session_token
:id: TEST-73
:entrega: DSM3
:status: executado
:verifies: REQ-O04, REQ-S04
:derived_from: SVC-AUD

`test_dashboard_mutations_require_session_token()` — tipo *seguranca*.  
**Resultado esperado:** POST sem token, com token errado, Origin de outro site ou Host estranho recebe 403 e não chega à simulação  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_gateway_rejects_declared_identity_without_credential
:id: TEST-74
:entrega: DSM3
:status: executado
:verifies: REQ-S04, REQ-S01
:derived_from: SVC-MCP

`test_gateway_rejects_declared_identity_without_credential()` — tipo *seguranca*.  
**Resultado esperado:** gateway MCP recusa identidade declarada sem credencial (ou com a de outro agente); barramento guarda só hashes de credenciais  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_memory_rejects_forged_identity_and_mismatched_ticket
:id: TEST-75
:entrega: DSM3
:status: executado
:verifies: REQ-F07, REQ-S04
:derived_from: SVC-MEM

`test_memory_rejects_forged_identity_and_mismatched_ticket()` — tipo *seguranca*.  
**Resultado esperado:** memória recusa identidade declarada, ticket rejeitado como waiver, outra competência ou lançamento fora da decisão  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_tampered_memory_file_is_discarded_on_load
:id: TEST-76
:entrega: DSM3
:status: executado
:verifies: REQ-F07, REQ-P01
:derived_from: SVC-MEM

`test_tampered_memory_file_is_discarded_on_load()` — tipo *seguranca*.  
**Resultado esperado:** entrada inventada (assinatura HMAC) ou malformada no arquivo é descartada e o AG-CIN segue funcionando  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_trace_truncation_and_recomputed_chain_are_detected
:id: TEST-77
:entrega: DSM3
:status: executado
:verifies: REQ-O01, REQ-P01
:derived_from: SVC-AUD

`test_trace_truncation_and_recomputed_chain_are_detected()` — tipo *seguranca*.  
**Resultado esperado:** corte do fim, cadeia recalculada sem a chave e trace sem hashes são acusados; replay exige --sem-verificar  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_lost_approval_never_leaves_request_without_answer
:id: TEST-78
:entrega: DSM3
:status: executado
:verifies: REQ-F01, REQ-S01
:derived_from: PROT-APR

`test_lost_approval_never_leaves_request_without_answer()` — tipo *seguranca*.  
**Resultado esperado:** approve perdido em trânsito: ticket expira em APROVADA, failure explícito e reserva liberada  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_non_serializable_content_is_rejected_before_any_side_effect
:id: TEST-79
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: PROT-APR

`test_non_serializable_content_is_rejected_before_any_side_effect()` — tipo *seguranca*.  
**Resultado esperado:** conteúdo não JSON é rejeitado antes de a política ou a FSM mudarem; waiver fecha o ticket em EXECUTADA  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_period_lock_is_renewed_while_waiting_for_approver
:id: TEST-80
:entrega: DSM3
:status: executado
:verifies: REQ-S02
:derived_from: PROT-LCK

`test_period_lock_is_renewed_while_waiting_for_approver()` — tipo *seguranca*.  
**Resultado esperado:** reserva renovada enquanto o aprovador decide: outro fechamento do mesmo mês é recusado  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_waiver_justification_must_have_content
:id: TEST-81
:entrega: DSM3
:status: executado
:verifies: REQ-S01
:derived_from: NORM-10

`test_waiver_justification_must_have_content()` — tipo *seguranca*.  
**Resultado esperado:** justificativa sem conteúdo (repetição de letras ou palavras) é recusada pela POL-04  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_malformed_dashboard_commands_do_not_kill_the_simulation
:id: TEST-82
:entrega: DSM3
:status: executado
:verifies: REQ-O04, REQ-S04
:derived_from: SVC-AUD

`test_malformed_dashboard_commands_do_not_kill_the_simulation()` — tipo *seguranca*.  
**Resultado esperado:** comandos com tipo errado recebem 400 e nenhum erro derruba a thread da simulação  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_redaction_covers_non_text_secrets_and_brazilian_ids
:id: TEST-83
:entrega: DSM3
:status: executado
:verifies: REQ-P01
:derived_from: NORM-06

`test_redaction_covers_non_text_secrets_and_brazilian_ids()` — tipo *seguranca*.  
**Resultado esperado:** segredo numérico, em lista ou objeto, CPF por campo, CNPJ e telefone são redigidos  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_memory_removal_corruption_or_rollback_fails_closed
:id: TEST-84
:entrega: DSM3
:status: executado
:verifies: REQ-F07, REQ-S01
:derived_from: SVC-MEM

`test_memory_removal_corruption_or_rollback_fails_closed()` — tipo *seguranca*.  
**Resultado esperado:** entrada removida, arquivo corrompido, apagado, versão antiga ou outro formato do arquivo (issue #2): memória comprometida e waiver não reaberto (falha fechada)  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_memory_key_and_counter_live_outside_the_data_folder
:id: TEST-85
:entrega: DSM3
:status: executado
:verifies: REQ-F07, REQ-P01
:derived_from: SVC-MEM

`test_memory_key_and_counter_live_outside_the_data_folder()` — tipo *seguranca*.  
**Resultado esperado:** chave HMAC e contador de versão da memória ficam fora da pasta de dados  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_memory_ids_stay_unique
:id: TEST-86
:entrega: DSM3
:status: executado
:verifies: REQ-F07
:derived_from: SVC-MEM

`test_memory_ids_stay_unique()` — tipo *seguranca*.  
**Resultado esperado:** ids de memória não se repetem quando entradas saem da lista  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_redaction_catches_unmasked_documents_in_free_text
:id: TEST-87
:entrega: DSM3
:status: executado
:verifies: REQ-P01
:derived_from: NORM-06

`test_redaction_catches_unmasked_documents_in_free_text()` — tipo *seguranca*.  
**Resultado esperado:** CPF e CNPJ sem máscara em texto livre são redigidos; valores monetários e contas seguem visíveis  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_trace_anchor_verifies_without_the_authors_key
:id: TEST-88
:entrega: DSM3
:status: executado
:verifies: REQ-O01, REQ-NF01
:derived_from: SVC-AUD

`test_trace_anchor_verifies_without_the_authors_key()` — tipo *seguranca*.  
**Resultado esperado:** âncora pública (hash final reproduzível) verifica o trace em outra máquina; outra chave não é acusada como adulteração  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_decision_that_cannot_be_delivered_in_time_is_rejected
:id: TEST-89
:entrega: DSM3
:status: executado
:verifies: REQ-S01
:derived_from: PROT-APR

`test_decision_that_cannot_be_delivered_in_time_is_rejected()` — tipo *seguranca*.  
**Resultado esperado:** decisão no último tick é recusada explicitamente (POL-08) em vez de aceita e expirada  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_dashboard_authenticates_before_reading_the_body
:id: TEST-90
:entrega: DSM3
:status: executado
:verifies: REQ-O04, REQ-S04
:derived_from: SVC-AUD

`test_dashboard_authenticates_before_reading_the_body()` — tipo *seguranca*.  
**Resultado esperado:** POST sem token com corpo enorme declarado ou token não-ASCII recebe 403 sem ler o corpo nem gerar exceção  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_local_hypothesis_triggers_verification_and_reclassifies
:id: TEST-91
:entrega: DSM3
:status: executado
:verifies: REQ-F08
:derived_from: NORM-11

`test_local_hypothesis_triggers_verification_and_reclassifies()` — tipo *e2e*.  
**Resultado esperado:** a observação vira hipótese, o AG-ORC consulta de novo o AG-CIN e o desvio bate com o gabarito  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_hypothesis_never_writes_a_belief
:id: TEST-92
:entrega: DSM3
:status: executado
:verifies: REQ-F08, REQ-S03
:derived_from: NORM-11

`test_hypothesis_never_writes_a_belief()` — tipo *seguranca*.  
**Resultado esperado:** nenhuma crença tem regra local ou LLM como fonte, em nenhum cenário cognitivo  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_false_alarm_hypothesis_is_refuted_without_extra_messages
:id: TEST-93
:entrega: DSM3
:status: executado
:verifies: REQ-F08
:derived_from: NORM-11

`test_false_alarm_hypothesis_is_refuted_without_extra_messages()` — tipo *e2e*.  
**Resultado esperado:** hipótese refutada pela resposta que o AG-CIN já deu; nenhuma mensagem a mais  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_hypothesis_without_evidence_is_archived_and_changes_nothing
:id: TEST-94
:entrega: DSM3
:status: executado
:verifies: REQ-F08
:derived_from: NORM-11

`test_hypothesis_without_evidence_is_archived_and_changes_nothing()` — tipo *e2e*.  
**Resultado esperado:** sem evidência a hipótese é arquivada e o resultado é igual ao do nível básico  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_calendar_pattern_is_confirmed_by_history_not_by_the_rule
:id: TEST-95
:entrega: DSM3
:status: executado
:verifies: REQ-F08
:derived_from: NORM-11

`test_calendar_pattern_is_confirmed_by_history_not_by_the_rule()` — tipo *e2e*.  
**Resultado esperado:** padrão de calendário confirmado pelo cálculo sobre o histórico; o desvio segue sinalizado, com ressalva  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_epistemic_action_respects_requester_deadline
:id: TEST-96
:entrega: DSM3
:status: executado
:verifies: REQ-F08
:derived_from: PROT-DEL

`test_epistemic_action_respects_requester_deadline()` — tipo *e2e*.  
**Resultado esperado:** a verificação que não cabe no prazo não é feita: o agente negocia ou arquiva e responde no prazo  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_basic_cognition_has_no_hypotheses_and_no_extra_perception
:id: TEST-97
:entrega: DSM3
:status: executado
:verifies: REQ-NF01
:derived_from: NORM-11

`test_basic_cognition_has_no_hypotheses_and_no_extra_perception()` — tipo *reprodutibilidade*.  
**Resultado esperado:** os cenários revisados não ganham registro novo no nível básico  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_llm_hypothesis_is_verified_before_changing_the_outcome
:id: TEST-98
:entrega: DSM3
:status: executado
:verifies: REQ-F08, REQ-S03
:derived_from: NORM-11

`test_llm_hypothesis_is_verified_before_changing_the_outcome()` — tipo *e2e*.  
**Resultado esperado:** proposta do LLM (mock) só muda a avaliação depois de o AG-CIN confirmar  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_rejected_llm_proposals_leave_the_result_identical
:id: TEST-99
:entrega: DSM3
:status: executado
:verifies: REQ-S03
:derived_from: NORM-11

`test_rejected_llm_proposals_leave_the_result_identical()` — tipo *seguranca*.  
**Resultado esperado:** cinco propostas inválidas rejeitadas, cada uma por uma regra; resultado idêntico ao básico  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_injected_note_cannot_change_classification
:id: TEST-100
:entrega: DSM3
:status: executado
:verifies: REQ-S03
:derived_from: NORM-11

`test_injected_note_cannot_change_classification()` — tipo *seguranca*.  
**Resultado esperado:** instrução embutida no texto livre é obedecida pelo modelo e recusada pela validação  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_provider_outage_opens_the_circuit_breaker_and_results_are_deterministic
:id: TEST-101
:entrega: DSM3
:status: executado
:verifies: REQ-C01
:derived_from: SVC-MOD

`test_provider_outage_opens_the_circuit_breaker_and_results_are_deterministic()` — tipo *e2e*.  
**Resultado esperado:** duas falhas do provedor, disjuntor aberto e avaliações iguais às sem LLM  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_external_provider_without_consent_sends_nothing
:id: TEST-102
:entrega: DSM3
:status: executado
:verifies: REQ-P01
:derived_from: NORM-06

`test_external_provider_without_consent_sends_nothing()` — tipo *seguranca*.  
**Resultado esperado:** provedor externo sem consentimento: fallback e nenhum prompt enviado  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_prompt_is_pseudonymized_and_insight_restores_real_names
:id: TEST-103
:entrega: DSM3
:status: executado
:verifies: REQ-P01
:derived_from: NORM-06

`test_prompt_is_pseudonymized_and_insight_restores_real_names()` — tipo *seguranca*.  
**Resultado esperado:** o prompt registrado leva pseudônimos; o insight volta com os nomes reais  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_true_number_under_the_wrong_label_is_rejected
:id: TEST-104
:entrega: DSM3
:status: executado
:verifies: REQ-S03
:derived_from: NORM-05

`test_true_number_under_the_wrong_label_is_rejected()` — tipo *seguranca*.  
**Resultado esperado:** valor verdadeiro sob a grandeza errada ou rótulo adulterado reprova o texto  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_openai_compatible_local_server_feeds_a_verified_hypothesis
:id: TEST-105
:entrega: DSM3
:status: executado
:verifies: REQ-C01
:derived_from: SVC-MOD

`test_openai_compatible_local_server_feeds_a_verified_hypothesis()` — tipo *integracao*.  
**Resultado esperado:** provedor por HTTP em loopback propõe, o agente valida e o AG-CIN confirma  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_openai_provider_sends_key_in_header_and_never_in_the_trace
:id: TEST-106
:entrega: DSM3
:status: executado
:verifies: REQ-P01, REQ-C01
:derived_from: NORM-06

`test_openai_provider_sends_key_in_header_and_never_in_the_trace()` — tipo *integracao*.  
**Resultado esperado:** a chave vai no cabeçalho e não aparece no trace; o corpo sai com pseudônimos  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_anthropic_sdk_request_shape_and_served_model
:id: TEST-107
:entrega: DSM3
:status: executado
:verifies: REQ-C01, REQ-O03
:derived_from: SVC-MOD

`test_anthropic_sdk_request_shape_and_served_model()` — tipo *integracao*.  
**Resultado esperado:** requisição do SDK com saída estruturada e fallback; custo pelo modelo que serviu  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_provider_failures_fall_back_to_the_deterministic_path
:id: TEST-108
:entrega: DSM3
:status: executado
:verifies: REQ-C01
:derived_from: SVC-MOD

`test_provider_failures_fall_back_to_the_deterministic_path()` — tipo *integracao*.  
**Resultado esperado:** 429, 500, resposta inválida, cortada ou recusada caem no fallback, sem vazar segredo  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_cli_benchmark_table_with_mock_and_with_a_local_server
:id: TEST-109
:entrega: DSM3
:status: executado
:verifies: REQ-C01
:derived_from: SVC-MOD

`test_cli_benchmark_table_with_mock_and_with_a_local_server()` — tipo *integracao*.  
**Resultado esperado:** bancada de avaliação de LLM pela linha de comando, com mock e por HTTP  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_involved_approver_is_refused_and_another_person_decides
:id: TEST-110
:entrega: DSM3
:status: executado
:verifies: REQ-S05, REQ-S01
:derived_from: NORM-10

`test_involved_approver_is_refused_and_another_person_decides()` — tipo *e2e*.  
**Resultado esperado:** quem criou o lançamento vetado é recusada (POL-03) e outra pessoa decide  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_requester_cannot_approve_their_own_request
:id: TEST-111
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: NORM-10

`test_requester_cannot_approve_their_own_request()` — tipo *e2e*.  
**Resultado esperado:** quem fez a solicitação é recusada na decisão (POL-13)  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_position_limits_which_decisions_a_person_can_take
:id: TEST-112
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: NORM-10

`test_position_limits_which_decisions_a_person_can_take()` — tipo *e2e*.  
**Resultado esperado:** analista não concede waiver (POL-02); gerente concede  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_single_person_company_uses_the_registered_compensating_control
:id: TEST-113
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: NORM-10

`test_single_person_company_uses_the_registered_compensating_control()` — tipo *e2e*.  
**Resultado esperado:** na microempresa a mesma pessoa pede e decide, com o controle compensatório anotado  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_access_attacks_are_all_rejected_and_nothing_is_published
:id: TEST-114
:entrega: DSM3
:status: executado
:verifies: REQ-S05, REQ-S04
:derived_from: NORM-12

`test_access_attacks_are_all_rejected_and_nothing_is_published()` — tipo *seguranca*.  
**Resultado esperado:** 15 ataques ao controle de acesso rejeitados; nada publicado; nenhum token no trace  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_each_role_can_only_do_what_its_permissions_allow
:id: TEST-115
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: NORM-12

`test_each_role_can_only_do_what_its_permissions_allow()` — tipo *integracao*.  
**Resultado esperado:** matriz papel x comando pelo HTTP: 202 só para quem tem a permissão  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_decision_is_bound_to_the_logged_in_person
:id: TEST-116
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: NORM-13

`test_decision_is_bound_to_the_logged_in_person()` — tipo *integracao*.  
**Resultado esperado:** a decisão pelo dashboard fica no ticket, no trace e na trilha com a pessoa  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_revoked_session_stops_at_once_and_closes_the_event_stream
:id: TEST-117
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: NORM-12

`test_revoked_session_stops_at_once_and_closes_the_event_stream()` — tipo *integracao*.  
**Resultado esperado:** sessão revogada por outro processo: 401 na requisição seguinte e fluxo de eventos encerrado  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_login_lockout_and_generic_errors
:id: TEST-118
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: NORM-12

`test_login_lockout_and_generic_errors()` — tipo *seguranca*.  
**Resultado esperado:** mesma resposta para usuário inexistente e senha errada; cinco erros bloqueiam  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_tampered_account_store_locks_everyone_out
:id: TEST-119
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: NORM-12

`test_tampered_account_store_locks_everyone_out()` — tipo *seguranca*.  
**Resultado esperado:** cadastro alterado fora do sistema: ninguém entra  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_full_account_lifecycle_from_the_terminal
:id: TEST-120
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: SVC-IAM

`test_full_account_lifecycle_from_the_terminal()` — tipo *integracao*.  
**Resultado esperado:** bootstrap, contas, papéis incompatíveis, último administrador, bloqueio e sessões pela CLI  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_access_trail_is_listed_verified_and_tampering_is_detected
:id: TEST-121
:entrega: DSM3
:status: executado
:verifies: REQ-S05, REQ-O01
:derived_from: NORM-13

`test_access_trail_is_listed_verified_and_tampering_is_detected()` — tipo *seguranca*.  
**Resultado esperado:** trilha de acesso íntegra é aprovada; alterada ou truncada é acusada  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_concurrent_writers_do_not_lose_updates
:id: TEST-122
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: SVC-IAM

`test_concurrent_writers_do_not_lose_updates()` — tipo *integracao*.  
**Resultado esperado:** seis processos gravando ao mesmo tempo: nenhuma conta perdida  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_invariant_checker_flags_a_forged_trace
:id: TEST-123
:entrega: DSM3
:status: executado
:verifies: REQ-S04, REQ-O01
:derived_from: SVC-AUD

`test_invariant_checker_flags_a_forged_trace()` — tipo *seguranca*.  
**Resultado esperado:** publicação sobre veto, efeito sem aprovação e crença de modelo são acusados  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_work_area_routes_reports_approvals_explanations_and_sequence
:id: TEST-124
:entrega: DSM3
:status: executado
:verifies: REQ-O04, REQ-O01
:derived_from: SVC-AUD

`test_work_area_routes_reports_approvals_explanations_and_sequence()` — tipo *integracao*.  
**Resultado esperado:** relatórios, aprovações, explicação de decisão e sequência pela API  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_specialist_negotiates_deadline_and_orchestrator_accepts
:id: TEST-125
:entrega: DSM3
:status: executado
:verifies: REQ-F01
:derived_from: PROT-DEL

`test_specialist_negotiates_deadline_and_orchestrator_accepts()` — tipo *protocolo-nominal*.  
**Resultado esperado:** propose e accept-proposal: prazo estendido, hipótese confirmada  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_orchestrator_refuses_extension_when_the_period_is_reserved
:id: TEST-126
:entrega: DSM3
:status: executado
:verifies: REQ-F01, REQ-S02
:derived_from: PROT-DEL

`test_orchestrator_refuses_extension_when_the_period_is_reserved()` — tipo *protocolo-nominal*.  
**Resultado esperado:** reject-proposal no fechamento com período reservado; entrega no prazo original  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_extended_deadline_replaces_the_original_timer
:id: TEST-127
:entrega: DSM3
:status: executado
:verifies: REQ-F01
:derived_from: PROT-DEL

`test_extended_deadline_replaces_the_original_timer()` — tipo *protocolo-nominal*.  
**Resultado esperado:** trabalho além do prazo original, dentro do estendido, não expira  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_protocol_rejects_negotiation_out_of_order_or_by_the_wrong_role
:id: TEST-128
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: PROT-DEL

`test_protocol_rejects_negotiation_out_of_order_or_by_the_wrong_role()` — tipo *protocolo-negativo*.  
**Resultado esperado:** proposta fora de ordem, pelo papel errado ou malformada é rejeitada  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_install_creates_a_ready_data_folder_and_doctor_approves_it
:id: TEST-129
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: SVC-IAM

`test_install_creates_a_ready_data_folder_and_doctor_approves_it()` — tipo *integracao*.  
**Resultado esperado:** instalação numa pasta limpa e diagnóstico sem erros  
**Execução:** DSM3 (status atual: executado).
````

````{test} a decisão é da pessoa: a gerente envolvida é impedida e outro gerente decide
:id: TEST-130
:entrega: DSM3
:status: executado
:verifies: REQ-S05, REQ-O04
:derived_from: NORM-10

`a decisão é da pessoa: a gerente envolvida é impedida e outro gerente decide()` — tipo *interface*.  
**Resultado esperado:** no navegador, a gerente envolvida vê o impedimento e outro gerente decide  
**Execução:** DSM3 (status atual: executado).
````

````{test} sessão revogada pelo administrador no terminal devolve o dashboard ao login
:id: TEST-131
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: NORM-12

`sessão revogada pelo administrador no terminal devolve o dashboard ao login()` — tipo *interface*.  
**Resultado esperado:** revogar pela CLI devolve o navegador à tela de login  
**Execução:** DSM3 (status atual: executado).
````

````{test} logs: filtros por agente e tipo, busca, por quê e sequência da conversa
:id: TEST-132
:entrega: DSM3
:status: executado
:verifies: REQ-O04
:derived_from: SVC-AUD

`logs: filtros por agente e tipo, busca, por quê e sequência da conversa()` — tipo *interface*.  
**Resultado esperado:** filtros, explicação e sequência pela aba Logs  
**Execução:** DSM3 (status atual: executado).
````

````{test} LLM opcional pelo dashboard: ligar o mock no AG-ORC, corroborar a hipótese e ver o custo
:id: TEST-133
:entrega: DSM3
:status: executado
:verifies: REQ-C01, REQ-F08
:derived_from: SVC-MOD

`LLM opcional pelo dashboard: ligar o mock no AG-ORC, corroborar a hipótese e ver o custo()` — tipo *interface*.  
**Resultado esperado:** configurar o LLM pela interface, ver a hipótese corroborada e o uso  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_new_scenarios_hold_every_invariant_and_repeat
:id: TEST-300
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-14

`test_new_scenarios_hold_every_invariant_and_repeat()` — tipo *e2e*.  
**Resultado esperado:** os sete cenários novos repetem o hash e respeitam todos os invariantes  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_person_without_authority_in_the_size_cannot_release
:id: TEST-301
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-14

`test_person_without_authority_in_the_size_cannot_release()` — tipo *e2e*.  
**Resultado esperado:** liberação sem alçada no porte recusada (POL-10); exposição no veto  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_without_iam_the_veto_carries_no_exposure
:id: TEST-302
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-14

`test_without_iam_the_veto_carries_no_exposure()` — tipo *e2e*.  
**Resultado esperado:** sem SVC-IAM o veto e o ticket são os da v0.5.0  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_delegated_decision_records_who_delegated
:id: TEST-303
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-14

`test_delegated_decision_records_who_delegated()` — tipo *e2e*.  
**Resultado esperado:** decisão por delegação aceita e registrada com quem delegou (POL-11)  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_expired_delegation_is_refused_and_the_delegator_decides
:id: TEST-304
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-14

`test_expired_delegation_is_refused_and_the_delegator_decides()` — tipo *e2e*.  
**Resultado esperado:** delegação expirada recusada (POL-11)  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_four_eyes_endorse_then_approve_by_another_person
:id: TEST-305
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-14

`test_four_eyes_endorse_then_approve_by_another_person()` — tipo *e2e*.  
**Resultado esperado:** endorse PENDENTE->PENDENTE e approve de outra pessoa (POL-12)  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_same_person_cannot_endorse_and_approve
:id: TEST-306
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-14

`test_same_person_cannot_endorse_and_approve()` — tipo *e2e*.  
**Resultado esperado:** a mesma pessoa nos dois passos é recusada (POL-12)  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_approval_without_endorsement_is_refused_above_the_limit
:id: TEST-307
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-14

`test_approval_without_endorsement_is_refused_above_the_limit()` — tipo *e2e*.  
**Resultado esperado:** aprovação direta acima do limite recusada (POL-12)  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_ticket_escalates_after_half_the_deadline
:id: TEST-308
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-14

`test_ticket_escalates_after_half_the_deadline()` — tipo *e2e*.  
**Resultado esperado:** nível acima recusado antes; escalonamento registrado na metade do prazo (POL-14)  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_advanced_access_attacks_are_all_rejected
:id: TEST-309
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-15

`test_advanced_access_attacks_are_all_rejected()` — tipo *seguranca*.  
**Resultado esperado:** doze ataques ao acesso avançado, nenhum aceito  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_invariants_catch_a_single_person_release_and_one_above_authority
:id: TEST-310
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-14

`test_invariants_catch_a_single_person_release_and_one_above_authority()` — tipo *seguranca*.  
**Resultado esperado:** INV-09 e INV-10 acusam trace adulterado  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_one_company_memory_is_never_remembered_in_another
:id: TEST-311
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-15

`test_one_company_memory_is_never_remembered_in_another()` — tipo *e2e*.  
**Resultado esperado:** memória de uma empresa não vira reincidência em outra; cópia fica comprometida  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_second_factor_from_the_terminal_with_policy_replay_and_recovery_codes
:id: TEST-312
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-15

`test_second_factor_from_the_terminal_with_policy_replay_and_recovery_codes()` — tipo *integracao*.  
**Resultado esperado:** 2FA pela CLI: política, replay, janela, recuperação de uso único  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_vault_keeps_llm_keys_without_ever_showing_them
:id: TEST-313
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-15

`test_vault_keeps_llm_keys_without_ever_showing_them()` — tipo *integracao*.  
**Resultado esperado:** cofre 0600 fora da pasta de dados, chave de LLM pelo cofre, valor nunca mostrado  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_delegation_policy_and_companies_from_the_terminal
:id: TEST-314
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-14

`test_delegation_policy_and_companies_from_the_terminal()` — tipo *integracao*.  
**Resultado esperado:** delegação, escalonamento e escopo de empresas pela CLI  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_memory_copied_to_another_folder_is_adopted_under_permission
:id: TEST-315
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-15

`test_memory_copied_to_another_folder_is_adopted_under_permission()` — tipo *integracao*.  
**Resultado esperado:** cópia íntegra adotada sob PERM-MEM-ADOTAR; adulterada recusada  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_two_runs_writing_the_same_memory_at_once_keep_both_entries
:id: TEST-316
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-15

`test_two_runs_writing_the_same_memory_at_once_keep_both_entries()` — tipo *integracao*.  
**Resultado esperado:** quatro execuções simultâneas sobre a mesma memória, nenhuma entrada perdida  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_two_step_login_with_short_lived_pre_session
:id: TEST-317
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-15

`test_two_step_login_with_short_lived_pre_session()` — tipo *integracao*.  
**Resultado esperado:** login em dois passos no servidor; pré-sessão só vale em /api/login/2fa  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_policy_requiring_second_factor_only_lets_the_account_enrol
:id: TEST-318
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-15

`test_policy_requiring_second_factor_only_lets_the_account_enrol()` — tipo *integracao*.  
**Resultado esperado:** conta sem o 2FA exigido só consegue ativá-lo  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_vault_routes_store_llm_keys_without_returning_them
:id: TEST-319
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-15

`test_vault_routes_store_llm_keys_without_returning_them()` — tipo *integracao*.  
**Resultado esperado:** rotas do cofre nunca devolvem o valor  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_each_company_gets_its_own_simulation_and_nothing_crosses_over
:id: TEST-320
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-15

`test_each_company_gets_its_own_simulation_and_nothing_crosses_over()` — tipo *integracao*.  
**Resultado esperado:** uma simulação por empresa; seletor /api/empresa; nada cruza  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_enrol_second_factor_then_log_in_with_a_recovery_code
:id: TEST-321
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-15

`test_enrol_second_factor_then_log_in_with_a_recovery_code()` — tipo *interface*.  
**Resultado esperado:** TUI: ativar 2FA, segredo e códigos uma vez, entrada em dois passos  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_approver_creates_and_revokes_a_delegation
:id: TEST-322
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-14

`test_approver_creates_and_revokes_a_delegation()` — tipo *interface*.  
**Resultado esperado:** TUI: criar e revogar delegação  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_administrator_sets_policy_vault_companies_and_sees_authority_limits
:id: TEST-323
:entrega: DSM4
:status: executado
:verifies: REQ-S06
:derived_from: NORM-15

`test_administrator_sets_policy_vault_companies_and_sees_authority_limits()` — tipo *interface*.  
**Resultado esperado:** TUI: política, cofre, empresas e alçadas  
**Execução:** DSM4 (status atual: executado).
````
