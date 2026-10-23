# Testes iniciais

A suíte é executada pelo `pytest` (`python -m pytest`) e tem **118 testes**: 49 unitários
(FSMs, bus, dataset, MCP, auditoria) e 69 de cenário e2e. Todos passam offline: o
`tests/conftest.py` bloqueia `socket.connect` em qualquer teste.

Um `TEST-*` só passa a `executado` em `models/tests.yaml` se existir uma função pytest com o
mesmo nome em `tests/`; o `tools/trace.py --check` verifica isso.

## Casos da DSM1 executados

| Teste | Função pytest | Arquivo |
|---|---|---|
| {need}`TEST-01` | `test_intent_decomposition_dag` | `tests/e2e/test_fechar_mes.py` |
| {need}`TEST-02` | `test_unknown_intent_not_understood` | `tests/e2e/test_intencao_desconhecida.py` |
| {need}`TEST-03` | `test_delegation_rejects_inform_before_agree` | `tests/e2e/test_protocolos_invalidos.py` |
| {need}`TEST-04` | `test_contribution_margin_matches_gold` | `tests/e2e/test_agentes_isolados.py` |
| {need}`TEST-05` | `test_budget_variance_flags_threshold` | `tests/e2e/test_agentes_isolados.py` |
| {need}`TEST-06` | `test_results_query_ref_to_costs` | `tests/e2e/test_resultados_conformidade.py` |
| {need}`TEST-07` | `test_query_ref_rejects_unsolicited_inform` | `tests/e2e/test_protocolos_invalidos.py` |
| {need}`TEST-08` | `test_critical_nonconformity_vetoes_close` | `tests/e2e/test_veto_waiver.py` |
| {need}`TEST-09` | `test_planted_nonconformities_detected` | `tests/e2e/test_resultados_conformidade.py` |
| {need}`TEST-10` | `test_report_template_without_llm` | `tests/e2e/test_resultados_conformidade.py` |
| {need}`TEST-14` | `test_period_lock_conflict_rejected` | `tests/e2e/test_lock_concorrente.py` |
| {need}`TEST-16` | `test_trace_causal_reconstruction` | `tests/e2e/test_cenario_depuracao.py` |
| {need}`TEST-24` | `test_offline_seeded_reproducibility` | `tests/e2e/test_reprodutibilidade.py` |
| {need}`TEST-26` | `test_specialist_failure_retry_then_abort` | `tests/e2e/test_falha_especialista.py` |

## Cenários e2e

| Arquivo | Cenário |
|---|---|
| `test_fechar_mes.py` | caminho feliz: DAG, ordem causal, paralelismo, gabarito, reserva liberada |
| `test_avaliar_orcamento.py` | desvios plantados, sem reserva e sem consulta a custos |
| `test_intencao_desconhecida.py` | `not-understood` sem delegar |
| `test_protocolos_invalidos.py` | inform antes de agree, inform não solicitado, segundo resultado |
| `test_veto_waiver.py` | veto, bloqueio, waiver, publicar em VETADO rejeitado, não crítica com ressalva |
| `test_falha_especialista.py` | reenvio único, abort na segunda falha, CIN mudo, tentativa anterior ignorada |
| `test_lock_concorrente.py` | reserva sobreposta recusada, TTL, fechamentos concorrentes pelo Orquestrador |
| `test_reprodutibilidade.py` | mesmo seed e mesmo hash, inclusive entre processos com `PYTHONHASHSEED` diferentes |
| `test_cenario_depuracao.py` | trace reconstruído só do JSONL e CLI `run`/`replay` |

## Ainda planejados

{need}`TEST-11`, {need}`TEST-12`, {need}`TEST-13`, {need}`TEST-15`, {need}`TEST-17`,
{need}`TEST-18`, {need}`TEST-19`, {need}`TEST-20`, {need}`TEST-21`, {need}`TEST-22`,
{need}`TEST-23` e {need}`TEST-25` dependem de serviços fora desta entrega (memória, Approval Gate,
LLM, registro de modelos, redaction, versionamento) e permanecem `planejado`.
