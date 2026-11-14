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

````{test} test_deadline_check_uses_the_real_delivery_time_of_the_decision
:id: TEST-134
:entrega: DSM3
:status: executado
:verifies: REQ-S02
:derived_from: SVC-POL

`test_deadline_check_uses_the_real_delivery_time_of_the_decision()` — tipo *seguranca*.  
**Resultado esperado:** decisão que só chegaria depois do prazo do ticket é recusada (POL-08); pelo canal normal, vale  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_first_use_wizard_creates_the_first_administrator
:id: TEST-135
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: SVC-IAM

`test_first_use_wizard_creates_the_first_administrator()` — tipo *interface*.  
**Resultado esperado:** TUI: o primeiro uso cria o administrador e exige senha forte  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_assigning_approver_role_to_the_administrator_is_refused_with_iam06
:id: TEST-136
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: NORM-12

`test_assigning_approver_role_to_the_administrator_is_refused_with_iam06()` — tipo *interface*.  
**Resultado esperado:** TUI: administrador não acumula aprovador (IAM-06)  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_revoking_a_session_opened_by_the_server_drops_it
:id: TEST-137
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: NORM-12

`test_revoking_a_session_opened_by_the_server_drops_it()` — tipo *interface*.  
**Resultado esperado:** TUI: sessão aberta pelo servidor é revogada e deixa de valer  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_access_trail_filters_export_integrity_and_tampering
:id: TEST-138
:entrega: DSM3
:status: executado
:verifies: REQ-S05, REQ-O01
:derived_from: NORM-13

`test_access_trail_filters_export_integrity_and_tampering()` — tipo *interface*.  
**Resultado esperado:** TUI: trilha filtrada, exportada, íntegra aprovada e adulterada acusada  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_open_a_recorded_trace_filter_explain_and_export
:id: TEST-139
:entrega: DSM3
:status: executado
:verifies: REQ-O01, REQ-O04
:derived_from: SVC-AUD

`test_open_a_recorded_trace_filter_explain_and_export()` — tipo *interface*.  
**Resultado esperado:** TUI: abrir trace, filtrar, explicar a decisão e exportar  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_auditor_sees_the_trail_and_cannot_administer
:id: TEST-140
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: NORM-12

`test_auditor_sees_the_trail_and_cannot_administer()` — tipo *interface*.  
**Resultado esperado:** TUI: auditor lê a trilha e não administra  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_unknown_identity_cannot_register_with_a_privileged_role_after_the_system_is_built
:id: TEST-141
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: SVC-A2A

`test_unknown_identity_cannot_register_with_a_privileged_role_after_the_system_is_built()` — tipo *seguranca*.  
**Resultado esperado:** identidade fora do diretório não se registra com o sistema montado; a tentativa é auditada  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_adversarial_model_text_never_becomes_a_hypothesis_nor_reaches_the_report
:id: TEST-142
:entrega: DSM3
:status: executado
:verifies: REQ-F08, REQ-C01
:derived_from: NORM-11

`test_adversarial_model_text_never_becomes_a_hypothesis_nor_reaches_the_report()` — tipo *seguranca*.  
**Resultado esperado:** número por extenso, outra escrita, sinônimo de ação, homógrafo e caractere invisível são rejeitados  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_model_text_in_the_report_is_labelled_unverified_and_values_carry_their_measure
:id: TEST-143
:entrega: DSM3
:status: executado
:verifies: REQ-F08
:derived_from: NORM-11

`test_model_text_in_the_report_is_labelled_unverified_and_values_carry_their_measure()` — tipo *seguranca*.  
**Resultado esperado:** texto de modelo no relatório sai rotulado como não verificado; valor resolvido leva a grandeza  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_synthesis_with_recommendations_falls_back_and_the_model_text_comes_last_and_labelled
:id: TEST-144
:entrega: DSM3
:status: executado
:verifies: REQ-C01
:derived_from: NORM-05

`test_synthesis_with_recommendations_falls_back_and_the_model_text_comes_last_and_labelled()` — tipo *seguranca*.  
**Resultado esperado:** síntese com recomendação cai no template; a redação do modelo vem ao fim, rotulada  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_server_api_key_is_never_sent_to_a_url_chosen_in_the_configuration
:id: TEST-145
:entrega: DSM3
:status: executado
:verifies: REQ-C01, REQ-P01
:derived_from: SVC-MOD

`test_server_api_key_is_never_sent_to_a_url_chosen_in_the_configuration()` — tipo *seguranca*.  
**Resultado esperado:** a chave do servidor só segue para a URL do provedor ou para a lista da instalação  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_counterpart_cannot_extend_its_own_deadline_without_negotiating
:id: TEST-146
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: PROT-DEL

`test_counterpart_cannot_extend_its_own_deadline_without_negotiating()` — tipo *protocolo-negativo*.  
**Resultado esperado:** só o iniciador define o prazo da conversa; o especialista não o estende sozinho  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_malformed_nested_payload_from_a_specialist_becomes_an_explicit_failure
:id: TEST-147
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: PROT-DEL

