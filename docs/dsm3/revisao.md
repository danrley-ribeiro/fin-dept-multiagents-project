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
| a suíte não detectava essas violações | testes só nominais e de FSM | testes adversariais e um cenário com 14 ataques: 75 testes novos na entrega inicial (232 no total, 10/11/2026), 249 na tag `dsm3-base` depois da revisão do PR e da issue #2, 414 na v0.5.0 ({doc}`testes`) | `test_adversarial_scenario_rejects_every_attack` |

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

## Revisão do PR pelo coautor

O Danrley revisou o pull request da DSM3 (commit `3c4b66f`) e reproduziu cada achado com um
script sobre o código. Todos foram corrigidos conforme as sugestões dele, cada um com um teste
de regressão em `tests/e2e/test_revisao_pr.py`:

| Achado da revisão | Correção | Teste |
|---|---|---|
| decisão humana recusada pela política (ex.: POL-04) tirava a pendência antes da validação: não dava para decidir de novo e o pedido terminava `expirada`; opção não oferecida devolvia sucesso sem enviar nada | a pendência só sai depois de o barramento e o SVC-POL aceitarem a decisão; `_responder` informa quando não envia; o dashboard avisa que a pendência continua aberta, e o botão de waiver usa a mesma regra da POL-04 (`aaaaaaaaaa` não o habilita) | `test_refused_decision_keeps_pending_and_can_be_retried`, `test_option_not_offered_reports_nothing_sent_and_keeps_pending`; no dashboard, `justificativa.test.ts` e o teste de navegador "waiver exige justificativa" |
| waiver sem justificativa recebia o texto padrão e passava na POL-04: um POST sem justificativa liberava o veto e o trace atribuía ao aprovador um texto que ele não escreveu | no modo interativo, o waiver usa só o texto do humano (vazio é recusado); bloquear e corrigir sem justificativa registram "sem justificativa informada"; o texto padrão fica só no modo em lote dos cenários | `test_waiver_without_human_justification_is_refused`, `test_block_without_justification_says_none_was_given` |
| `replay` não lia trace gravado em outra máquina (não tinha `--ancora`) | `replay --ancora HASH`, como no `verificar` | `test_replay_reads_trace_from_another_machine_with_anchor` |
| a redação de CPF/CNPJ sem máscara alterava cerca de 5,5% dos hashes SHA-256 (ex.: o hash do veto no trace) | fronteira sem letras nem dígitos em volta dos 11 ou 14 dígitos | `test_redaction_keeps_hex_digests_intact` (20.000 hashes) |
| a NORM-05 aceitava número com a escala errada (`12.345,6` contra `1.234,56`) | números comparados pelo valor, lidos no formato pt-BR | `test_norm05_number_check_respects_scale` |
| pseudônimo da memória reversível por dicionário (SHA-256 sem chave) | HMAC com a chave da memória, que fica fora da pasta de dados; no trace o pseudônimo aparece como `pessoa#…`, para o hash continuar igual em qualquer máquina | `test_pseudonym_is_keyed_and_not_reversible_by_dictionary` |
| regra de competência duplicada e divergente (`1999-12` válido só na memória) | memória e dashboard usam a regra de `core/schema.py` | `test_competence_rule_is_shared` |

Arquivos de memória gravados antes desta correção têm pseudônimos no formato antigo (versão 3
do arquivo): continuam íntegros, mas não casam com os novos, então uma reincidência anterior a
esta versão não é reconhecida. Como a memória da entrega começa vazia, isso não afeta os cenários.

## Etapa v0.5.0 (12/11/2026)

Depois da tag `dsm3-base` (a versão revisada acima, com 249 testes), a DSM3 foi concluída com o
que faltava das funcionalidades previstas e com a lacuna que a própria revisão deixou exposta.

