# Catálogo de cenários de teste da DSM4

Página **gerada** por `python tools/relatorio_numeros.py` a partir de `CENARIOS`
(`src/fin_mas/env/scenarios.py`), da conferência `python -m fin_mas cenarios --verificar` e dos testes
modelados com `entrega: DSM4` em `models/tests.yaml`. O catálogo da DSM3 (37 cenários) continua em
{doc}`../dsm3/cenarios-de-teste`; aqui ficam só os cenários que não existiam na tag
`dsm3-v0.5.0`. Não edite à mão: rode o gerador de novo.

Conferência no momento da geração: **64 de 64 cenário(s) em ordem**.

## Terminal

```bash
python -m fin_mas cenarios --verificar --filtro <nome>   # resposta, invariantes e repetibilidade
python -m fin_mas run --scenario <nome>                  # trilha causal legível
python -m fin_mas run --scenario <nome> --trace t.jsonl && python -m fin_mas invariantes t.jsonl
```

| Cenário | Cognição | Porte | Segmento | Resposta | Invariantes | Repetível | O que observar |
|---|---|---|---|---|---|---|---|
| `aprovador_sem_alcada` | `basico` | micro | software_servicos | `inform` | ok | sim | correção de carla recusada (POL-10, gerente sem alçada no porte); o controller corrige; publicado |
| `delegacao_valida` | `basico` | media | software_servicos | `inform` | ok | sim | waiver de ana por delegação de diego (DLG-001) aceito; publicado com ressalva |
| `delegacao_expirada` | `basico` | media | software_servicos | `inform` | ok | sim | waiver de ana recusado (POL-11, delegação expirada); waiver de diego aceito |
| `dupla_aprovacao` | `basico` | grande | software_servicos | `inform` | ok | sim | endorse de carla (PENDENTE->PENDENTE), approve de diego; aprovado_por com o aval; publicado |
| `dupla_mesma_pessoa_recusada` | `basico` | grande | software_servicos | `inform` | ok | sim | aprovação de carla depois do próprio aval recusada (POL-12); diego aprova; publicado |
| `escalonamento` | `basico` | media | software_servicos | `inform` | ok | sim | elisa recusada (POL-14) antes; ticket escalado de gerente para diretor; elisa aprova depois |
| `ataque_acesso_avancado` | `basico` | grande | software_servicos | `failure` | ok | sim | ataques rejeitados (IAM-04, 08, 09, POL-10, 11, 12); prazo esgota; nada publicado |
| `res_explica_variacao` | `local` | media | software_servicos | `inform` | ok | sim | hipótese causa_custo_fixo confirmada por cálculo sobre AG-CUS e histórico; explicação aponta CC-OPS; insight no relatório |
| `res_insumo_faltante` | `local` | media | software_servicos | `inform` | ok | sim | P-CONSULTAR-ESPECIALISTA falha, P-CONSULTAR-DE-NOVO falha, P-DAR-POR-INDISPONIVEL; P-CONSOLIDAR-COM-RESSALVA; publicado com ressalva, sem reenvio do Orquestrador |
| `cus_rateio_alternativo` | `local` | media | software_servicos | `inform` | ok | sim | P-RATEIO-PADRAO falha; P-RATEIO-PROPORCIONAL-RECEITA escolhido (média); resultado por UN igual ao gabarito do critério; ressalva no relatório |
| `rel_relatorio_de_excecao` | `local` | media | software_servicos | `inform` | ok | sim | P-RELATORIO-DE-EXCECAO escolhido; exceção antes dos indicadores; base normativa COSO-ALCADA; texto por template |
| `aprendizado_regra` | `local` | media | software_servicos | `inform` | ok | sim | duas observações 'refutada' de local:R-OBS-REPETICAO; hipótese de setembro com confiança 0,40; P-VERIFICAR-COM-CIN não aplicável; uma consulta a menos que sem aprendizado |
| `compromisso_aberto` | `local` | media | software_servicos | `inform` | ok | sim | P-CONSULTAR-CIN falha e é replanejado; P-SINALIZAR abandonada por reconsideração; conta atribuída a controle (igual ao gabarito) |
| `compromisso_obstinado` | `local` | media | software_servicos | `inform` | ok | sim | P-SINALIZAR 'mantida' e concluída; conta sinalizada como desvio orçamentário (diferente do gabarito) |
| `compromisso_cego` | `local` | media | software_servicos | `inform` | ok | sim | P-CONSULTAR-CIN 'insistida' (sem replanejar); P-SINALIZAR mantida; falso desvio |
| `memoria_reincidencia_orc` | `local` | media | software_servicos | `inform` | ok | sim | memória 'correcao' consultada pelo AG-ORC; hipótese de origem local:R-MEM-REINCIDENCIA confirmada pelo AG-CIN; sem falso desvio em setembro |
| `normas_fundamentam_achado` | `local` | media | software_servicos | `inform` | ok | sim | achado de sod com fundamento COSO-2013, trecho COSO-SEGREGACAO (corpus-v1) no veto; o relatório de exceção cita a mesma base |
| `normas_sem_evidencia` | `local` | media | software_servicos | `inform` | ok | sim | normas.buscar devolve zero trechos para duplicidade; achado marcado 'sem evidência'; o veto vale pela regra interna |
| `fechamento_mei` | `basico` | mei | software_servicos | `inform` | ok | sim | veto só da duplicidade (crítica); estorno aprovado; SoD e competência viram ressalvas; realizado da planilha |
| `fechamento_media_ii` | `basico` | media_ii | software_servicos | `inform` | ok | sim | veto da alçada com reaprovação; dois desvios acima de 7% e de R$ 20 mil; publicado |
| `fechamento_comercio` | `basico` | media | comercio | `inform` | ok | sim | AG-CUS rateia por m² (80/20); estorno aprovado; relatório publicado |
| `fechamento_servicos` | `basico` | media | servicos | `inform` | ok | sim | AG-CUS rateia por horas (65/35); SoD vetado e reaprovado; relatório publicado |
| `fechamento_industria` | `basico` | media | industria | `inform` | ok | sim | AG-CUS rateia por horas-máquina (70/30); desvio atribuído a controle; estorno aprovado |
| `conector_rest_demo` | `basico` | media | software_servicos | `inform` | ok | sim | mesmo resultado do veto_correcao sobre o ERP simulado; a correção só chega ao ERP com o ticket aprovado |
| `conector_fora_do_ar` | `basico` | media | software_servicos | `failure` | ok | sim | failure com 'fonte indisponível'; leituras negadas auditadas; nada publicado |
| `planilha_fora_do_modelo` | `basico` | pequena | software_servicos | `inform` | ok | sim | mesmo resultado da mesma empresa no modelo canônico; linha de total excluída e conferida |
| `mcp_tools_entendidas` | `basico` | micro | software_servicos | `inform` | ok | sim | mesmo resultado da planilha lida pela pasta; proveniência mcp://mcp-excel/ler_aba#Aba |

