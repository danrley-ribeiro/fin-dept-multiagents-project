# Corretude e robustez: segurança das decisões

## Política de aprovação (SVC-POL)

Cada regra tem um id que aparece no motivo da rejeição e no registro `politica` do trace.

| Regra | Conteúdo | Onde é aplicada |
|---|---|---|
| POL-01 | toda liberação de veto exige aprovação humana (REQUIRE_APPROVAL); a proposta tem de ser idêntica ao ticket emitido | emissão do ticket; validador do `propose-action` |
| POL-02 | só o aprovador designado decide, e só o que o cadastro dele permite (ex.: analista corrige ou bloqueia, não concede waiver) | validador do `approve`/`reject` |
| POL-03 | quem criou ou aprovou um lançamento vetado não decide sobre ele (segregação de funções da própria aprovação) | idem, com os `envolvidos` que o AG-CIN informa no veto |
| POL-04 | waiver exige justificativa com pelo menos 10 caracteres | idem |
| POL-05 | correção aprovada só contém correções sugeridas pelo AG-CIN; o AG-CIN recebe exatamente as executadas | idem; gateway (`autorizar_efeito`); validador do `correcao` |
| POL-06 | achado crítico reincidente após waiver anterior do mesmo padrão (memória) não admite novo waiver | emissão do ticket |
| POL-07 | sem opção de liberação restante, a ação é negada (DENY) e a publicação fica bloqueada | emissão e classificação |
| POL-08 | ticket de uso único: um veto, uma vez, no prazo, com o hash dos achados apresentados; o prazo é conferido no instante previsto de entrega da decisão | validadores do PROT-APR e do PROT-CMP |
| POL-09 (v0.5.0) | com o SVC-IAM ligado, a decisão leva o atestado de sessão de uma pessoa autenticada: sem ele, forjado, de outra decisão ou ticket, de sessão revogada ou expirada, repetido ou de quem não é aprovador, é recusada | validador do `approve`/`reject` |
| POL-13 (v0.5.0) | quem fez a solicitação não decide sobre ela; no porte com controle compensatório registrado (micro), a decisão passa e o controle fica anotado | idem |

Com o SVC-IAM ligado, **POL-02** e **POL-03** passam a conferir a pessoa real: o cargo da conta
define o que ela decide, e o vínculo da conta com a pessoa do ERP diz se ela participou de um
lançamento vetado. Sem o SVC-IAM (cenários em lote da primeira versão), valem POL-01 a POL-08 com
o cadastro por identidade.

O ticket guarda solicitação, conversa vetada e ciclo, hash do veto, opções abertas e negadas
(com a regra), aprovador designado, prazo, decisão, quem decidiu (agente, pessoa, cargo),
justificativa, correções aprovadas e executadas e se já foi consumido. A memória e o
relatório citam o id do ticket.

## Ataques testados

O cenário `ataque_decisao_forjada` (plantio de alçada, aprovador em silêncio) dispara, um tick
depois da abertura do PROT-APR, a sequência de `src/fin_mas/env/ataques.py`. Resultado
(`python -m fin_mas run --scenario ataque_decisao_forjada`):

| # | Ataque | Barrado em | Motivo registrado |
|---|---|---|---|
| 1 | `decisao_humana` sem protocolo, de remetente inexistente (feedback) | autenticação | remetente desconhecido: 'FANTASMA' |
| 2 | `approve` em nome do APR, sem a credencial dele | autenticação | credencial ausente ou inválida para APR |
| 3 | `approve` enviado pelo AG-REL | papel | ROLE-REL não pode emitir 'approve' |
| 4 | `approve` do APR com hash de veto adulterado | política | POL-08: hash do veto não confere |
| 5 | `approve` do APR citando outro ticket | política | POL-08: não corresponde ao ticket |
| 6 | `waiver_humano` ao AG-CIN sem aprovação | política | POL-08: sem aprovação emitida |
| 7 | `advance publicar` por identificador não autorizado (feedback) | autenticação | identidade desconhecida: 'HACKER' |
| 8 | `advance publicar` pelo AG-CIN | papel | ROLE-CIN não pode aplicar 'publicar' |
| 9 | `execute` antes da aprovação | FSM | execução sem aprovação humana |
| 10 | `erp.corrigir` sem aprovação, pelo próprio Orquestrador | gateway | aprovação APR-001 está pendente (`mcp_denied`) |
| 10b | gateway chamado em nome de outro agente (AG-REL se declara AG-CIN) | gateway | identidade não autenticada (`mcp_denied`) |
| 11 | resposta a quem não é a contraparte da conversa (feedback) | destinatário | AG-RES não é a contraparte de AG-CUS |
| 12 | resposta a papel que não participa do protocolo | papel | ROLE-REL não participa do PROT-CMP |
| 13 | pedido sem campos obrigatórios (feedback) | esquema | campo obrigatório ausente: entidade; competencia |