| Ponto de partida | O que foi feito | Onde |
|---|---|---|
| Qualquer processo local que lesse o token do dashboard agia como o aprovador `APR`; TEST-19 (dashboard autenticado) pendente desde a DSM1 | SVC-IAM: contas, sessões, papéis, permissões por rota e comando; decisão atestada pela pessoa (POL-09), cargo e SoD contra a pessoa real (POL-02, POL-03), quem pede não aprova (POL-13); cenário `ataque_acesso` com 15 ataques, 0 aceitos | {doc}`acesso`, {doc}`dashboard`, ADR-009 |
| AG-ORC ignorava o texto livre da planilha e o histórico | hipóteses validadas por regras, ação epistêmica, evidência determinística; motor local e LLM opcional | {doc}`cognicao`, ADR-008 |
| PROT-DEL só aceitava resultado ou falha no prazo | negociação de prazo (`propose`, `accept-proposal`, `reject-proposal`, estado `NEGOCIANDO`) | {doc}`protocolos` |
| LLM só no AG-REL e só Claude | usos por agente (síntese, hipóteses, narrativa, comentário), cinco provedores, consentimento, pseudônimos, disjuntor, conferência de números por rótulo, bancada | {doc}`llm` |
| Implantação só pelo repositório | `fin-mas instalar`, `doctor`, `serve --instalacao`; ficha do porte | {doc}`implantacao` |
| Propriedades de segurança conferidas cenário a cenário | 8 invariantes sobre qualquer trace; `cenarios --verificar` | {doc}`seguranca` |

Os 17 cenários revisados continuam no nível `basico`: as 20 colunas de métricas da comparação em
10 seeds são idênticas às da tag `dsm3-base`; os hashes dos traces mudaram só porque o registro
`meta` leva a versão do pacote (0.4.0 → 0.5.0), o que também muda a âncora do cenário
adversarial ({doc}`cognicao`).

### Pontos da correção simulada que estavam em aberto

Na 3ª rodada da correção simulada (`entregas/dsm3/USO_DE_IA.md`) ficaram cinco pontos
não corrigidos. Situação na v0.5.0:

| Ponto (gravidade) | Situação | Teste |
|---|---|---|
| a checagem do prazo da aprovação supõe entrega em um tick (menor) | **corrigido**: o barramento expõe `entrega_prevista` (agora + atraso do envio) e a POL-08 confere o prazo nesse instante | `test_deadline_check_uses_the_real_delivery_time_of_the_decision` (TEST-134) |
| `verificar --ancora` sobre trace sem cadeia devolve 1, não 3 (menor) | **corrigido**: devolve 3, com a mensagem de que a âncora não pode ser conferida | `test_verify_with_anchor_on_unchained_trace_returns_three` |
| números legítimos soltos de 11 ou 14 dígitos são redigidos como CPF/CNPJ (menor) | **mantido por decisão** (falha fechada): os testes da revisão exigem redigir, por exemplo, "chave pix 98765432100" e "doc (12345678901)", que não têm contexto de CPF nem dígito verificador válido; a parte que atingia hashes foi corrigida na revisão do PR | {doc}`limitacoes` |
| cópia íntegra da memória em outra pasta ou máquina é tratada como comprometida (moderado) | em aberto, DSM4 | {doc}`limitacoes` |
| duas execuções simultâneas sobre o mesmo arquivo de memória perdem entradas (menor) | em aberto, DSM4 (o cadastro de acesso já usa trava entre processos; a memória ainda não) | {doc}`limitacoes` |

### Correção simulada da v0.5.0 (4ª rodada, 12 e 13/11/2026)

Antes do pacote, um avaliador independente (agente de IA sem acesso ao plano nem à conversa de
desenvolvimento, só leitura) avaliou a v0.5.0 contra a rubrica da DSM3 e fez testes adversariais
próprios. Confirmou as quatro falhas do feedback da DSM2 como corrigidas, não conseguiu publicar
com veto pendente nem executar `erp.corrigir` sem aprovação por nenhum caminho, e deu **7,2** ao
estado que avaliou. Os achados abaixo foram reproduzidos por ele e corrigidos depois; **não houve
nova avaliação depois das correções**, então a nota não foi refeita.

