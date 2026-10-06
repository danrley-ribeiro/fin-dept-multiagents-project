<!-- ARQUIVO GERADO por tools/trace.py a partir de models/*.yaml — não editar à mão -->

````{test} test_intent_decomposition_dag
:id: TEST-01
:entrega: DSM2
:status: planejado
:verifies: REQ-F01
:derived_from: PROT-DEL

`test_intent_decomposition_dag()` — tipo *protocolo-nominal*.  
**Resultado esperado:** 'fechar o mês' gera DAG CUS∥ORC → RES → CIN → REL e resposta final inform  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_unknown_intent_not_understood
:id: TEST-02
:entrega: DSM2
:status: planejado
:verifies: REQ-F01
:derived_from: PROT-SOL

`test_unknown_intent_not_understood()` — tipo *protocolo-negativo*.  
**Resultado esperado:** intenção fora do catálogo termina em RECUSADA com not-understood  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_delegation_rejects_inform_before_agree
:id: TEST-03
:entrega: DSM2
:status: planejado
:verifies: REQ-F01
:derived_from: PROT-DEL

`test_delegation_rejects_inform_before_agree()` — tipo *protocolo-negativo*.  
**Resultado esperado:** inform em AGUARDANDO levanta ProtocolViolation  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_contribution_margin_matches_gold
:id: TEST-04
:entrega: DSM2
:status: planejado
:verifies: REQ-F02
:derived_from: ROLE-CUS

`test_contribution_margin_matches_gold()` — tipo *cenario*.  
**Resultado esperado:** margens por produto/UN iguais ao gabarito com proveniência  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_budget_variance_flags_threshold
:id: TEST-05
:entrega: DSM2
:status: planejado
:verifies: REQ-F03
:derived_from: ROLE-ORC

`test_budget_variance_flags_threshold()` — tipo *cenario*.  
**Resultado esperado:** somente desvios plantados acima do limiar são sinalizados  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_results_query_ref_to_costs
:id: TEST-06
:entrega: DSM2
:status: planejado
:verifies: REQ-F04
:derived_from: PROT-QRY

`test_results_query_ref_to_costs()` — tipo *protocolo-nominal*.  
**Resultado esperado:** query-ref → inform antes do inform final de RES; DRE igual ao gabarito  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_query_ref_rejects_unsolicited_inform
:id: TEST-07
:entrega: DSM2
:status: planejado
:verifies: REQ-F04
:derived_from: PROT-QRY

`test_query_ref_rejects_unsolicited_inform()` — tipo *protocolo-negativo*.  
**Resultado esperado:** inform com conversation_id desconhecido é rejeitado  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_critical_nonconformity_vetoes_close
:id: TEST-08
:entrega: DSM2
:status: planejado
:verifies: REQ-F05
:derived_from: PROT-CMP

`test_critical_nonconformity_vetoes_close()` — tipo *protocolo-negativo*.  
**Resultado esperado:** publicar em VETADO é rejeitado; waiver humano libera com ressalva  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_planted_nonconformities_detected
:id: TEST-09
:entrega: DSM2
:status: planejado
:verifies: REQ-F05
:derived_from: NORM-04

`test_planted_nonconformities_detected()` — tipo *cenario*.  
**Resultado esperado:** recall 100% das críticas plantadas (alçada, SoD, duplicidade)  
**Execução:** DSM2 (status atual: planejado).
````

````{test} test_report_template_without_llm
:id: TEST-10
:entrega: DSM2
:status: planejado
:verifies: REQ-F06, REQ-NF01
:derived_from: ROLE-REL

`test_report_template_without_llm()` — tipo *cenario*.  
**Resultado esperado:** relatório completo com flag desligada e rede bloqueada  
**Execução:** DSM2 (status atual: planejado).
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
:status: planejado
:verifies: REQ-S02
:derived_from: PROT-LCK

`test_period_lock_conflict_rejected()` — tipo *concorrencia*.  
**Resultado esperado:** segunda reserva sobreposta recebe reserve-failure; TTL libera  
**Execução:** DSM2 (status atual: planejado).
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
:status: planejado
:verifies: REQ-O01
:derived_from: SVC-AUD

`test_trace_causal_reconstruction()` — tipo *observabilidade*.  
**Resultado esperado:** sequência causal completa reconstruída pelo conversation_id  
**Execução:** DSM2 (status atual: planejado).
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
**Resultado esperado:** habilitar LLM em ORQ, CUS ou CIN é rejeitado na validação  
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
:status: planejado
:verifies: REQ-NF01
:derived_from: SVC-MCP

`test_offline_seeded_reproducibility()` — tipo *reprodutibilidade*.  
**Resultado esperado:** mesmo seed → mesmo hash de saída, sem rede  
**Execução:** DSM2 (status atual: planejado).
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