## Dashboard

Qualquer cenário do catálogo roda ao vivo no escritório e, se o trace foi exportado
(`python -m fin_mas export --out web/public/traces`), também no replay offline.

```bash
python -m fin_mas serve --demo --scenario <nome>        # ao vivo: http://127.0.0.1:8765 (avaliador / Demonstracao-SMA-2026)
./iniciar.sh replay                                     # replay dos traces exportados: http://127.0.0.1:4173
```

| Cenário | Ao vivo | Replay (trace exportado) | Onde olhar |
|---|---|---|---|
| `aprovador_sem_alcada` | `serve --demo --scenario aprovador_sem_alcada` | sim | aba Porte e o relatório publicado |
| `delegacao_valida` | `serve --demo --scenario delegacao_valida` | sim | feed de eventos |
| `delegacao_expirada` | `serve --demo --scenario delegacao_expirada` | sim | feed de eventos |
| `dupla_aprovacao` | `serve --demo --scenario dupla_aprovacao` | sim | aba Porte e o relatório publicado |
| `dupla_mesma_pessoa_recusada` | `serve --demo --scenario dupla_mesma_pessoa_recusada` | sim | aba Porte e o relatório publicado |
| `escalonamento` | `serve --demo --scenario escalonamento` | sim | feed de eventos |
| `ataque_acesso_avancado` | `serve --demo --scenario ataque_acesso_avancado` | sim | aba Porte e o relatório publicado |
| `res_explica_variacao` | `serve --demo --scenario res_explica_variacao` | sim | mente do agente (crenças, desejos, deliberações) |
| `res_insumo_faltante` | `serve --demo --scenario res_insumo_faltante` | sim | mente do agente (crenças, desejos, deliberações) |
| `cus_rateio_alternativo` | `serve --demo --scenario cus_rateio_alternativo` | sim | mente do agente (crenças, desejos, deliberações) |
| `rel_relatorio_de_excecao` | `serve --demo --scenario rel_relatorio_de_excecao` | sim | mente do agente (crenças, desejos, deliberações) |
| `aprendizado_regra` | `serve --demo --scenario aprendizado_regra` | sim | mente do agente (crenças, desejos, deliberações) |
| `compromisso_aberto` | `serve --demo --scenario compromisso_aberto` | sim | mente do agente (crenças, desejos, deliberações) |
| `compromisso_obstinado` | `serve --demo --scenario compromisso_obstinado` | sim | mente do agente (crenças, desejos, deliberações) |
| `compromisso_cego` | `serve --demo --scenario compromisso_cego` | sim | mente do agente (crenças, desejos, deliberações) |
| `memoria_reincidencia_orc` | `serve --demo --scenario memoria_reincidencia_orc` | sim | mente do agente (crenças, desejos, deliberações) |
| `normas_fundamentam_achado` | `serve --demo --scenario normas_fundamentam_achado` | sim | mente do agente (crenças, desejos, deliberações) |
| `normas_sem_evidencia` | `serve --demo --scenario normas_sem_evidencia` | sim | mente do agente (crenças, desejos, deliberações) |
| `fechamento_mei` | `serve --demo --scenario fechamento_mei` | sim | aba Porte e o relatório publicado |
| `fechamento_media_ii` | `serve --demo --scenario fechamento_media_ii` | sim | aba Porte e o relatório publicado |
| `fechamento_comercio` | `serve --demo --scenario fechamento_comercio` | sim | aba Porte e o relatório publicado |
| `fechamento_servicos` | `serve --demo --scenario fechamento_servicos` | sim | aba Porte e o relatório publicado |
| `fechamento_industria` | `serve --demo --scenario fechamento_industria` | sim | aba Porte e o relatório publicado |
| `conector_rest_demo` | `serve --demo --scenario conector_rest_demo` | sim | feed de eventos |
| `conector_fora_do_ar` | `serve --demo --scenario conector_fora_do_ar` | sim | feed de eventos |
| `planilha_fora_do_modelo` | `serve --demo --scenario planilha_fora_do_modelo` | sim | aba Porte e o relatório publicado |
| `mcp_tools_entendidas` | `serve --demo --scenario mcp_tools_entendidas` | sim | aba Porte e o relatório publicado |

## Testes que exercitam cada cenário

Arquivos de `tests/` que citam o nome do cenário.