Resultado: 14 tentativas, **0 aceitas** (MET-15), 12 `rejected` + 2 `mcp_denied` no trace,
nenhum `erro_agente`; o ticket expira no prazo e o fechamento termina **bloqueado, sem
publicar**. Os testes de {doc}`testes` repetem cada ataque isoladamente e cobrem ainda
duplicidade, atraso, reutilização entre ciclos, papel do aprovador, SoD, justificativa,
correção fora das sugeridas, personificação no registro e adulteração de conteúdo e de trace.

## Proteção de informações

- **Redaction fail-closed (NORM-06):** todo registro de auditoria passa por `services/redacao.py`
  antes de ser guardado: campos com nome de segredo (senha, token, api_key, credencial…) e CPF,
  e-mail, chaves de API e tokens Bearer em texto são substituídos. Se a sanitização falhar
  (tipo desconhecido, estrutura profunda), o conteúdo é recusado e fica só um marcador
  `redacao: recusada`. Na memória, a falha recusa a gravação.
- **Credenciais:** cada identidade recebe a sua credencial no registro; o barramento guarda só o
  hash SHA-256 dela (ler o estado do barramento não permite se passar por ninguém). O gateway MCP
  e a memória também exigem prova de identidade: `Agent.ferramenta` envia a credencial ao gateway
  e a memória só aceita a visão emitida para cada agente. Um teste confere que nenhuma
  credencial aparece no JSONL gravado.
- **Minimização na memória:** pessoas viram pseudônimos estáveis (`pessoa#…`, HMAC com a chave da memória, que fica fora da pasta de dados) e nenhum texto
  livre (detalhe de correção, justificativa) é guardado; o arquivo de memória não tem nomes.