| Achado (gravidade) | Correção | Teste |
|---|---|---|
| C1: identidade fora do diretório se registrava com papel privilegiado (ROLE-ORQ, ROLE-RES), delegava ao AG-CIN, lia o veto e encurtava o prazo de uma avaliação legítima (crítico) | com o sistema montado o registro do barramento é fechado: só identidades do diretório; a tentativa é auditada | TEST-141 |
| C2: a validação do texto do LLM era contornável (número por extenso, numeral de outra escrita, sinônimo e flexão de ação, homógrafo, caractere invisível, instrução ao leitor, marcador com rótulo trocado) e o texto saía no relatório publicado junto de "confirmada por AG-CIN" (crítico) | só letras latinas e pontuação comum (NFKC estável, sem caracteres de formato); números por extenso e radicais de ação e de instrução recusados; valor resolvido sai com a grandeza ao lado (`R$ … (realizado)`); o texto de modelo sai rotulado "texto não verificado", separado do desfecho; a síntese do AG-REL passou para o fim do relatório, rotulada, e recomendação na síntese cai no template | TEST-142, 143, 144 |
| M1: a chave de API do servidor seguia para uma `base_url` escolhida por quem configura o modelo (moderado) | a chave só segue para a URL padrão do provedor ou para uma URL da lista `FIN_MAS_LLM_URLS_CONFIAVEIS`, definida na instalação | TEST-145 |
| M2: o especialista estendia o próprio prazo com `reply_by` numa resposta (moderado) | só o iniciador da conversa define ou estende o prazo | TEST-146 |
| M3: conteúdo aninhado inválido de um especialista deixava o solicitante sem resposta e o período reservado (moderado) | o Orquestrador aborta com `failure` e libera a reserva | TEST-147 |
| M4: oito exceções não tratadas no servidor HTTP, três sem autenticação (moderado) | todo corpo é validado como objeto JSON; campo de tipo errado devolve 400 | TEST-148 |
| M5: cinco senhas erradas de quem não tem conta derrubavam a sessão viva da pessoa (moderado) | o bloqueio temporário só impede novas entradas; a sessão aberta continua | TEST-149 |
| M6: SVC-LCK aceitava liberar e tomar a reserva só com o nome do dono (moderado) | reserva, renovação e liberação exigem a credencial do Orquestrador | TEST-150 |
| M8: verificador de invariantes com um falso positivo (reenvio do pedido de parecer) e dois falsos negativos (moderado) | aviso de prazo do PROT-CMP não conta como transição; INV-01 exige parecer do AG-CIN em todo fechamento publicado; INV-02 confere uso único da correção | TEST-151 |
| m1: operador sem a permissão de modelos reiniciava com outro nível de cognição; agente inexistente aceito no comando (menor) | o reinício com mudança de cognição exige `PERM-MOD-CONFIG`; agente desconhecido devolve 400 | TEST-153 |
| m2: identificador não textual ou conteúdo não copiável levantava exceção sem registro (menor) | rejeição com registro `rejected` | TEST-152 |

Continuam em aberto, declarados em {doc}`limitacoes`: o prazo compartilhado entre solicitantes no
AG-ORC; o pedido (`solicitado_por`) sem atestado no barramento (M7); o fluxo de eventos ao vivo
visível a quem vê a simulação (M9, assumido e descrito em `PERM-SIM-VER`); o baseline sem as
mesmas funções (M10, DSM4); esquemas de conteúdo só no primeiro nível; a raiz de confiança das
chaves no disco; a POL-04 só léxica; lacunas da redação; AG-CUS e AG-REL reativos.

## Ressalva sobre a comparação experimental

O professor observou que o baseline centralizado foi construído **sem** veto e correção, e
que parte da vantagem vem dessa diferença, não do paradigma. Concordamos: a comparação da
DSM2 e a reexecução da DSM3 ({doc}`coordenacao`) medem a **arquitetura completa contra um
workflow mínimo**, não SMA contra centralizado em igualdade de funções. Para a DSM4, o plano é
um workflow centralizado **funcionalmente equivalente** (mesmas regras de veto, correção e
aprovação, executadas em sequência por um único controlador), além de falhas combinadas,
portes e parâmetros variados, latência e custo de coordenação ({doc}`limitacoes`).
