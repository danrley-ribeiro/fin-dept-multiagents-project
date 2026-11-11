# Revisão pós-feedback da DSM2

Cada ponto do feedback, o que foi feito e o teste que o reproduz. Os testes são do tipo
adversarial: **repetem o ataque** e verificam que ele é rejeitado, auditado e que nada muda.

## Falhas relatadas

| Feedback | Causa | Correção | Teste que reproduz o ataque |
|---|---|---|---|
| `decisao_humana` de remetente inexistente liberou e publicou o fechamento vetado | canal livre (`protocol=None`) sem identidade, sem vínculo com o veto | canal livre removido; remetente precisa estar registrado e apresentar a credencial; decisão só pelo PROT-APR, validada pelo SVC-POL | `test_forged_human_decision_from_unknown_sender_is_rejected` |
| transição local atribuída a identificador não autorizado mudou a FSM | `advance` aceitava qualquer `actor` | `advance` exige credencial, participação e papel listado em `eventos_locais` | `test_local_transition_by_unauthorized_identity_is_rejected` |
| resposta de protocolo para quem não participava da conversa foi aceita | só o remetente era conferido | o destinatário precisa ser a outra ponta da conversa e ter papel participante do protocolo | `test_reply_to_non_participant_receiver_is_rejected` |
| solicitação sem campos obrigatórios gerou `KeyError` e parou a execução | conteúdo sem esquema | esquema por performativo no barramento; exceção de agente isolada (`erro_agente` + resposta explícita) | `test_malformed_request_does_not_crash_simulation`, `test_agent_exception_is_isolated_and_answered` |
| a suíte não detectava essas violações | testes só nominais e de FSM | 75 testes novos, incluindo os adversariais e um cenário com 14 ataques | `test_adversarial_scenario_rejects_every_attack` |

## Recomendações para a DSM3

| Recomendação | O que foi feito | Onde |
|---|---|---|
| Validar remetente, destinatário, papel, conversação e performativo | pipeline de 7 etapas no barramento; emissores, eventos locais e esquemas em `models/protocols.yaml` | {doc}`protocolos`, `core/bus.py` |
| Transições internas só pelo participante autorizado | idem, para `advance` | `test_local_transition_by_unauthorized_identity_is_rejected` |
| Decisão humana vinculada à solicitação, ao veto e ao aprovador, com política explícita e auditoria | ticket do SVC-POL com hash do veto, aprovador designado, prazo e uso único; POL-01 a POL-08 | {doc}`seguranca`, `services/politica.py` |
| Validação de esquemas para mensagens malformadas não interromperem a simulação | `core/schema.py` + isolamento de erros no barramento | `test_malformed_request_does_not_crash_simulation` |
| Testes adversariais de falsificação, duplicidade, atraso e reutilização | falsificação (5 testes), duplicidade, atraso, reutilização entre ciclos, papel, SoD, justificativa, adulteração de conteúdo e de trace | {doc}`testes` |
| Concluir memória persistente | SVC-MEM: só decisão humana vira memória, com proveniência, retenção, pseudônimos e arquivo persistente | {doc}`memoria` |
| Approval Gate formal | PROT-APR implementado com allow/deny/require_approval, approve, reject, timeout e execute | {doc}`protocolos` |
| Mecanismos de proteção de informações | redaction fail-closed em todo registro e na memória; credenciais fora do trace; JSONL com hash encadeado (`verificar`) | {doc}`seguranca` |
| Demais funcionalidades previstas, mantendo o modo offline | LLM opcional do AG-REL (SVC-MOD) com mocks offline, validação numérica, logs de prompt e custo, cota | {doc}`llm` |

## Revisão interna antes da entrega

Uma bateria de ataques escrita fora da suíte (as quatro falhas do feedback em todas as
variações: todos os eventos locais de todas as conversas, respostas para todos os agentes,
decisões forjadas por três canais, reutilização e duplicidade) não encontrou nada aceito
indevidamente. Encontrou três pontos, todos corrigidos:

| Achado | Correção | Teste |
|---|---|---|
| competência com tipo certo, mas valor absurdo (`2026-99`, `xx`) era aceita; `xx` gerava exceção isolada no AG-ORC | formato `AAAA-MM` (mês 01 a 12) no esquema de PROT-SOL, PROT-DEL, PROT-CMP e PROT-APR | `test_invalid_period_or_unknown_entity_is_refused` |
| entidade desconhecida era processada e publicada | `refuse` do Orquestrador antes de delegar (e competência sem dados no modo planilha) | idem |
| API do dashboard aceitava POST de qualquer origem | `Host`/`Origin` só loopback e token de sessão nos POST | `test_dashboard_mutations_require_session_token` |

Também alinhamos os scripts de inicialização ao `pyproject.toml` (Python 3.11+).

## Correção simulada (avaliador independente)