`test_malformed_nested_payload_from_a_specialist_becomes_an_explicit_failure()` — tipo *robustez*.  
**Resultado esperado:** conteúdo aninhado inválido vira failure ao solicitante e libera o período  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_malformed_bodies_get_a_400_instead_of_a_dropped_connection
:id: TEST-148
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: SVC-IAM

`test_malformed_bodies_get_a_400_instead_of_a_dropped_connection()` — tipo *robustez*.  
**Resultado esperado:** corpo que não é objeto ou campo de tipo errado recebe 400, com ou sem sessão  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_wrong_passwords_by_a_stranger_do_not_drop_the_live_session_of_the_account
:id: TEST-149
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: NORM-12

`test_wrong_passwords_by_a_stranger_do_not_drop_the_live_session_of_the_account()` — tipo *seguranca*.  
**Resultado esperado:** bloqueio por tentativas não derruba a sessão viva da pessoa  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_period_reservation_cannot_be_released_or_taken_by_naming_its_owner
:id: TEST-150
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: PROT-LCK

`test_period_reservation_cannot_be_released_or_taken_by_naming_its_owner()` — tipo *seguranca*.  
**Resultado esperado:** reserva de período só muda com a credencial do Orquestrador  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_invariant_checker_has_no_false_alarm_on_resend_and_catches_what_it_missed
:id: TEST-151
:entrega: DSM3
:status: executado
:verifies: REQ-O01
:derived_from: SVC-AUD

`test_invariant_checker_has_no_false_alarm_on_resend_and_catches_what_it_missed()` — tipo *seguranca*.  
**Resultado esperado:** sem falso alarme no reenvio do parecer; acusa fechamento sem parecer e correção repetida  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_unhashable_or_uncopiable_input_is_rejected_and_audited_not_raised
:id: TEST-152
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: SVC-A2A

`test_unhashable_or_uncopiable_input_is_rejected_and_audited_not_raised()` — tipo *robustez*.  
**Resultado esperado:** identificador não textual e conteúdo não copiável são rejeitados com registro  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_changing_the_cognition_level_on_restart_needs_the_model_permission
:id: TEST-153
:entrega: DSM3
:status: executado
:verifies: REQ-S05
:derived_from: SVC-IAM

`test_changing_the_cognition_level_on_restart_needs_the_model_permission()` — tipo *seguranca*.  
**Resultado esperado:** mudar a cognição no reinício exige a permissão de modelos; agente desconhecido é recusado  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_message_lost_after_the_opening_never_leaves_the_requester_without_an_answer
:id: TEST-154
:entrega: DSM3
:status: executado
:verifies: REQ-S04
:derived_from: SVC-A2A

`test_message_lost_after_the_opening_never_leaves_the_requester_without_an_answer()` — tipo *robustez*.  
**Resultado esperado:** resposta final ou mensagem do meio perdida na entrega: o iniciador é avisado, reenvia uma vez ou falha de forma explícita  
**Execução:** DSM3 (status atual: executado).
````

````{test} test_new_scenarios_deliberate_and_keep_beliefs_with_deterministic_sources
:id: TEST-201
:entrega: DSM4
:status: executado
:verifies: REQ-F20
:derived_from: NORM-11

`test_new_scenarios_deliberate_and_keep_beliefs_with_deterministic_sources()` — tipo *e2e*.  
**Resultado esperado:** nos onze cenários novos há deliberação com plano aplicável e não aplicável e toda crença tem fonte determinística  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_basic_level_runs_the_same_scenario_with_the_reactive_specialists
:id: TEST-202
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-NF01
:derived_from: ROLE-RES

`test_basic_level_runs_the_same_scenario_with_the_reactive_specialists()` — tipo *reprodutibilidade*.  
**Resultado esperado:** no nível básico os mesmos cenários rodam com as classes reativas, sem registro BDI de RES, CUS e REL  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_build_system_picks_the_variant_by_cognition_level
:id: TEST-203
:entrega: DSM4
:status: executado
:verifies: REQ-F20
:derived_from: ROLE-RES

`test_build_system_picks_the_variant_by_cognition_level()` — tipo *e2e*.  
**Resultado esperado:** variante BDI nos níveis local e llm; classe reativa no básico; estratégia de compromisso inválida é recusada  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_results_agent_explains_a_relevant_variation_with_verified_evidence
:id: TEST-204
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-F04
:derived_from: PROT-QRY

`test_results_agent_explains_a_relevant_variation_with_verified_evidence()` — tipo *e2e*.  
**Resultado esperado:** variação do EBITDA% vira hipótese, o AG-RES pede o detalhe ao AG-CUS e a explicação aponta o centro do gabarito  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_variation_hypothesis_falls_back_to_history_when_the_cost_agent_goes_offline
:id: TEST-205
:entrega: DSM4
:status: executado
:verifies: REQ-F20
:derived_from: PROT-QRY

`test_variation_hypothesis_falls_back_to_history_when_the_cost_agent_goes_offline()` — tipo *e2e*.  
**Resultado esperado:** plano de detalhe falha por timeout e o AG-RES replaneja para a conferência no histórico  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_results_agent_replans_when_a_specialist_is_silent_and_decides_by_size_and_criticality
:id: TEST-206
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-F04
:derived_from: PROT-QRY