| Cenário | Arquivos de teste |
|---|---|
| `aprovador_sem_alcada` | `tests/e2e/test_acesso_avancado.py` |
| `delegacao_valida` | `tests/e2e/test_acesso_avancado.py`, `tests/integration/test_aprovacao_e_acesso_dsm4.py` |
| `delegacao_expirada` | `tests/e2e/test_acesso_avancado.py` |
| `dupla_aprovacao` | `tests/e2e/test_acesso_avancado.py`, `tests/integration/test_aprovacao_e_acesso_dsm4.py`, `tests/integration/test_empresa_porte_simulacao.py` |
| `dupla_mesma_pessoa_recusada` | `tests/e2e/test_acesso_avancado.py` |
| `escalonamento` | `tests/e2e/test_acesso_avancado.py` |
| `ataque_acesso_avancado` | `tests/e2e/test_acesso_avancado.py` |
| `res_explica_variacao` | `tests/e2e/test_aprendizado_compromisso.py`, `tests/e2e/test_cognicao_local.py`, `tests/e2e/test_especialistas_bdi.py`, `tests/integration/test_acesso_cli.py`, `tests/integration/test_cognicao_dsm4.py` |
| `res_insumo_faltante` | `tests/e2e/test_cognicao_local.py`, `tests/e2e/test_especialistas_bdi.py`, `tests/integration/test_cognicao_dsm4.py` |
| `cus_rateio_alternativo` | `tests/e2e/test_aprendizado_compromisso.py`, `tests/e2e/test_cognicao_local.py`, `tests/e2e/test_especialistas_bdi.py`, `tests/integration/test_cognicao_dsm4.py` |
| `rel_relatorio_de_excecao` | `tests/e2e/test_cognicao_local.py`, `tests/e2e/test_especialistas_bdi.py`, `tests/integration/test_cognicao_dsm4.py` |
| `aprendizado_regra` | `tests/e2e/test_aprendizado_compromisso.py`, `tests/e2e/test_especialistas_bdi.py`, `tests/integration/test_cognicao_dsm4.py` |
| `compromisso_aberto` | `tests/e2e/test_aprendizado_compromisso.py`, `tests/e2e/test_especialistas_bdi.py`, `tests/integration/test_cognicao_dsm4.py` |
| `compromisso_obstinado` | `tests/e2e/test_especialistas_bdi.py`, `tests/integration/test_cognicao_dsm4.py` |
| `compromisso_cego` | `tests/e2e/test_aprendizado_compromisso.py`, `tests/e2e/test_especialistas_bdi.py`, `tests/integration/test_cognicao_dsm4.py` |
| `memoria_reincidencia_orc` | `tests/e2e/test_especialistas_bdi.py`, `tests/e2e/test_memoria_lida.py`, `tests/integration/test_cognicao_dsm4.py` |
| `normas_fundamentam_achado` | `tests/e2e/test_cognicao_local.py`, `tests/e2e/test_conhecimento_normativo.py`, `tests/e2e/test_especialistas_bdi.py`, `tests/integration/test_cognicao_dsm4.py` |
| `normas_sem_evidencia` | `tests/e2e/test_cognicao_local.py`, `tests/e2e/test_conhecimento_normativo.py`, `tests/e2e/test_especialistas_bdi.py`, `tests/integration/test_cognicao_dsm4.py` |
| `fechamento_mei` | `tests/e2e/test_portes_segmentos.py`, `tests/integration/test_implantacao_dsm4.py` |
| `fechamento_media_ii` | `tests/e2e/test_portes_segmentos.py` |
| `fechamento_comercio` | `tests/e2e/test_portes_segmentos.py` |
| `fechamento_servicos` | `tests/e2e/test_portes_segmentos.py` |
| `fechamento_industria` | `tests/e2e/test_portes_segmentos.py`, `tests/integration/test_implantacao_dsm4.py` |
| `conector_rest_demo` | `tests/e2e/test_escrita_sem_confirmacao.py`, `tests/integration/test_conectores.py` |
| `conector_fora_do_ar` | `tests/integration/test_conectores.py` |
| `planilha_fora_do_modelo` | `tests/integration/test_conectores.py` |
| `mcp_tools_entendidas` | `tests/integration/test_conectores.py` |

## Testes modelados da DSM4

Testes com `entrega: DSM4` em `models/tests.yaml` (o `tools/trace.py --check` confere que cada função
existe); o título é o campo `esperado` do modelo.