- **Memória íntegra e com falha fechada:** cada entrada é assinada com HMAC-SHA256 e o arquivo
  inteiro tem um selo HMAC sobre (contador de versão, entradas). A chave e o último contador
  ficam fora da pasta de dados (`~/.fin_mas/chaves/` ou `FIN_MAS_DIR_CHAVES`). Entrada inventada,
  alterada, removida ou malformada, arquivo corrompido ou apagado, volta a uma versão antiga e
  arquivo em outra versão do formato (ex.: v3, com pseudônimos sem chave; issue #2)
  deixam a memória **comprometida**: nada é gravado e o AG-CIN trata todo achado crítico como
  reincidente, então a política não reabre o waiver (TEST-84). A gravação exige ticket compatível: waiver aprovado para
  `waiver`, correção executada para `correcao`, rejeição para `bloqueio`, mesma competência e
  lançamento do veto.
- **Trace com cadeia de hashes e selo HMAC:** cada linha do JSONL traz `_hash` = SHA-256(hash
  anterior + registro) e a última linha é um selo com o número de registros, o hash final e um
  HMAC desses valores com a chave local do trace (`~/.fin_mas/chave_trace` ou
  `FIN_MAS_CHAVE_TRACE`, fora do repositório). `python -m fin_mas verificar trace.jsonl` acusa
  linha alterada, removida ou reordenada, corte do fim do arquivo e cadeia recalculada por quem
  não tem a chave (saída 3); o `replay` recusa trace sem cadeia, salvo com `--sem-verificar`.
  Em outra máquina, sem a chave do autor, a verificação usa a **âncora pública**: o hash final da
  cadeia, que é reproduzível (`verificar trace.jsonl --ancora <hash>`); a âncora do cenário
  adversarial está no README da entrega (TEST-88).
- **Isolamento de erros e atomicidade:** o barramento calcula o hash do conteúdo (que precisa ser
  JSON com chaves de texto) antes de qualquer efeito; uma mensagem recusada nunca deixa ticket ou
  FSM alterados. Exceção de um agente não interrompe a simulação, e todo estado de espera tem
  prazo, inclusive `APROVADA` no PROT-APR: nenhuma solicitação fica sem resposta. Comandos do
  dashboard têm os tipos validados (400) e nenhum erro derruba a thread da simulação.
- **Reserva do período durante a aprovação:** o Orquestrador renova a reserva (PROT-LCK) até o
  prazo do ticket e não publica se a perder; outro fechamento do mesmo mês é recusado.
- **Validação de domínio na entrada:** competência fora de `AAAA-MM` (ano 2000–2099, mês 01 a 12) é barrada pelo
  esquema; entidade que não é a empresa atendida, ou competência sem dados no modo planilha,
  recebe `refuse` do Orquestrador antes de qualquer delegação (TEST-72).
- **API do dashboard:** autentica antes de ler o corpo (corpo enorme sem sessão não é lido;
  leitura com tempo limite; token não-ASCII não gera exceção, TEST-90); só loopback; `Host` e
  `Origin` precisam ser `127.0.0.1`/`localhost` (bloqueia DNS rebinding e páginas de outros
  sites); desde a v0.5.0, toda rota exige a sessão de uma pessoa (cookie `HttpOnly;
  SameSite=Strict`) e a permissão da rota ou do comando, e todo POST exige ainda o cabeçalho
  `X-SMA-Token` com o token CSRF **daquela sessão** (TEST-73, {doc}`dashboard`).
- **Privacidade no LLM:** provedor externo só com consentimento explícito; o que sai leva
  pseudônimos no lugar de fornecedores, documentos, lançamentos e pessoas; chaves só no ambiente,
  nunca no trace ({doc}`llm`).

## Controle de acesso (v0.5.0)

Quem usa a plataforma é uma pessoa com conta, sob as regras IAM-01 a IAM-07 do SVC-IAM, e a
decisão humana vale pela pessoa autenticada (POL-09, POL-02, POL-03, POL-13). Detalhes, matriz de
papéis, TUI e contas de demonstração em {doc}`acesso`; decisão em
{doc}`ADR-009-identidade-e-acesso`.

O cenário `ataque_acesso` parte da posição que a primeira versão da DSM3 deixava aberta (quem
controla a caixa `APR`) e tenta 15 vezes fazer valer uma decisão sem ser a pessoa certa:
**15 de 15 recusados** (8 por POL-09, 2 por POL-02, 1 por POL-03, 1 por POL-13, 2 por IAM-05 e 2
por IAM-06; tabela completa em {doc}`acesso`). O ticket expira e nada é publicado (MET-17 = 0
aceitos).

## Modelo de ameaças

Quem ataca, o que tenta, o que impede e o teste que repete o ataque.

| Ameaça | Controle | Teste |
|---|---|---|
| Remetente inexistente ou sem credencial injeta mensagem no barramento | autenticação por identidade registrada e credencial (hash) | `test_forged_human_decision_from_unknown_sender_is_rejected`, cenário `ataque_decisao_forjada` |
| Agente emite performativo que não é do papel dele (ex.: AG-REL aprova) | `emissores` por performativo; `eventos_locais` para transições locais | `test_local_transition_by_unauthorized_identity_is_rejected` |
| Resposta para quem não participa da conversa | contraparte e papel participante | `test_reply_to_non_participant_receiver_is_rejected` |
| Identidade fora do diretório se registra com papel privilegiado e passa a delegar ou consultar | registro do barramento fechado depois da montagem do sistema; tentativa auditada | `test_unknown_identity_cannot_register_with_a_privileged_role_after_the_system_is_built` |
| Especialista estende o próprio prazo sem negociar | só o iniciador da conversa define o prazo | `test_counterpart_cannot_extend_its_own_deadline_without_negotiating` |
| Reserva de período liberada ou tomada por quem só diz o nome do dono | SVC-LCK exige a credencial do Orquestrador | `test_period_reservation_cannot_be_released_or_taken_by_naming_its_owner` |
| Conteúdo aninhado inválido de um especialista deixa o solicitante sem resposta | o Orquestrador aborta com `failure` e libera o período | `test_malformed_nested_payload_from_a_specialist_becomes_an_explicit_failure` |
| Texto de modelo com número por extenso, outra escrita, sinônimo de ação ou instrução ao leitor chega ao relatório | alfabeto restrito, números por extenso e radicais de ação recusados; texto de modelo rotulado como não verificado, depois do conteúdo determinístico | `test_adversarial_model_text_never_becomes_a_hypothesis_nor_reaches_the_report`, `test_synthesis_with_recommendations_falls_back_and_the_model_text_comes_last_and_labelled` |
| Quem configura o modelo aponta o provedor para um endereço seu e recebe a chave de API do servidor | a chave só segue para a URL do provedor ou para a lista da instalação | `test_server_api_key_is_never_sent_to_a_url_chosen_in_the_configuration` |
| Corpo HTTP que não é objeto, ou campo de tipo errado, derruba a conexão | validação do corpo e resposta 400 | `test_malformed_bodies_get_a_400_instead_of_a_dropped_connection` |
| Quem não tem conta derruba a sessão de outra pessoa errando a senha dela | o bloqueio temporário só impede novas entradas | `test_wrong_passwords_by_a_stranger_do_not_drop_the_live_session_of_the_account` |
| Conteúdo malformado derruba a simulação | esquema por performativo; erro de agente isolado | `test_malformed_request_does_not_crash_simulation` |
| Decisão forjada, reutilizada, atrasada ou de outro veto | ticket com hash do veto, uso único, prazo pela entrega prevista (POL-08) | `tests/e2e/test_approval_gate.py`, `test_deadline_check_uses_the_real_delivery_time_of_the_decision` |
| Processo local com a credencial da caixa `APR` decide em nome de alguém (lacuna da primeira versão) | atestado HMAC por sessão de pessoa (POL-09) | `test_access_attacks_are_all_rejected_and_nothing_is_published`, cenário `ataque_acesso` |
| Aprovador decide o que o cargo não permite, sobre lançamento em que participou ou sobre o próprio pedido | POL-02, POL-03 e POL-13 contra a pessoa real | `test_position_limits_which_decisions_a_person_can_take`, `test_involved_approver_is_refused_and_another_person_decides`, `test_requester_cannot_approve_their_own_request` |
| Chamada à API sem sessão ou sem permissão | sessão obrigatória (401), permissão por rota e comando (403), negado por padrão | `test_each_role_can_only_do_what_its_permissions_allow`, `test_dashboard_filters_and_auth` |
| Outro site dispara comandos (CSRF) ou DNS rebinding | cookie `SameSite=Strict`, token CSRF por sessão, `Host`/`Origin` de loopback | `test_dashboard_mutations_require_session_token` |
| Força bruta de senha | bloqueio após 5 erros por 15 min; mesma resposta para usuário inexistente (IAM-03) | `test_login_lockout_and_generic_errors` |
| Sessão roubada continua valendo depois de revogada | sessão conferida a cada requisição; SSE fechado | `test_revoked_session_stops_at_once_and_closes_the_event_stream`, `test_revoking_a_session_opened_by_the_server_drops_it` |
| Escalada de privilégio (operador vira aprovador; admin acumula aprovação; último admin removido) | `PERM-IAM-PAPEIS`, IAM-06 | `test_revoked_or_demoted_actor_cannot_keep_administering`, `test_assigning_approver_role_to_the_administrator_is_refused_with_iam06`, `test_last_administrator_cannot_be_blocked` |
| Edição, rollback ou corrida de escrita no cadastro de contas | arquivo selado com contador fora da pasta, trava entre processos; falha fechada (IAM-07) | `test_tampered_account_store_locks_everyone_out`, `test_rolled_back_account_file_is_refused`, `test_concurrent_writers_do_not_lose_updates` |
| Adulteração da trilha de acesso ou do trace | cadeia de hashes com cabeça/selo HMAC fora da pasta; âncora pública | `test_access_trail_is_listed_verified_and_tampering_is_detected`, `test_trace_truncation_and_recomputed_chain_are_detected` |
| Página do dashboard embutida ou carregando script de fora | CSP `default-src 'self'`, `frame-ancestors 'none'`, `X-Frame-Options: DENY` | `test_security_headers_and_cookie_flags` |
| LLM inventa número, propõe ação, obedece a instrução no texto livre ou responde fora do formato | proposta validada por regras (NORM-11) e texto conferido por rótulo (NORM-05); fallback | `test_rejected_llm_proposals_leave_the_result_identical`, `test_injected_note_cannot_change_classification`, `test_true_number_under_the_wrong_label_is_rejected` |
| Dados da empresa enviados a provedor externo sem autorização | consentimento explícito e pseudônimos (NORM-06) | `test_external_provider_without_consent_sends_nothing`, `test_prompt_is_pseudonymized_and_insight_restores_real_names` |
| Chave de LLM vaza para o trace ou para a interface | chave lida do ambiente na chamada, nunca registrada; INV-08 | `test_openai_provider_sends_key_in_header_and_never_in_the_trace`, `test_cli_lists_providers_without_revealing_keys` |
| Memória apagada, editada ou recolocada para liberar novo waiver | selo do arquivo com contador e chave fora da pasta; falha fechada | `test_memory_removal_corruption_or_rollback_fails_closed` |

Fora do modelo: código com acesso ao objeto Python de outro agente ou à memória do processo do
servidor (a raiz de confiança continua sendo o processo); quem tem acesso à pasta de chaves
(`~/.fin_mas/`); a máquina comprometida. O barramento é em processo e single-thread; numa versão
distribuída, a mesma checagem passaria a usar mTLS ou assinaturas por mensagem, sem mudar os
protocolos (ADR-007). Limites em {doc}`limitacoes`.

## Invariantes de segurança

`src/fin_mas/invariantes.py` confere, só a partir do trace (sem saber qual cenário rodou nem
confiar no que os agentes dizem), propriedades que precisam valer em **toda** execução, com ou
sem falhas, ataques ou LLM:

| Invariante | Propriedade |
|---|---|
| INV-01 | nenhuma publicação sai de um pacote vetado sem que o veto tenha sido tratado (correção reavaliada pelo AG-CIN ou waiver humano), e todo fechamento publicado tem parecer do AG-CIN |
| INV-02 | nenhum efeito externo (`erp.corrigir`) acontece sem uma aprovação já decidida para aquela correção, e cada correção aprovada é usada uma única vez |
| INV-03 | toda transição registrada existe na máquina de estados do protocolo |
| INV-04 | com o controle de acesso ligado, toda decisão humana aceita tem pessoa e sessão |
| INV-05 | nenhuma crença tem um proponente (regra local ou LLM) como fonte |
| INV-06 | hipótese só é confirmada ou refutada com a fonte da evidência registrada |
| INV-07 | toda solicitação recebe uma resposta explícita (resultado, recusa ou falha) |
| INV-08 | nenhum segredo conhecido aparece no trace (token de atestado, chave de API) |

```bash
python -m fin_mas invariantes trace.jsonl     # "8 invariantes, 0 violação(ões)"
python -m fin_mas cenarios --verificar        # confere os 8 em cada um dos 37 cenários
```

`test_invariant_checker_flags_a_forged_trace` confere que o verificador acusa um trace forjado.
A TUI mostra os invariantes do trace aberto na aba *Traces*.