`test_results_agent_replans_when_a_specialist_is_silent_and_decides_by_size_and_criticality()` — tipo *e2e*.  
**Resultado esperado:** duas consultas perdidas: média consolida com ressalva, grande falha explicitamente, básico aborta o fechamento  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_missing_critical_input_never_becomes_a_partial_result
:id: TEST-207
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-F04
:derived_from: ROLE-RES

`test_missing_critical_input_never_becomes_a_partial_result()` — tipo *e2e*.  
**Resultado esperado:** sem custos não há DRE parcial em nenhum porte: falha explícita  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_cost_agent_picks_an_allocation_criterion_when_the_driver_is_unusable
:id: TEST-208
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-F02
:derived_from: ROLE-CUS

`test_cost_agent_picks_an_allocation_criterion_when_the_driver_is_unusable()` — tipo *e2e*.  
**Resultado esperado:** direcionador inconsistente: plano padrão falha, critério proporcional à receita escolhido, conta igual ao gabarito, motivo registrado  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_cost_criterion_depends_on_company_size_and_on_what_is_wrong_with_the_driver
:id: TEST-209
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-F02
:derived_from: ROLE-CUS

`test_cost_criterion_depends_on_company_size_and_on_what_is_wrong_with_the_driver()` — tipo *e2e*.  
**Resultado esperado:** microempresa divide em partes iguais; tabela ausente reusa a última aprovada; sem problema, critério padrão  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_report_agent_chooses_structure_by_findings_and_audience
:id: TEST-210
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-F06
:derived_from: ROLE-REL

`test_report_agent_chooses_structure_by_findings_and_audience()` — tipo *e2e*.  
**Resultado esperado:** relatório de exceção com veto corrigido, sumário quando conforme, relatório completo para conselho e auditoria  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_exception_report_orders_caveats_and_keeps_only_verified_insights
:id: TEST-211
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-F06
:derived_from: ROLE-REL

`test_exception_report_orders_caveats_and_keeps_only_verified_insights()` — tipo *e2e*.  
**Resultado esperado:** waiver primeiro nas ressalvas; hipótese arquivada não é reproduzida, só contada  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_model_text_goes_to_the_end_of_the_report_labelled_and_never_inside_template_sentences
:id: TEST-212
:entrega: DSM4
:status: executado
:verifies: REQ-S03, REQ-F06
:derived_from: NORM-05

`test_model_text_goes_to_the_end_of_the_report_labelled_and_never_inside_template_sentences()` — tipo *seguranca*.  
**Resultado esperado:** texto de modelo ao fim do relatório, rotulado; corpo igual ao do template; AG-CUS recusa LLM  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_deliberation_and_grounding_metrics_are_read_from_the_trace
:id: TEST-213
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-F21
:derived_from: SVC-AUD

`test_deliberation_and_grounding_metrics_are_read_from_the_trace()` — tipo *observabilidade*.  
**Resultado esperado:** MET-30 e MET-31 calculadas só do trace: replanejamentos, insistências, crenças sem fonte, citações incompletas  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_rule_confidence_follows_refutations_and_changes_what_the_agent_does
:id: TEST-214
:entrega: DSM4
:status: executado
:verifies: REQ-F20
:derived_from: NORM-20

`test_rule_confidence_follows_refutations_and_changes_what_the_agent_does()` — tipo *e2e*.  
**Resultado esperado:** duas refutações levam a confiança de 0,80 a 0,40 e a hipótese deixa de justificar nova consulta  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_rule_confidence_rises_with_confirmations
:id: TEST-215
:entrega: DSM4
:status: executado
:verifies: REQ-F20
:derived_from: NORM-20

`test_rule_confidence_rises_with_confirmations()` — tipo *e2e*.  
**Resultado esperado:** confirmações em meses seguidos elevam a confiança de 0,80 a 0,87 e 0,90  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_only_verified_evidence_counts_for_learning
:id: TEST-216
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-S03
:derived_from: NORM-20

`test_only_verified_evidence_counts_for_learning()` — tipo *seguranca*.  
**Resultado esperado:** hipótese arquivada, origem LLM e observação sem fonte determinística não contam  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_results_agent_rules_learn_too
:id: TEST-217
:entrega: DSM4
:status: executado
:verifies: REQ-F20
:derived_from: NORM-20

`test_results_agent_rules_learn_too()` — tipo *e2e*.  
**Resultado esperado:** a regra de custo fixo do AG-RES registra a confirmação com a fonte da evidência  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_three_commitment_strategies_differ_on_the_same_situation
:id: TEST-218
:entrega: DSM4
:status: executado
:verifies: REQ-F20
:derived_from: ROLE-ORC

`test_three_commitment_strategies_differ_on_the_same_situation()` — tipo *e2e*.  
**Resultado esperado:** aberto replaneja e abandona o alerta (gabarito); obstinado mantém o alerta; cego insiste no plano; três traces distintos  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_open_commitment_is_the_default_and_reproduces_previous_behaviour
:id: TEST-219
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-NF01
:derived_from: ROLE-ORC

