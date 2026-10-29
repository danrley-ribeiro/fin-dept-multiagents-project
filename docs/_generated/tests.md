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
:entrega: DSM2
:status: planejado
:verifies: REQ-F07
:derived_from: NORM-08

`test_memory_only_approved_with_provenance()` — tipo *seguranca*.  
**Resultado esperado:** saída não aprovada não é indexada; aprovada é recuperada com fonte  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_external_action_requires_approval
:id: TEST-12
:entrega: DSM2
:status: planejado
:verifies: REQ-S01
:derived_from: PROT-APR

`test_external_action_requires_approval()` — tipo *seguranca*.  
**Resultado esperado:** ajuste no ERP fica PENDENTE; execute sem approve levanta ApprovalRequired  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_denied_action_never_executes
:id: TEST-13
:entrega: DSM2
:status: planejado
:verifies: REQ-S01
:derived_from: NORM-02

`test_denied_action_never_executes()` — tipo *seguranca*.  
**Resultado esperado:** ação fora da allowlist nunca chega ao conector MCP  
**Execução:** DSM2 (status atual: planejado).
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
:entrega: DSM2
:status: planejado
:verifies: REQ-S03, REQ-F06
:derived_from: NORM-05

`test_llm_numeric_mismatch_falls_back()` — tipo *seguranca*.  
**Resultado esperado:** mock LLM com número alterado aciona template e log de fallback  
**Execução:** DSM2 (status atual: planejado).
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
:entrega: DSM2
:status: planejado
:verifies: REQ-O02
:derived_from: NORM-07

`test_prompt_log_only_when_llm_enabled()` — tipo *observabilidade*.  
**Resultado esperado:** registro de prompt existe sse flag ligada  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_cost_log_per_call_and_task
:id: TEST-18
:entrega: DSM2
:status: planejado
:verifies: REQ-O03
:derived_from: SVC-AUD

`test_cost_log_per_call_and_task()` — tipo *observabilidade*.  
**Resultado esperado:** soma por chamada = total da tarefa; zero com flag desligada  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_dashboard_filters_and_auth
:id: TEST-19
:entrega: FUTURA
:status: planejado
:verifies: REQ-O04
:derived_from: SVC-AUD

`test_dashboard_filters_and_auth()` — tipo *integracao*.  
**Resultado esperado:** filtros retornam o recorte exato; acesso anônimo negado  
**Execução:** FUTURA (status atual: planejado).
````

````{test} test_model_swap_without_redeploy
:id: TEST-20
:entrega: DSM2
:status: planejado
:verifies: REQ-C01
:derived_from: SVC-MOD

`test_model_swap_without_redeploy()` — tipo *configuracao*.  
**Resultado esperado:** troca de modelo vale na próxima tarefa sem reiniciar agentes  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_llm_not_allowed_roles_rejected
:id: TEST-21
:entrega: DSM2
:status: planejado
:verifies: REQ-C01
:derived_from: NORM-07

`test_llm_not_allowed_roles_rejected()` — tipo *configuracao*.  
**Resultado esperado:** habilitar LLM em AG-ORQ, AG-CUS ou AG-CIN é rejeitado na validação  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_token_limit_exceeded_fallback
:id: TEST-22
:entrega: DSM2
:status: planejado
:verifies: REQ-C01, REQ-O03
:derived_from: NORM-07

`test_token_limit_exceeded_fallback()` — tipo *configuracao*.  
**Resultado esperado:** cota esgotada bloqueia chamada e usa template  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_redaction_fail_closed
:id: TEST-23
:entrega: DSM2
:status: planejado
:verifies: REQ-P01
:derived_from: NORM-06

`test_redaction_fail_closed()` — tipo *seguranca*.  
**Resultado esperado:** segredo/CPF sintético sanitizado; falha de sanitização recusa gravação  
**Execução:** DSM2 (status atual: planejado).
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
:entrega: DSM2
:status: planejado
:verifies: REQ-NF02
:derived_from: SVC-AUD

`test_versions_recorded_in_logs()` — tipo *observabilidade*.  
**Resultado esperado:** todo log contém versões de prompt, regras e configuração  
**Execução:** DSM2 (status atual: planejado).
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