Antes da entrega, um avaliador independente refez a correção com o método do professor: suíte,
cenários, reprodução do experimento (byte a byte) e **ataques próprios**, escritos sem olhar os
testes do grupo. Ele encontrou problemas da mesma família fora dos caminhos protegidos; todos
foram corrigidos e os scripts dele, rodados de novo sem alteração, não passam mais:

| Achado do avaliador | Gravidade | Correção | Teste |
|---|---|---|---|
| gateway MCP confiava no nome declarado (leitura fora da allowlist; terceiro executava a correção aprovada) | grave | `Agent.ferramenta` envia a credencial; gateway autentica; barramento guarda só hashes | `test_gateway_rejects_declared_identity_without_credential` |
| approve perdido ou conteúdo não serializável deixavam a solicitação sem resposta | grave | hash calculado antes de qualquer efeito; prazo também em `APROVADA`; estado inesperado vira bloqueio | `test_lost_approval_never_leaves_request_without_answer`, `test_non_serializable_content_is_rejected_before_any_side_effect` |
| reserva do período expirava durante a espera humana (dois fechamentos do mesmo mês) | grave | reserva renovada até o prazo do ticket; não publica sem a reserva | `test_period_lock_is_renewed_while_waiting_for_approver` |
| memória aceitava identidade declarada, ticket rejeitado, arquivo editado; guardava nomes | moderado | visão com token, ticket compatível, assinatura HMAC, validação ao carregar, sem texto livre | `test_memory_rejects_forged_identity_and_mismatched_ticket`, `test_tampered_memory_file_is_discarded_on_load` |
| trace não detectava corte do fim nem cadeia recalculada; replay aceitava trace sem hashes | moderado | selo final com HMAC; replay exige `--sem-verificar` | `test_trace_truncation_and_recomputed_chain_are_detected` |
| comandos malformados derrubavam a thread do dashboard | moderado | tipos validados (400) e laço protegido | `test_malformed_dashboard_commands_do_not_kill_the_simulation` |
| teste do token instável no Windows | moderado | servidor lê o corpo antes de responder 403 | `test_dashboard_mutations_require_session_token` (15/15) |
| redaction ignorava segredo não-texto, CNPJ, telefone; competência `0001-01`; justificativa `aaaaaaaaaa`; PROT-APR terminava em `APROVADA` | menor | redaction por nome de campo e padrões BR; ano 2000–2099; POL-04 com conteúdo; waiver fecha com `execute` | `test_redaction_covers_non_text_secrets_and_brazilian_ids`, `test_waiver_justification_must_have_content` |

Na **recorreção** da versão corrigida, o avaliador deu 8,1 (antes 7,3), confirmou os itens acima
e apontou os pontos abaixo, também corrigidos:

| Achado da recorreção | Correção | Teste |
|---|---|---|
| apagar ou corromper a memória liberava novo waiver; chave HMAC ao lado do arquivo | selo do arquivo inteiro com contador; chave e contador fora da pasta de dados; memória comprometida falha fechada (sem waiver) | `test_memory_removal_corruption_or_rollback_fails_closed`, `test_memory_key_and_counter_live_outside_the_data_folder` |
| ids de memória duplicados | id = maior existente + 1 | `test_memory_ids_stay_unique` |
| decisão no último tick aceita e depois expirada | recusada explicitamente (POL-08) se não puder ser entregue no prazo | `test_decision_that_cannot_be_delivered_in_time_is_rejected` |
| servidor lia o corpo antes de autenticar; token não-ASCII gerava exceção | autentica antes, leitura com tempo limite, comparação em bytes | `test_dashboard_authenticates_before_reading_the_body` |
| CPF/CNPJ sem máscara em texto livre | padrão de 11/14 dígitos | `test_redaction_catches_unmasked_documents_in_free_text` |
| trace não verificável em outra máquina (acusava adulteração) | âncora pública reproduzível (`--ancora`) e mensagem que distingue outra chave | `test_trace_anchor_verifies_without_the_authors_key` |

A crítica sobre o experimento (variância zero entre as seeds, baseline sem as mesmas funções)
está registrada em {doc}`limitacoes` e é o foco da DSM4.

## Ressalva sobre a comparação experimental

O professor observou que o baseline centralizado foi construído **sem** veto e correção, e
que parte da vantagem vem dessa diferença, não do paradigma. Concordamos: a comparação da
DSM2 e a reexecução da DSM3 ({doc}`coordenacao`) medem a **arquitetura completa contra um
workflow mínimo**, não SMA contra centralizado em igualdade de funções. Para a DSM4, o plano é
um workflow centralizado **funcionalmente equivalente** (mesmas regras de veto, correção e
aprovação, executadas em sequência por um único controlador), além de falhas combinadas,
portes e parâmetros variados, latência e custo de coordenação ({doc}`limitacoes`).