`test_open_commitment_is_the_default_and_reproduces_previous_behaviour()` — tipo *reprodutibilidade*.  
**Resultado esperado:** compromisso aberto explícito produz o mesmo trace, byte a byte, dos cenários existentes  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_blind_commitment_stops_insisting_at_the_cap_and_costs_the_deadline
:id: TEST-220
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-F01
:derived_from: PROT-DEL

`test_blind_commitment_stops_insisting_at_the_cap_and_costs_the_deadline()` — tipo *e2e*.  
**Resultado esperado:** falha permanente: o cego insiste duas vezes, estoura o prazo e a solicitação falha; o aberto entrega com ressalva  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_commitment_applies_to_the_new_bdi_specialists
:id: TEST-221
:entrega: DSM4
:status: executado
:verifies: REQ-F20
:derived_from: ROLE-CUS

`test_commitment_applies_to_the_new_bdi_specialists()` — tipo *e2e*.  
**Resultado esperado:** AG-CUS cego relê o direcionador inconsistente duas vezes antes de trocar de critério  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_budget_agent_reads_approved_memory_and_avoids_a_false_deviation
:id: TEST-222
:entrega: DSM4
:status: executado
:verifies: REQ-F07, REQ-F20
:derived_from: NORM-08

`test_budget_agent_reads_approved_memory_and_avoids_a_false_deviation()` — tipo *e2e*.  
**Resultado esperado:** correção aprovada em agosto vira hipótese de reincidência em setembro, o AG-CIN confirma e o falso desvio some  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_memory_corroboration_raises_the_confidence_of_an_existing_hypothesis
:id: TEST-223
:entrega: DSM4
:status: executado
:verifies: REQ-F07, REQ-F20
:derived_from: NORM-11

`test_memory_corroboration_raises_the_confidence_of_an_existing_hypothesis()` — tipo *e2e*.  
**Resultado esperado:** observação e memória apontam a mesma causa: hipótese corroborada, com confiança maior  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_memory_read_access_is_by_type_and_denials_are_audited
:id: TEST-224
:entrega: DSM4
:status: executado
:verifies: REQ-F07, REQ-S04
:derived_from: SVC-MEM

`test_memory_read_access_is_by_type_and_denials_are_audited()` — tipo *seguranca*.  
**Resultado esperado:** correção legível por ORC, RES e REL; waiver e bloqueio só pelo AG-CIN; leitura negada fica no trace  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_report_and_results_agents_cite_previous_approved_corrections
:id: TEST-225
:entrega: DSM4
:status: executado
:verifies: REQ-F07
:derived_from: NORM-08

`test_report_and_results_agents_cite_previous_approved_corrections()` — tipo *e2e*.  
**Resultado esperado:** o relatório de exceção e a explicação do AG-RES citam a correção anterior com o id da memória  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_search_returns_the_expected_passage_first_with_provenance
:id: TEST-226
:entrega: DSM4
:status: executado
:verifies: REQ-F21
:derived_from: NORM-21

`test_search_returns_the_expected_passage_first_with_provenance()` — tipo *e2e*.  
**Resultado esperado:** top-k esperado para oito consultas de referência, com documento, trecho e versão  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_search_without_evidence_returns_nothing
:id: TEST-227
:entrega: DSM4
:status: executado
:verifies: REQ-F21, REQ-S01
:derived_from: NORM-21

`test_search_without_evidence_returns_nothing()` — tipo *seguranca*.  
**Resultado esperado:** assunto fora do corpus devolve lista vazia; a tool é negada fora da allowlist  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_finding_cites_the_passage_that_grounds_it
:id: TEST-228
:entrega: DSM4
:status: executado
:verifies: REQ-F21, REQ-F05
:derived_from: NORM-21

`test_finding_cites_the_passage_that_grounds_it()` — tipo *e2e*.  
**Resultado esperado:** achado de SoD cita COSO-SEGREGACAO com a versão do corpus; no básico não há busca nem campo novo  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_no_evidence_is_declared_and_never_filled
:id: TEST-229
:entrega: DSM4
:status: executado
:verifies: REQ-F21, REQ-F05
:derived_from: NORM-21

`test_no_evidence_is_declared_and_never_filled()` — tipo *seguranca*.  
**Resultado esperado:** duplicidade sai marcada sem evidência, sem documento nem trecho; o veto segue pela regra interna  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_cli_checks_every_new_scenario_against_the_invariants
:id: TEST-230
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-O01
:derived_from: SVC-AUD

`test_cli_checks_every_new_scenario_against_the_invariants()` — tipo *integracao*.  
**Resultado esperado:** cenarios --verificar aprova os cenários novos: resposta explícita, invariantes e repetição  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_cli_shows_deliberation_of_the_new_bdi_specialists
:id: TEST-231
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-O01
:derived_from: SVC-AUD