| Teste | Função | Arquivo | Tipo | O que verifica |
|---|---|---|---|---|
| TEST-201 | `test_new_scenarios_deliberate_and_keep_beliefs_with_deterministic_sources` | `tests/e2e/test_especialistas_bdi.py` | e2e | nos onze cenários novos há deliberação com plano aplicável e não aplicável e toda crença tem fonte determinística |
| TEST-202 | `test_basic_level_runs_the_same_scenario_with_the_reactive_specialists` | `tests/e2e/test_especialistas_bdi.py` | reprodutibilidade | no nível básico os mesmos cenários rodam com as classes reativas, sem registro BDI de RES, CUS e REL |
| TEST-203 | `test_build_system_picks_the_variant_by_cognition_level` | `tests/e2e/test_especialistas_bdi.py` | e2e | variante BDI nos níveis local e llm; classe reativa no básico; estratégia de compromisso inválida é recusada |
| TEST-204 | `test_results_agent_explains_a_relevant_variation_with_verified_evidence` | `tests/e2e/test_especialistas_bdi.py` | e2e | variação do EBITDA% vira hipótese, o AG-RES pede o detalhe ao AG-CUS e a explicação aponta o centro do gabarito |
| TEST-205 | `test_variation_hypothesis_falls_back_to_history_when_the_cost_agent_goes_offline` | `tests/e2e/test_especialistas_bdi.py` | e2e | plano de detalhe falha por timeout e o AG-RES replaneja para a conferência no histórico |
| TEST-206 | `test_results_agent_replans_when_a_specialist_is_silent_and_decides_by_size_and_criticality` | `tests/e2e/test_especialistas_bdi.py` | e2e | duas consultas perdidas: média consolida com ressalva, grande falha explicitamente, básico aborta o fechamento |
| TEST-207 | `test_missing_critical_input_never_becomes_a_partial_result` | `tests/e2e/test_especialistas_bdi.py` | e2e | sem custos não há DRE parcial em nenhum porte: falha explícita |
| TEST-208 | `test_cost_agent_picks_an_allocation_criterion_when_the_driver_is_unusable` | `tests/e2e/test_especialistas_bdi.py` | e2e | direcionador inconsistente: plano padrão falha, critério proporcional à receita escolhido, conta igual ao gabarito, motivo registrado |
| TEST-209 | `test_cost_criterion_depends_on_company_size_and_on_what_is_wrong_with_the_driver` | `tests/e2e/test_especialistas_bdi.py` | e2e | microempresa divide em partes iguais; tabela ausente reusa a última aprovada; sem problema, critério padrão |
| TEST-210 | `test_report_agent_chooses_structure_by_findings_and_audience` | `tests/e2e/test_especialistas_bdi.py` | e2e | relatório de exceção com veto corrigido, sumário quando conforme, relatório completo para conselho e auditoria |
| TEST-211 | `test_exception_report_orders_caveats_and_keeps_only_verified_insights` | `tests/e2e/test_especialistas_bdi.py` | e2e | waiver primeiro nas ressalvas; hipótese arquivada não é reproduzida, só contada |
| TEST-212 | `test_model_text_goes_to_the_end_of_the_report_labelled_and_never_inside_template_sentences` | `tests/e2e/test_especialistas_bdi.py` | seguranca | texto de modelo ao fim do relatório, rotulado; corpo igual ao do template; AG-CUS recusa LLM |
| TEST-213 | `test_deliberation_and_grounding_metrics_are_read_from_the_trace` | `tests/e2e/test_especialistas_bdi.py` | observabilidade | MET-30 e MET-31 calculadas só do trace: replanejamentos, insistências, crenças sem fonte, citações incompletas |
| TEST-214 | `test_rule_confidence_follows_refutations_and_changes_what_the_agent_does` | `tests/e2e/test_aprendizado_compromisso.py` | e2e | duas refutações levam a confiança de 0,80 a 0,40 e a hipótese deixa de justificar nova consulta |
| TEST-215 | `test_rule_confidence_rises_with_confirmations` | `tests/e2e/test_aprendizado_compromisso.py` | e2e | confirmações em meses seguidos elevam a confiança de 0,80 a 0,87 e 0,90 |
| TEST-216 | `test_only_verified_evidence_counts_for_learning` | `tests/e2e/test_aprendizado_compromisso.py` | seguranca | hipótese arquivada, origem LLM e observação sem fonte determinística não contam |
| TEST-217 | `test_results_agent_rules_learn_too` | `tests/e2e/test_aprendizado_compromisso.py` | e2e | a regra de custo fixo do AG-RES registra a confirmação com a fonte da evidência |
| TEST-218 | `test_three_commitment_strategies_differ_on_the_same_situation` | `tests/e2e/test_aprendizado_compromisso.py` | e2e | aberto replaneja e abandona o alerta (gabarito); obstinado mantém o alerta; cego insiste no plano; três traces distintos |
| TEST-219 | `test_open_commitment_is_the_default_and_reproduces_previous_behaviour` | `tests/e2e/test_aprendizado_compromisso.py` | reprodutibilidade | compromisso aberto explícito produz o mesmo trace, byte a byte, dos cenários existentes |
| TEST-220 | `test_blind_commitment_stops_insisting_at_the_cap_and_costs_the_deadline` | `tests/e2e/test_aprendizado_compromisso.py` | e2e | falha permanente: o cego insiste duas vezes, estoura o prazo e a solicitação falha; o aberto entrega com ressalva |
| TEST-221 | `test_commitment_applies_to_the_new_bdi_specialists` | `tests/e2e/test_aprendizado_compromisso.py` | e2e | AG-CUS cego relê o direcionador inconsistente duas vezes antes de trocar de critério |
| TEST-222 | `test_budget_agent_reads_approved_memory_and_avoids_a_false_deviation` | `tests/e2e/test_memoria_lida.py` | e2e | correção aprovada em agosto vira hipótese de reincidência em setembro, o AG-CIN confirma e o falso desvio some |
| TEST-223 | `test_memory_corroboration_raises_the_confidence_of_an_existing_hypothesis` | `tests/e2e/test_memoria_lida.py` | e2e | observação e memória apontam a mesma causa: hipótese corroborada, com confiança maior |
| TEST-224 | `test_memory_read_access_is_by_type_and_denials_are_audited` | `tests/e2e/test_memoria_lida.py` | seguranca | correção legível por ORC, RES e REL; waiver e bloqueio só pelo AG-CIN; leitura negada fica no trace |
| TEST-225 | `test_report_and_results_agents_cite_previous_approved_corrections` | `tests/e2e/test_memoria_lida.py` | e2e | o relatório de exceção e a explicação do AG-RES citam a correção anterior com o id da memória |
| TEST-226 | `test_search_returns_the_expected_passage_first_with_provenance` | `tests/e2e/test_conhecimento_normativo.py` | e2e | top-k esperado para oito consultas de referência, com documento, trecho e versão |
| TEST-227 | `test_search_without_evidence_returns_nothing` | `tests/e2e/test_conhecimento_normativo.py` | seguranca | assunto fora do corpus devolve lista vazia; a tool é negada fora da allowlist |
| TEST-228 | `test_finding_cites_the_passage_that_grounds_it` | `tests/e2e/test_conhecimento_normativo.py` | e2e | achado de SoD cita COSO-SEGREGACAO com a versão do corpus; no básico não há busca nem campo novo |
| TEST-229 | `test_no_evidence_is_declared_and_never_filled` | `tests/e2e/test_conhecimento_normativo.py` | seguranca | duplicidade sai marcada sem evidência, sem documento nem trecho; o veto segue pela regra interna |
| TEST-230 | `test_cli_checks_every_new_scenario_against_the_invariants` | `tests/integration/test_cognicao_dsm4.py` | integracao | cenarios --verificar aprova os cenários novos: resposta explícita, invariantes e repetição |
| TEST-231 | `test_cli_shows_deliberation_of_the_new_bdi_specialists` | `tests/integration/test_cognicao_dsm4.py` | integracao | a trilha no terminal mostra deliberação, falha de plano, hipótese e compromisso por parâmetro |
| TEST-232 | `test_cli_searches_the_normative_base_and_reports_missing_evidence` | `tests/integration/test_cognicao_dsm4.py` | integracao | fin-mas normas devolve o trecho com proveniência e sai com código 1 quando não há evidência |
| TEST-233 | `test_learning_persists_between_runs_in_a_sealed_file` | `tests/integration/test_cognicao_dsm4.py` | integracao | arquivo selado guarda a observação; a execução seguinte usa a confiança aprendida; reprocessar não conta duas vezes |
| TEST-234 | `test_tampered_learning_file_fails_closed` | `tests/integration/test_cognicao_dsm4.py` | seguranca | arquivo adulterado desliga o aprendizado, as regras voltam à confiança inicial e nada é gravado |
| TEST-235 | `test_equivalent_workflow_matches_the_mas_on_the_comparable_scenarios` | `tests/e2e/test_equivalencia_workflow.py` | e2e | sem falhas, workflow equivalente e SMA básico dão o mesmo status, DRE, classificação, correções e decisões nos 11 cenários comparáveis |
| TEST-236 | `test_equivalent_workflow_matches_the_mas_on_drawn_workloads` | `tests/e2e/test_equivalencia_workflow.py` | e2e | a mesma igualdade nas cargas sorteadas do experimento, nos quatro portes e nas duas intenções |
| TEST-237 | `test_equivalent_workflow_has_one_controller_and_only_approval_messages` | `tests/e2e/test_equivalencia_workflow.py` | e2e | um só componente decide; as únicas mensagens são as do Approval Gate; correção só com aprovação |
| TEST-238 | `test_equivalence_stops_where_messages_can_be_lost_and_the_minimal_workflow_never_was_equivalent` | `tests/e2e/test_equivalencia_workflow.py` | e2e | com perda de mensagens o SMA falha e o workflow publica; o workflow mínimo publica a crítica que os outros vetam |
| TEST-239 | `test_chaos_and_parameters_change_nothing_by_default` | `tests/e2e/test_caos.py` | e2e | sem modelo de falhas e com os parâmetros padrão, o hash do trace é o de sempre |
| TEST-240 | `test_same_seed_repeats_the_run_and_each_factor_has_its_own_draw` | `tests/e2e/test_caos.py` | e2e | mesma seed, mesmo trace; ligar uma falha não muda plantios, perfil do aprovador nem os dados |
| TEST-241 | `test_random_loss_and_outages_reach_the_bus_and_every_silence_is_flagged` | `tests/e2e/test_caos.py` | e2e | perdas e indisponibilidades chegam ao barramento; solicitação sem resposta é acusada pelo INV-07 |
| TEST-242 | `test_slow_or_absent_approver_lets_the_ticket_expire_and_nothing_is_published` | `tests/e2e/test_caos.py` | e2e | aprovador lento ou ausente: o ticket expira, a publicação fica bloqueada e nenhuma crítica sai |
| TEST-243 | `test_attacks_during_combined_failures_are_all_rejected` | `tests/e2e/test_caos.py` | seguranca | ataques ao Approval Gate sob perda, atraso, indisponibilidade e humano lento: nenhum aceito |
| TEST-244 | `test_injected_parameters_change_the_coordination_they_control` | `tests/e2e/test_caos.py` | e2e | tentativas, correções, extensão de prazo, reserva, prazos e limiar mudam o comportamento e ficam no trace |
| TEST-245 | `test_quick_experiment_writes_every_output_and_repeats_byte_for_byte` | `tests/integration/test_experimento.py` | integracao | o comando do experimento grava os 12 arquivos e os reproduzíveis saem idênticos numa segunda execução |
| TEST-246 | `test_pipeline_statistics_match_hand_computed_references` | `tests/integration/test_experimento.py` | integracao | Wilcoxon, Mann-Whitney, Cliff, Holm e descritivas gravados pelo pipeline batem com valores calculados à mão |
| TEST-247 | `test_summary_and_tests_are_recomputed_from_the_raw_rows` | `tests/integration/test_experimento.py` | integracao | a análise refeita só com o execucoes.csv dá o mesmo resumo e os mesmos testes |
| TEST-170 | `test_legal_bands_follow_lc123_and_bndes` | `tests/e2e/test_portes_segmentos.py` | cenario | faixas legais: MEI só por opção (LC 123/2006, art. 18-A), ME, EPP, Média I e II e grande (BNDES); os quatro portes de antes inalterados |
| TEST-171 | `test_mei_runs_alone_without_erp_and_with_compensating_control` | `tests/e2e/test_portes_segmentos.py` | cenario | MEI com uma pessoa e sem ERP: SoD impossível vira controle compensatório, duplicidade vetada e estornada, plantio de alçada recusado |
| TEST-172 | `test_media_ii_applies_the_upper_band_rules` | `tests/e2e/test_portes_segmentos.py` | cenario | Média empresa II: receita na faixa de R$ 90 a 300 milhões, materialidade e pesos do porte, alçada reaprovada e publicação |
| TEST-173 | `test_segment_changes_accounts_costs_and_allocation_driver` | `tests/e2e/test_portes_segmentos.py` | cenario | comércio, serviços e indústria: plano de contas, unidades e centros do segmento; AG-CUS rateia pelo direcionador e o resultado por UN confere com o gabarito |
| TEST-174 | `test_segment_cost_structure_is_consistent` | `tests/e2e/test_portes_segmentos.py` | cenario | CMV pelo estoque no comércio, horas de mão de obra direta em serviços, custo de produção e rateio dos CIF na indústria |
| TEST-175 | `test_default_segment_keeps_the_dsm3_data_and_trace` | `tests/e2e/test_portes_segmentos.py` | regressao | segmento padrão gera os mesmos dados e o mesmo hash de trace da DSM3; o meta só ganha segmento fora do padrão |
| TEST-176 | `test_backup_restores_into_another_folder_on_another_machine` | `tests/integration/test_backup_restauracao.py` | integracao | backup com manifesto selado e chaves em arquivo separado; restauração em outra pasta e outra pasta de chaves com selos, trilha e memória conferidos |
| TEST-177 | `test_tampered_or_mismatched_backup_is_refused` | `tests/integration/test_backup_restauracao.py` | seguranca | arquivo trocado, hash corrigido, manifesto re-selado, fuga de diretório, arquivo a mais, chaves de outra instalação e rollback: recusados sem gravar nada |
| TEST-178 | `test_migration_mechanism_with_an_example_from_version_1_to_2` | `tests/integration/test_backup_restauracao.py` | integracao | migrar confere o selo na versão de origem, aplica a migração de exemplo 1->2 e grava selado; o sistema na versão 1 recusa o arquivo migrado |
| TEST-179 | `test_server_on_all_interfaces_still_accepts_only_loopback_names` | `tests/integration/test_implantacao_dsm4.py` | seguranca | serve --host 0.0.0.0 (contêiner) continua recusando Host e Origin que não sejam de loopback |
| TEST-180 | `test_dashboard_api_lists_sizes_segments_templates_and_restarts_with_a_segment` | `tests/integration/test_implantacao_dsm4.py` | integracao | /api/portes com segmentos, /api/modelos com os portes novos e os segmentos, reiniciar com segmento e segmento desconhecido recusado |
| TEST-181 | `test_wheel_installs_in_a_clean_venv_and_runs_outside_the_repository` | `tests/integration/test_implantacao_dsm4.py` | integracao | wheel com YAML e dashboard embutidos instalado num venv limpo: list, run (mesmo hash do checkout), instalar --demo e doctor fora do repositório |
| TEST-182 | `test_container_files_publish_only_on_loopback_and_keep_keys_apart` | `tests/integration/test_implantacao_dsm4.py` | configuracao | compose publica só em 127.0.0.1, volumes de dados e chaves separados, usuário sem privilégio, healthcheck em /api/saude |
| TEST-300 | `test_new_scenarios_hold_every_invariant_and_repeat` | `tests/e2e/test_acesso_avancado.py` | e2e | os sete cenários novos repetem o hash e respeitam todos os invariantes |
| TEST-301 | `test_person_without_authority_in_the_size_cannot_release` | `tests/e2e/test_acesso_avancado.py` | e2e | liberação sem alçada no porte recusada (POL-10); exposição no veto |
| TEST-302 | `test_without_iam_the_veto_carries_no_exposure` | `tests/e2e/test_acesso_avancado.py` | e2e | sem SVC-IAM o veto e o ticket são os da v0.5.0 |
| TEST-303 | `test_delegated_decision_records_who_delegated` | `tests/e2e/test_acesso_avancado.py` | e2e | decisão por delegação aceita e registrada com quem delegou (POL-11) |
| TEST-304 | `test_expired_delegation_is_refused_and_the_delegator_decides` | `tests/e2e/test_acesso_avancado.py` | e2e | delegação expirada recusada (POL-11) |
| TEST-305 | `test_four_eyes_endorse_then_approve_by_another_person` | `tests/e2e/test_acesso_avancado.py` | e2e | endorse PENDENTE->PENDENTE e approve de outra pessoa (POL-12) |
| TEST-306 | `test_same_person_cannot_endorse_and_approve` | `tests/e2e/test_acesso_avancado.py` | e2e | a mesma pessoa nos dois passos é recusada (POL-12) |
| TEST-307 | `test_approval_without_endorsement_is_refused_above_the_limit` | `tests/e2e/test_acesso_avancado.py` | e2e | aprovação direta acima do limite recusada (POL-12) |
| TEST-308 | `test_ticket_escalates_after_half_the_deadline` | `tests/e2e/test_acesso_avancado.py` | e2e | nível acima recusado antes; escalonamento registrado na metade do prazo (POL-14) |
| TEST-309 | `test_advanced_access_attacks_are_all_rejected` | `tests/e2e/test_acesso_avancado.py` | seguranca | doze ataques ao acesso avançado, nenhum aceito |
| TEST-310 | `test_invariants_catch_a_single_person_release_and_one_above_authority` | `tests/e2e/test_acesso_avancado.py` | seguranca | INV-09 e INV-10 acusam trace adulterado |
| TEST-311 | `test_one_company_memory_is_never_remembered_in_another` | `tests/e2e/test_acesso_avancado.py` | e2e | memória de uma empresa não vira reincidência em outra; cópia fica comprometida |
| TEST-312 | `test_second_factor_from_the_terminal_with_policy_replay_and_recovery_codes` | `tests/integration/test_acesso_avancado_cli.py` | integracao | 2FA pela CLI: política, replay, janela, recuperação de uso único |
| TEST-313 | `test_vault_keeps_llm_keys_without_ever_showing_them` | `tests/integration/test_acesso_avancado_cli.py` | integracao | cofre 0600 fora da pasta de dados, chave de LLM pelo cofre, valor nunca mostrado |
| TEST-314 | `test_delegation_policy_and_companies_from_the_terminal` | `tests/integration/test_acesso_avancado_cli.py` | integracao | delegação, escalonamento e escopo de empresas pela CLI |
| TEST-315 | `test_memory_copied_to_another_folder_is_adopted_under_permission` | `tests/integration/test_acesso_avancado_cli.py` | integracao | cópia íntegra adotada sob PERM-MEM-ADOTAR; adulterada recusada |
| TEST-316 | `test_two_runs_writing_the_same_memory_at_once_keep_both_entries` | `tests/integration/test_acesso_avancado_cli.py` | integracao | quatro execuções simultâneas sobre a mesma memória, nenhuma entrada perdida |
| TEST-317 | `test_two_step_login_with_short_lived_pre_session` | `tests/integration/test_dashboard_acesso_avancado.py` | integracao | login em dois passos no servidor; pré-sessão só vale em /api/login/2fa |
| TEST-318 | `test_policy_requiring_second_factor_only_lets_the_account_enrol` | `tests/integration/test_dashboard_acesso_avancado.py` | integracao | conta sem o 2FA exigido só consegue ativá-lo |
| TEST-319 | `test_vault_routes_store_llm_keys_without_returning_them` | `tests/integration/test_dashboard_acesso_avancado.py` | integracao | rotas do cofre nunca devolvem o valor |
| TEST-320 | `test_each_company_gets_its_own_simulation_and_nothing_crosses_over` | `tests/integration/test_dashboard_acesso_avancado.py` | integracao | uma simulação por empresa; seletor /api/empresa; nada cruza |
| TEST-321 | `test_enrol_second_factor_then_log_in_with_a_recovery_code` | `tests/tui/test_tui_acesso_avancado.py` | interface | TUI: ativar 2FA, segredo e códigos uma vez, entrada em dois passos |
| TEST-322 | `test_approver_creates_and_revokes_a_delegation` | `tests/tui/test_tui_acesso_avancado.py` | interface | TUI: criar e revogar delegação |
| TEST-323 | `test_administrator_sets_policy_vault_companies_and_sees_authority_limits` | `tests/tui/test_tui_acesso_avancado.py` | interface | TUI: política, cofre, empresas e alçadas |
| TEST-250 | `test_understanding_openapi_samples_spreadsheet_and_mcp_match_the_answer_key` | `tests/integration/test_conectores.py` | integracao | OpenAPI, amostras JSON, planilha fora do modelo e tools MCP: sugestões iguais ao gabarito, com confiança e motivo |
| TEST-251 | `test_quality_report_flags_missing_duplicates_out_of_period_totals_and_negatives` | `tests/integration/test_conectores.py` | integracao | faltantes, duplicados, fora da competência, total que não fecha e negativos acusados; prévia redigida |
| TEST-252 | `test_rest_demo_closes_the_month_like_the_simulated_erp_and_writes_only_with_approval` | `tests/integration/test_conectores.py` | integracao | fechamento sobre o ERP de demonstração igual ao ERP simulado; correção só com ticket aprovado |
| TEST-253 | `test_source_down_fails_explicitly_and_does_not_hang` | `tests/integration/test_conectores.py` | integracao | failure com o motivo, leituras negadas auditadas, nada publicado, em segundos |
| TEST-254 | `test_rest_connector_errors_401_500_timeout_invalid_json_and_redirect_are_redacted` | `tests/integration/test_conectores.py` | seguranca | erros tipados e redigidos; redirecionamento não seguido; credencial não vai a outro host |
| TEST-255 | `test_external_host_is_denied_without_admin_release` | `tests/integration/test_conectores.py` | seguranca | host externo recusado antes de qualquer conexão; liberado, só o ambiente offline bloqueia |
| TEST-256 | `test_simulated_connector_and_spreadsheet_folder_preserve_the_current_behavior` | `tests/integration/test_conectores.py` | integracao | ERP simulado por conector com o mesmo trace; pasta com uma planilha igual a --pasta; várias competências |
| TEST-257 | `test_spreadsheet_off_model_and_mcp_scenarios_match_the_canonical_reading` | `tests/integration/test_conectores.py` | e2e | planilha_fora_do_modelo e mcp_tools_entendidas iguais à leitura canônica e repetíveis |
| TEST-258 | `test_mcp_client_talks_to_the_excel_server_over_stdio` | `tests/integration/test_conectores.py` | integracao | initialize, tools/list, tools/call e erro de tool contra o servidor embutido |
| TEST-259 | `test_optional_llm_only_suggests_and_goes_through_the_same_validation` | `tests/integration/test_conectores.py` | integracao | LLM só sugere pendentes, envia só nomes e tipos; inválidas rejeitadas; externo sem consentimento não envia |
| TEST-260 | `test_cli_understands_tests_and_serves_the_demo_erp` | `tests/integration/test_conectores.py` | integracao | fontes entender, fontes testar e erp-demo pela CLI; token fora da saída |
| TEST-261 | `test_sources_flow_register_test_understand_adjust_confirm_activate_and_close` | `tests/integration/test_dashboard_fontes.py` | integracao | cadastro, teste, entendimento, ajuste, confirmação e ativação pelo HTTP; token fora de resposta, trace, trilha e cofre |
| TEST-262 | `test_sources_permissions_external_host_and_body_validation` | `tests/integration/test_dashboard_fontes.py` | seguranca | 403 sem permissão, 400 para corpo não objeto, host externo só pelo administrador, credencial desvinculada |
| TEST-263 | `test_spreadsheet_uploads_history_and_off_model_activation` | `tests/integration/test_dashboard_fontes.py` | integracao | envio no modelo e fora dele, histórico, planilha fora do modelo entendida, confirmada e ativada |
| TEST-264 | `fontes: cadastrar o ERP, testar, entender, ajustar, confirmar, ativar e fechar o mês sobre ele` | `web/e2e/fontes.spec.ts` | interface | no navegador: aba Fontes de ponta a ponta; o token nunca aparece |
| TEST-265 | `fontes: modelos para baixar, envio de planilha e histórico; host externo só pelo administrador` | `web/e2e/fontes.spec.ts` | interface | modelos, envio e histórico; só o administrador libera host externo |
| TEST-400 | `segundo fator: ativar mostra o segredo e os códigos uma vez e a entrada passa a ter dois passos` | `web/e2e/avancado.spec.ts` | interface | no navegador: ativação com TOTP calculado no teste; segredo e códigos fora da página depois; senha abre só o pedido do código; código errado recusado com erro genérico |
| TEST-401 | `segundo fator: código de recuperação entra uma vez só e cinco códigos errados devolvem ao início` | `web/e2e/avancado.spec.ts` | interface | código de recuperação vale uma vez; as tentativas que restam vêm do servidor; a quinta recusa volta ao usuário e senha |
| TEST-402 | `segundo fator: novos códigos de recuperação e desativação pela própria pessoa` | `web/e2e/avancado.spec.ts` | interface | códigos novos invalidam os antigos; desativar pede um código válido; a entrada volta a um passo |
| TEST-403 | `política que exige o segundo fator leva a conta sem ele à ativação e só depois libera o escritório` | `web/e2e/avancado.spec.ts` | interface | política ligada pela CLI: quem entra e quem já estava dentro caem na ativação; a API nega com IAM-08; ativado, o escritório abre |
| TEST-404 | `chave de LLM no cofre: definir, ver que há chave e remover, sem o valor aparecer em lugar nenhum` | `web/e2e/avancado.spec.ts` | interface | só com PERM-MOD-SEGREDOS; situação por provedor; valor fora das respostas, do HTML, do console e da trilha |
| TEST-405 | `troca de empresa: seletor só para quem tem mais de uma, empresa ativa inequívoca e dados isolados` | `web/e2e/avancado.spec.ts` | interface | empresas e escopo criados pela CLI; escolha na entrada; a troca recarrega estado e fluxo de eventos; nada cruza |
| TEST-406 | `demonstração guiada: abre por opção, dispara os comandos de cada passo e fecha sem mudar o escritório` | `web/e2e/demo.spec.ts` | interface | desligada por padrão; fechamento, veto, agente desligado (reenvio e falha) e ataque recusado disparados pelo roteiro; fechada, o escritório funciona igual |
| TEST-407 | `demonstração guiada respeita as permissões: o auditor lê o roteiro, mas não dispara comandos` | `web/e2e/demo.spec.ts` | interface | botões de comando desligados com o motivo; o servidor nega o comando forçado |
| TEST-408 | `test_own_second_factor_status_and_new_recovery_codes` | `tests/integration/test_dashboard_acesso_avancado.py` | integracao | GET /api/2fa e POST /api/2fa/recuperacao: situação, códigos novos, antigos inválidos, trilha sem os códigos |
| TEST-409 | `test_second_step_reports_remaining_attempts_until_the_pre_session_ends` | `tests/integration/test_dashboard_acesso_avancado.py` | integracao | a recusa do código diz quantas tentativas restam; na quinta a pré-sessão acaba |
| TEST-410 | `test_vault_route_tells_where_each_llm_key_comes_from` | `tests/integration/test_dashboard_acesso_avancado.py` | integracao | por provedor: ambiente, cofre ou nenhuma; o valor nunca sai |
| TEST-420 | `test_late_delivery_of_an_earlier_message_does_not_hide_a_lost_final_answer` | `tests/e2e/test_caos.py` | robustez | com atraso de entrega de 3 a 6 ticks e perda, toda solicitação recebe resposta e nenhum invariante é violado |
| TEST-421 | `test_lost_human_decision_notice_is_redelivered_so_recurrence_is_still_refused` | `tests/e2e/test_approval_gate.py` | seguranca | aviso de waiver perdido é reentregue: a reincidência segue barrada (POL-06) e há um ticket por veto |
| TEST-422 | `test_learning_only_counts_evidence_from_a_deterministic_source` | `tests/e2e/test_aprendizado_compromisso.py` | seguranca | texto livre, fonte de proponente ou vazia não contam como evidência no aprendizado |
| TEST-423 | `test_scenario_options_the_data_cannot_support_give_a_message_not_a_traceback` | `tests/integration/test_acesso_cli.py` | robustez | combinação de cenário, porte e segmento que os dados não comportam sai com mensagem e código 2 |
| TEST-430 | `test_brute_force_through_disable_route_locks_the_second_factor_and_needs_the_password` | `tests/integration/test_segundo_fator_forca_bruta.py` | seguranca | segundo fator com contador por conta, bloqueio e senha exigida |
| TEST-431 | `test_new_pre_sessions_do_not_renew_the_attempts_and_parallel_guesses_respect_the_limit` | `tests/integration/test_segundo_fator_forca_bruta.py` | seguranca | segundo fator com contador por conta, bloqueio e senha exigida |
| TEST-432 | `test_lock_holds_for_fifteen_minutes_counts_activation_and_only_a_correct_code_resets` | `tests/integration/test_segundo_fator_forca_bruta.py` | seguranca | segundo fator com contador por conta, bloqueio e senha exigida |
| TEST-433 | `test_sources_of_one_company_cannot_be_listed_activated_removed_downloaded_or_overwritten_by_another` | `tests/integration/test_fontes_por_empresa.py` | seguranca | fontes, planilhas e credenciais isoladas por empresa |
| TEST-434 | `test_forged_backup_never_writes_outside_the_destination_and_malformed_ones_are_refused` | `tests/integration/test_backup_seguro.py` | seguranca | restauração validada antes de gravar; cofre viaja no pacote de chaves |
| TEST-435 | `test_backup_carries_the_vault_and_the_restored_install_keeps_2fa_llm_key_and_connector_credential` | `tests/integration/test_backup_seguro.py` | seguranca | restauração validada antes de gravar; cofre viaja no pacote de chaves |
| TEST-436 | `test_confirmed_mapping_stops_counting_when_the_source_renames_a_column_or_changes_the_unit` | `tests/integration/test_mapeamento_impressao.py` | seguranca | mapeamento confirmado perde a validade quando a fonte muda de coluna ou de escala |
| TEST-437 | `test_open_dashboard_does_not_keep_an_idle_session_alive` | `tests/integration/test_fluxo_eventos_acesso.py` | seguranca | fluxo de eventos reconfere sessão, permissão e empresa e não conta como atividade |
| TEST-438 | `test_stream_closes_when_the_account_loses_the_company_or_the_permission` | `tests/integration/test_fluxo_eventos_acesso.py` | seguranca | fluxo de eventos reconfere sessão, permissão e empresa e não conta como atividade |
| TEST-439 | `test_company_size_comes_from_the_registry_and_an_operator_cannot_change_it` | `tests/integration/test_empresa_porte_simulacao.py` | seguranca | porte vem do cadastro da empresa; uma simulação por empresa |
| TEST-440 | `test_simultaneous_requests_create_a_single_simulation_per_company` | `tests/integration/test_empresa_porte_simulacao.py` | seguranca | porte vem do cadastro da empresa; uma simulação por empresa |
| TEST-441 | `test_delegation_is_usable_live_and_does_not_cross_companies` | `tests/integration/test_aprovacao_e_acesso_dsm4.py` | seguranca | delegação ao vivo, dupla aprovação por pessoas distintas, veto sem exposição, senha e cofre |
| TEST-442 | `test_delegation_made_in_one_company_is_refused_in_another` | `tests/integration/test_aprovacao_e_acesso_dsm4.py` | seguranca | delegação ao vivo, dupla aprovação por pessoas distintas, veto sem exposição, senha e cofre |
| TEST-443 | `test_double_approval_needs_two_real_people_and_a_still_valid_endorsement` | `tests/integration/test_aprovacao_e_acesso_dsm4.py` | seguranca | delegação ao vivo, dupla aprovação por pessoas distintas, veto sem exposição, senha e cofre |
| TEST-444 | `test_veto_without_exposure_fails_closed` | `tests/integration/test_aprovacao_e_acesso_dsm4.py` | seguranca | delegação ao vivo, dupla aprovação por pessoas distintas, veto sem exposição, senha e cofre |
| TEST-445 | `test_password_change_revokes_other_sessions_and_wrong_current_password_counts` | `tests/integration/test_aprovacao_e_acesso_dsm4.py` | seguranca | delegação ao vivo, dupla aprovação por pessoas distintas, veto sem exposição, senha e cofre |
| TEST-446 | `test_burst_of_anonymous_logins_does_not_hold_the_registry_lock` | `tests/integration/test_aprovacao_e_acesso_dsm4.py` | seguranca | delegação ao vivo, dupla aprovação por pessoas distintas, veto sem exposição, senha e cofre |
| TEST-447 | `test_infinite_price_is_refused_and_a_tampered_vault_answers_503` | `tests/integration/test_aprovacao_e_acesso_dsm4.py` | seguranca | delegação ao vivo, dupla aprovação por pessoas distintas, veto sem exposição, senha e cofre |
| TEST-448 | `test_excel_mcp_server_answers_malformed_requests_with_json_rpc_errors_and_keeps_serving` | `tests/integration/test_mcp_excel_robusto.py` | robustez | servidor MCP de Excel responde erro JSON-RPC e segue atendendo |
| TEST-449 | `test_write_accepted_by_the_erp_with_an_invalid_reread_is_recorded_as_applied_and_never_repeated` | `tests/e2e/test_escrita_sem_confirmacao.py` | robustez | correção aplicada com releitura inválida é registrada como aplicada e não se repete |