`test_cli_shows_deliberation_of_the_new_bdi_specialists()` — tipo *integracao*.  
**Resultado esperado:** a trilha no terminal mostra deliberação, falha de plano, hipótese e compromisso por parâmetro  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_cli_searches_the_normative_base_and_reports_missing_evidence
:id: TEST-232
:entrega: DSM4
:status: executado
:verifies: REQ-F21
:derived_from: NORM-21

`test_cli_searches_the_normative_base_and_reports_missing_evidence()` — tipo *integracao*.  
**Resultado esperado:** fin-mas normas devolve o trecho com proveniência e sai com código 1 quando não há evidência  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_learning_persists_between_runs_in_a_sealed_file
:id: TEST-233
:entrega: DSM4
:status: executado
:verifies: REQ-F20
:derived_from: NORM-20

`test_learning_persists_between_runs_in_a_sealed_file()` — tipo *integracao*.  
**Resultado esperado:** arquivo selado guarda a observação; a execução seguinte usa a confiança aprendida; reprocessar não conta duas vezes  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_tampered_learning_file_fails_closed
:id: TEST-234
:entrega: DSM4
:status: executado
:verifies: REQ-F20, REQ-S04
:derived_from: NORM-20

`test_tampered_learning_file_fails_closed()` — tipo *seguranca*.  
**Resultado esperado:** arquivo adulterado desliga o aprendizado, as regras voltam à confiança inicial e nada é gravado  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_equivalent_workflow_matches_the_mas_on_the_comparable_scenarios
:id: TEST-235
:entrega: DSM4
:status: executado
:verifies: REQ-F03, REQ-F05, REQ-S01
:derived_from: SVC-POL

`test_equivalent_workflow_matches_the_mas_on_the_comparable_scenarios()` — tipo *e2e*.  
**Resultado esperado:** sem falhas, workflow equivalente e SMA básico dão o mesmo status, DRE, classificação, correções e decisões nos 11 cenários comparáveis  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_equivalent_workflow_matches_the_mas_on_drawn_workloads
:id: TEST-236
:entrega: DSM4
:status: executado
:verifies: REQ-F03, REQ-F05
:derived_from: SVC-POL

`test_equivalent_workflow_matches_the_mas_on_drawn_workloads()` — tipo *e2e*.  
**Resultado esperado:** a mesma igualdade nas cargas sorteadas do experimento, nos quatro portes e nas duas intenções  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_equivalent_workflow_has_one_controller_and_only_approval_messages
:id: TEST-237
:entrega: DSM4
:status: executado
:verifies: REQ-S01
:derived_from: PROT-APR

`test_equivalent_workflow_has_one_controller_and_only_approval_messages()` — tipo *e2e*.  
**Resultado esperado:** um só componente decide; as únicas mensagens são as do Approval Gate; correção só com aprovação  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_equivalence_stops_where_messages_can_be_lost_and_the_minimal_workflow_never_was_equivalent
:id: TEST-238
:entrega: DSM4
:status: executado
:verifies: REQ-F01, REQ-F05
:derived_from: PROT-DEL

`test_equivalence_stops_where_messages_can_be_lost_and_the_minimal_workflow_never_was_equivalent()` — tipo *e2e*.  
**Resultado esperado:** com perda de mensagens o SMA falha e o workflow publica; o workflow mínimo publica a crítica que os outros vetam  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_chaos_and_parameters_change_nothing_by_default
:id: TEST-239
:entrega: DSM4
:status: executado
:verifies: REQ-NF01
:derived_from: SVC-A2A

`test_chaos_and_parameters_change_nothing_by_default()` — tipo *e2e*.  
**Resultado esperado:** sem modelo de falhas e com os parâmetros padrão, o hash do trace é o de sempre  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_same_seed_repeats_the_run_and_each_factor_has_its_own_draw
:id: TEST-240
:entrega: DSM4
:status: executado
:verifies: REQ-NF01
:derived_from: SVC-A2A

`test_same_seed_repeats_the_run_and_each_factor_has_its_own_draw()` — tipo *e2e*.  
**Resultado esperado:** mesma seed, mesmo trace; ligar uma falha não muda plantios, perfil do aprovador nem os dados  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_random_loss_and_outages_reach_the_bus_and_every_silence_is_flagged
:id: TEST-241
:entrega: DSM4
:status: executado
:verifies: REQ-F01, REQ-O01
:derived_from: SVC-A2A

`test_random_loss_and_outages_reach_the_bus_and_every_silence_is_flagged()` — tipo *e2e*.  
**Resultado esperado:** perdas e indisponibilidades chegam ao barramento; solicitação sem resposta é acusada pelo INV-07  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_slow_or_absent_approver_lets_the_ticket_expire_and_nothing_is_published
:id: TEST-242
:entrega: DSM4
:status: executado
:verifies: REQ-S01, REQ-F05
:derived_from: PROT-APR

`test_slow_or_absent_approver_lets_the_ticket_expire_and_nothing_is_published()` — tipo *e2e*.  
**Resultado esperado:** aprovador lento ou ausente: o ticket expira, a publicação fica bloqueada e nenhuma crítica sai  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_attacks_during_combined_failures_are_all_rejected
:id: TEST-243
:entrega: DSM4
:status: executado
:verifies: REQ-S04
:derived_from: PROT-APR

`test_attacks_during_combined_failures_are_all_rejected()` — tipo *seguranca*.  
**Resultado esperado:** ataques ao Approval Gate sob perda, atraso, indisponibilidade e humano lento: nenhum aceito  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_injected_parameters_change_the_coordination_they_control
:id: TEST-244
:entrega: DSM4
:status: executado
:verifies: REQ-F01, REQ-S02, REQ-NF02
:derived_from: PROT-DEL

`test_injected_parameters_change_the_coordination_they_control()` — tipo *e2e*.  
**Resultado esperado:** tentativas, correções, extensão de prazo, reserva, prazos e limiar mudam o comportamento e ficam no trace  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_quick_experiment_writes_every_output_and_repeats_byte_for_byte
:id: TEST-245
:entrega: DSM4
:status: executado
:verifies: REQ-NF01
:derived_from: SVC-AUD

`test_quick_experiment_writes_every_output_and_repeats_byte_for_byte()` — tipo *integracao*.  
**Resultado esperado:** o comando do experimento grava os 12 arquivos e os reproduzíveis saem idênticos numa segunda execução  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_pipeline_statistics_match_hand_computed_references
:id: TEST-246
:entrega: DSM4
:status: executado
:verifies: REQ-NF01
:derived_from: SVC-AUD

`test_pipeline_statistics_match_hand_computed_references()` — tipo *integracao*.  
**Resultado esperado:** Wilcoxon, Mann-Whitney, Cliff, Holm e descritivas gravados pelo pipeline batem com valores calculados à mão  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_summary_and_tests_are_recomputed_from_the_raw_rows
:id: TEST-247
:entrega: DSM4
:status: executado
:verifies: REQ-NF01, REQ-O01
:derived_from: SVC-AUD

`test_summary_and_tests_are_recomputed_from_the_raw_rows()` — tipo *integracao*.  
**Resultado esperado:** a análise refeita só com o execucoes.csv dá o mesmo resumo e os mesmos testes  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_legal_bands_follow_lc123_and_bndes
:id: TEST-170
:entrega: DSM4
:status: executado
:verifies: REQ-F05, REQ-F03
:derived_from: NORM-04

`test_legal_bands_follow_lc123_and_bndes()` — tipo *cenario*.  
**Resultado esperado:** faixas legais: MEI só por opção (LC 123/2006, art. 18-A), ME, EPP, Média I e II e grande (BNDES); os quatro portes de antes inalterados  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_mei_runs_alone_without_erp_and_with_compensating_control
:id: TEST-171
:entrega: DSM4
:status: executado
:verifies: REQ-F05, REQ-F03
:derived_from: NORM-04

`test_mei_runs_alone_without_erp_and_with_compensating_control()` — tipo *cenario*.  
**Resultado esperado:** MEI com uma pessoa e sem ERP: SoD impossível vira controle compensatório, duplicidade vetada e estornada, plantio de alçada recusado  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_media_ii_applies_the_upper_band_rules
:id: TEST-172
:entrega: DSM4
:status: executado
:verifies: REQ-F05, REQ-F03
:derived_from: NORM-04

`test_media_ii_applies_the_upper_band_rules()` — tipo *cenario*.  
**Resultado esperado:** Média empresa II: receita na faixa de R$ 90 a 300 milhões, materialidade e pesos do porte, alçada reaprovada e publicação  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_segment_changes_accounts_costs_and_allocation_driver
:id: TEST-173
:entrega: DSM4
:status: executado
:verifies: REQ-F02, REQ-F04
:derived_from: SVC-MCP

`test_segment_changes_accounts_costs_and_allocation_driver()` — tipo *cenario*.  
**Resultado esperado:** comércio, serviços e indústria: plano de contas, unidades e centros do segmento; AG-CUS rateia pelo direcionador e o resultado por UN confere com o gabarito  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_segment_cost_structure_is_consistent
:id: TEST-174
:entrega: DSM4
:status: executado
:verifies: REQ-F02
:derived_from: SVC-MCP

`test_segment_cost_structure_is_consistent()` — tipo *cenario*.  
**Resultado esperado:** CMV pelo estoque no comércio, horas de mão de obra direta em serviços, custo de produção e rateio dos CIF na indústria  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_default_segment_keeps_the_dsm3_data_and_trace
:id: TEST-175
:entrega: DSM4
:status: executado
:verifies: REQ-NF01
:derived_from: SVC-AUD

`test_default_segment_keeps_the_dsm3_data_and_trace()` — tipo *regressao*.  
**Resultado esperado:** segmento padrão gera os mesmos dados e o mesmo hash de trace da DSM3; o meta só ganha segmento fora do padrão  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_backup_restores_into_another_folder_on_another_machine
:id: TEST-176
:entrega: DSM4
:status: executado
:verifies: REQ-S05, REQ-NF01
:derived_from: SVC-IAM

`test_backup_restores_into_another_folder_on_another_machine()` — tipo *integracao*.  
**Resultado esperado:** backup com manifesto selado e chaves em arquivo separado; restauração em outra pasta e outra pasta de chaves com selos, trilha e memória conferidos  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_tampered_or_mismatched_backup_is_refused
:id: TEST-177
:entrega: DSM4
:status: executado
:verifies: REQ-S05, REQ-S04
:derived_from: SVC-IAM

`test_tampered_or_mismatched_backup_is_refused()` — tipo *seguranca*.  
**Resultado esperado:** arquivo trocado, hash corrigido, manifesto re-selado, fuga de diretório, arquivo a mais, chaves de outra instalação e rollback: recusados sem gravar nada  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_migration_mechanism_with_an_example_from_version_1_to_2
:id: TEST-178
:entrega: DSM4
:status: executado
:verifies: REQ-NF02, REQ-S05
:derived_from: SVC-IAM

`test_migration_mechanism_with_an_example_from_version_1_to_2()` — tipo *integracao*.  
**Resultado esperado:** migrar confere o selo na versão de origem, aplica a migração de exemplo 1->2 e grava selado; o sistema na versão 1 recusa o arquivo migrado  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_server_on_all_interfaces_still_accepts_only_loopback_names
:id: TEST-179
:entrega: DSM4
:status: executado
:verifies: REQ-O04, REQ-S05
:derived_from: NORM-12

`test_server_on_all_interfaces_still_accepts_only_loopback_names()` — tipo *seguranca*.  
**Resultado esperado:** serve --host 0.0.0.0 (contêiner) continua recusando Host e Origin que não sejam de loopback  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_dashboard_api_lists_sizes_segments_templates_and_restarts_with_a_segment
:id: TEST-180
:entrega: DSM4
:status: executado
:verifies: REQ-O04
:derived_from: SVC-AUD

`test_dashboard_api_lists_sizes_segments_templates_and_restarts_with_a_segment()` — tipo *integracao*.  
**Resultado esperado:** /api/portes com segmentos, /api/modelos com os portes novos e os segmentos, reiniciar com segmento e segmento desconhecido recusado  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_wheel_installs_in_a_clean_venv_and_runs_outside_the_repository
:id: TEST-181
:entrega: DSM4
:status: executado
:verifies: REQ-NF01
:derived_from: SVC-AUD

`test_wheel_installs_in_a_clean_venv_and_runs_outside_the_repository()` — tipo *integracao*.  
**Resultado esperado:** wheel com YAML e dashboard embutidos instalado num venv limpo: list, run (mesmo hash do checkout), instalar --demo e doctor fora do repositório  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_container_files_publish_only_on_loopback_and_keep_keys_apart
:id: TEST-182
:entrega: DSM4
:status: executado
:verifies: REQ-S05
:derived_from: SVC-IAM

`test_container_files_publish_only_on_loopback_and_keep_keys_apart()` — tipo *configuracao*.  
**Resultado esperado:** compose publica só em 127.0.0.1, volumes de dados e chaves separados, usuário sem privilégio, healthcheck em /api/saude  
**Execução:** DSM4 (status atual: executado).
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

````{test} test_understanding_openapi_samples_spreadsheet_and_mcp_match_the_answer_key
:id: TEST-250
:entrega: DSM4
:status: executado
:verifies: REQ-F30
:derived_from: NORM-30

`test_understanding_openapi_samples_spreadsheet_and_mcp_match_the_answer_key()` — tipo *integracao*.  
**Resultado esperado:** OpenAPI, amostras JSON, planilha fora do modelo e tools MCP: sugestões iguais ao gabarito, com confiança e motivo  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_quality_report_flags_missing_duplicates_out_of_period_totals_and_negatives
:id: TEST-251
:entrega: DSM4
:status: executado
:verifies: REQ-F30
:derived_from: NORM-06

`test_quality_report_flags_missing_duplicates_out_of_period_totals_and_negatives()` — tipo *integracao*.  
**Resultado esperado:** faltantes, duplicados, fora da competência, total que não fecha e negativos acusados; prévia redigida  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_rest_demo_closes_the_month_like_the_simulated_erp_and_writes_only_with_approval
:id: TEST-252
:entrega: DSM4
:status: executado
:verifies: REQ-F30, REQ-S20
:derived_from: PROT-APR

`test_rest_demo_closes_the_month_like_the_simulated_erp_and_writes_only_with_approval()` — tipo *integracao*.  
**Resultado esperado:** fechamento sobre o ERP de demonstração igual ao ERP simulado; correção só com ticket aprovado  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_source_down_fails_explicitly_and_does_not_hang
:id: TEST-253
:entrega: DSM4
:status: executado
:verifies: REQ-F30
:derived_from: SVC-MCP

`test_source_down_fails_explicitly_and_does_not_hang()` — tipo *integracao*.  
**Resultado esperado:** failure com o motivo, leituras negadas auditadas, nada publicado, em segundos  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_rest_connector_errors_401_500_timeout_invalid_json_and_redirect_are_redacted
:id: TEST-254
:entrega: DSM4
:status: executado
:verifies: REQ-S20
:derived_from: NORM-32

`test_rest_connector_errors_401_500_timeout_invalid_json_and_redirect_are_redacted()` — tipo *seguranca*.  
**Resultado esperado:** erros tipados e redigidos; redirecionamento não seguido; credencial não vai a outro host  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_external_host_is_denied_without_admin_release
:id: TEST-255
:entrega: DSM4
:status: executado
:verifies: REQ-S20
:derived_from: NORM-32

`test_external_host_is_denied_without_admin_release()` — tipo *seguranca*.  
**Resultado esperado:** host externo recusado antes de qualquer conexão; liberado, só o ambiente offline bloqueia  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_simulated_connector_and_spreadsheet_folder_preserve_the_current_behavior
:id: TEST-256
:entrega: DSM4
:status: executado
:verifies: REQ-F30
:derived_from: SVC-MCP

`test_simulated_connector_and_spreadsheet_folder_preserve_the_current_behavior()` — tipo *integracao*.  
**Resultado esperado:** ERP simulado por conector com o mesmo trace; pasta com uma planilha igual a --pasta; várias competências  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_spreadsheet_off_model_and_mcp_scenarios_match_the_canonical_reading
:id: TEST-257
:entrega: DSM4
:status: executado
:verifies: REQ-F30
:derived_from: NORM-30

`test_spreadsheet_off_model_and_mcp_scenarios_match_the_canonical_reading()` — tipo *e2e*.  
**Resultado esperado:** planilha_fora_do_modelo e mcp_tools_entendidas iguais à leitura canônica e repetíveis  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_mcp_client_talks_to_the_excel_server_over_stdio
:id: TEST-258
:entrega: DSM4
:status: executado
:verifies: REQ-F30
:derived_from: SVC-MCP

`test_mcp_client_talks_to_the_excel_server_over_stdio()` — tipo *integracao*.  
**Resultado esperado:** initialize, tools/list, tools/call e erro de tool contra o servidor embutido  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_optional_llm_only_suggests_and_goes_through_the_same_validation
:id: TEST-259
:entrega: DSM4
:status: executado
:verifies: REQ-F30
:derived_from: NORM-31

`test_optional_llm_only_suggests_and_goes_through_the_same_validation()` — tipo *integracao*.  
**Resultado esperado:** LLM só sugere pendentes, envia só nomes e tipos; inválidas rejeitadas; externo sem consentimento não envia  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_cli_understands_tests_and_serves_the_demo_erp
:id: TEST-260
:entrega: DSM4
:status: executado
:verifies: REQ-F30, REQ-S20
:derived_from: SVC-MCP

`test_cli_understands_tests_and_serves_the_demo_erp()` — tipo *integracao*.  
**Resultado esperado:** fontes entender, fontes testar e erp-demo pela CLI; token fora da saída  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_sources_flow_register_test_understand_adjust_confirm_activate_and_close
:id: TEST-261
:entrega: DSM4
:status: executado
:verifies: REQ-F30, REQ-S20
:derived_from: NORM-30

`test_sources_flow_register_test_understand_adjust_confirm_activate_and_close()` — tipo *integracao*.  
**Resultado esperado:** cadastro, teste, entendimento, ajuste, confirmação e ativação pelo HTTP; token fora de resposta, trace, trilha e cofre  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_sources_permissions_external_host_and_body_validation
:id: TEST-262
:entrega: DSM4
:status: executado
:verifies: REQ-S20
:derived_from: NORM-32

`test_sources_permissions_external_host_and_body_validation()` — tipo *seguranca*.  
**Resultado esperado:** 403 sem permissão, 400 para corpo não objeto, host externo só pelo administrador, credencial desvinculada  
**Execução:** DSM4 (status atual: executado).
````

````{test} test_spreadsheet_uploads_history_and_off_model_activation
:id: TEST-263
:entrega: DSM4
:status: executado
:verifies: REQ-F30
:derived_from: SVC-IAM

`test_spreadsheet_uploads_history_and_off_model_activation()` — tipo *integracao*.  
**Resultado esperado:** envio no modelo e fora dele, histórico, planilha fora do modelo entendida, confirmada e ativada  
**Execução:** DSM4 (status atual: executado).
````

````{test} fontes: cadastrar o ERP, testar, entender, ajustar, confirmar, ativar e fechar o mês sobre ele
:id: TEST-264
:entrega: DSM4
:status: executado
:verifies: REQ-F30, REQ-S20
:derived_from: NORM-30

`fontes: cadastrar o ERP, testar, entender, ajustar, confirmar, ativar e fechar o mês sobre ele()` — tipo *interface*.  
**Resultado esperado:** no navegador: aba Fontes de ponta a ponta; o token nunca aparece  
**Execução:** DSM4 (status atual: executado).
````

````{test} fontes: modelos para baixar, envio de planilha e histórico; host externo só pelo administrador
:id: TEST-265
:entrega: DSM4
:status: executado
:verifies: REQ-S20
:derived_from: NORM-32

`fontes: modelos para baixar, envio de planilha e histórico; host externo só pelo administrador()` — tipo *interface*.  
**Resultado esperado:** modelos, envio e histórico; só o administrador libera host externo  
**Execução:** DSM4 (status atual: executado).
````
