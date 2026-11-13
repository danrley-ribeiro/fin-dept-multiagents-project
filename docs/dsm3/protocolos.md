# Comunicação e protocolos

## Envelope e finalidade de cada mensagem

Toda mensagem é `m = <remetente, destinatário, performativo, conteúdo, ontologia, conversation_id>`
mais `reply_by` (prazo no relógio lógico), como na DSM1. Na DSM3, cada protocolo declara em
`models/protocols.yaml`, além da FSM:

- `participantes`: papéis que podem estar numa conversa do protocolo;
- `emissores`: para cada performativo, os papéis que podem enviá-lo (a **finalidade** da mensagem
  fica amarrada a quem tem a responsabilidade: só o ROLE-CIN veta, só o ROLE-APR aprova);
- `eventos_locais`: transições sem mensagem e quem pode aplicá-las;
- `esquemas`: campos obrigatórios e tipos do conteúdo de cada performativo (`?` = opcional).

| Protocolo | Finalidade | Emissores (performativo → papel) | Eventos locais |
|---|---|---|---|
| PROT-SOL | pedido da liderança e resposta final ou falha explícita | `request` → SOL; `agree`, `refuse`, `not-understood`, `inform`, `failure` → ORQ | — |
| PROT-DEL | delegar uma subtarefa do DAG com prazo; o especialista pode negociar o prazo | `request`, `accept-proposal`, `reject-proposal` → ORQ; `agree`, `refuse`, `inform`, `failure`, `propose` → especialistas | — |
| PROT-QRY | especialista consulta outro sem acessar suas regras | `query-ref` → RES, ORC; respostas → CUS, ORC, CIN | — |
| PROT-CMP | parecer de conformidade com veto | `request`, `correcao`, `waiver_humano`, `prazo_esgotado` → ORQ; `conforme`, `nao_conforme_nao_critico`, `veto` → CIN | `publicar` → ORQ |
| PROT-APR | reter ação restrita até decisão humana, tomada por uma pessoa autenticada | `propose-action` → ORQ; `approve`, `reject` → APR (com `atestado` da pessoa) | `allow`, `deny`, `require_approval` → SVC-POL; `execute` → ORQ |
| PROT-LCK | exclusão mútua do período | chamada local ao SVC-LCK | `reserve`, `release`, `ttl_expirado` |

## Validação no barramento

```{mermaid}
flowchart LR
  A[send] --> B{remetente registrado<br/>e credencial?}
  B -- não --> R[rejected: autenticacao]
  B -- sim --> C{envelope válido?<br/>ontologia, reply_by}
  C -- não --> R2[rejected: esquema]
  C -- sim --> D{destinatário<br/>registrado?}
  D -- não --> R3[rejected: destinatario]
  D -- sim --> E{papel pode emitir?<br/>destinatário participa?}
  E -- não --> R4[rejected: papel]
  E -- sim --> F{esquema do<br/>performativo?}
  F -- não --> R5[rejected: esquema]
  F -- sim --> G{conversa: abertura,<br/>contraparte, FSM}
  G -- não --> R6[rejected: conversa / fsm]
  G -- sim --> H{validadores<br/>do domínio SVC-POL}
  H -- não --> R7[rejected: politica]
  H -- sim --> I[FSM avança · send/open auditado · entrega agendada com hash]
```

- A recusa levanta `MensagemRejeitada` (subclasse de `ProtocolViolation`) e grava `rejected`
  com etapa, motivo e o envelope — nunca altera conversa nem agenda entrega.
- Resposta após `reply_by` continua sendo **descartada** (`discard`), não rejeitada: não é
  ataque, é atraso.
- Na entrega, o hash do conteúdo é conferido (alteração após o envio → `drop` por integridade)
  e o destinatário recebe uma cópia própria.
- Se o agente levanta exceção ao tratar a mensagem, o barramento registra `erro_agente` e
  chama `on_error`, que responde `not-understood`, `refuse` ou `failure` quando a FSM permite.

## Approval Gate (PROT-APR)

```{mermaid}
stateDiagram-v2
  [*] --> CRIADA
  CRIADA --> PROPOSTA: propose-action (ORQ)
  PROPOSTA --> PENDENTE: require_approval (SVC-POL)
  PROPOSTA --> NEGADA: deny (SVC-POL)
  PROPOSTA --> EXECUTADA: allow (SVC-POL)
  PENDENTE --> APROVADA: approve (APR)
  PENDENTE --> REJEITADA: reject (APR)
  PENDENTE --> EXPIRADA: timeout (reply_by)
  APROVADA --> EXECUTADA: execute (ORQ)
  APROVADA --> EXPIRADA: timeout (aprovada, não executada)
  NEGADA --> [*]
  REJEITADA --> [*]
  EXPIRADA --> [*]
  EXECUTADA --> [*]
```

Transições inválidas que viram testes negativos: `execute` em PENDENTE (execução sem
aprovação), `approve` em NEGADA, APROVADA (duplicada), EXECUTADA (reutilizada) e EXPIRADA
(atrasada).

```{mermaid}
sequenceDiagram
  participant CIN as AG-CIN
  participant ORQ as AG-ORQ
  participant POL as SVC-POL
  participant APR as Aprovador (humano)
  participant MCP as Gateway MCP
  CIN->>ORQ: veto (achados, opções, correções sugeridas, envolvidos) [PROT-CMP]
  ORQ->>POL: emitir ticket (hash do veto, aprovador, prazo, opções pela política)
  ORQ->>APR: propose-action APR-001 [PROT-APR]
  POL-->>POL: require_approval (evento local)
  APR->>ORQ: approve {aprovacao, solicitacao, veto(hash), decisao=corrigir, correcoes}
  Note over POL: validado no barramento: POL-02..05, uso único
  ORQ->>MCP: erp.corrigir (aprovacao=APR-001, lançamento, ação)
  MCP->>POL: autorizar_efeito → registrar_execucao
  ORQ-->>ORQ: execute (evento local)
  ORQ->>CIN: correcao {aprovacao=APR-001, correcoes} [PROT-CMP]
  Note over POL,CIN: SVC-POL consome o ticket, e o AG-CIN percebe o ERP de novo e reconsidera
  CIN->>ORQ: conforme
```

Sem decisão no prazo, o `timeout` expira o ticket e o Orquestrador envia `prazo_esgotado`
(`decisao: expirada`) ao AG-CIN: a publicação fica bloqueada. Com `reject`, o mesmo, com
`decisao: bloquear`. Com `deny` (nenhuma liberação aberta pela política), o bloqueio é imediato.

### Decisão atestada pela pessoa (v0.5.0)

Com o SVC-IAM ligado (servidor do dashboard e cenários de acesso), o `approve` e o `reject` levam
um campo opcional `atestado` (`dict`) no esquema: `{pessoa, sessao, nonce, token}`, emitido pelo
servidor para a sessão da pessoa que decidiu ({doc}`acesso`). O esquema recusa atestado com tipo
errado já na etapa de esquema; a política confere o resto (POL-09: token, sessão viva, nonce
inédito, papel de aprovador; POL-02 e POL-03 contra a pessoa real; POL-13 contra quem pediu).
O ticket decidido guarda `aprovado_por = {agente, pessoa, titulo, sessao}`. A checagem do
prazo (POL-08) usa o instante previsto de entrega da decisão (`entrega_prevista` do barramento:
agora + atraso do envio), não um tick fixo (TEST-134).

```{mermaid}
sequenceDiagram
  participant P as Pessoa (navegador)
  participant S as Servidor (SVC-IAM)
  participant APR as caixa APR
  participant ORQ as AG-ORQ
  participant POL as SVC-POL
  P->>S: POST /api/comando decidir (cookie + X-SMA-Token)
  S->>S: sessão viva? PERM-APR-DECIDIR?
  S->>APR: decisão + atestado HMAC(ticket, veto, decisão, corpo, pessoa, sessão, nonce)
  APR->>ORQ: approve {..., atestado} [PROT-APR]
  Note over POL: POL-09 atestado · POL-02 cargo · POL-03 envolvido · POL-13 solicitante · POL-08 prazo
  POL-->>ORQ: aceita (aprovado_por: pessoa, sessão) ou rejected com a regra
```

## Negociação de prazo no PROT-DEL (v0.5.0)

Em vez de estourar o prazo, o especialista pode propor uma extensão justificada. O Orquestrador
decide pelas regras de quem coordena (`agents/orq.py`, `_negociar_prazo`).

```{mermaid}
stateDiagram-v2
  [*] --> CRIADA
  CRIADA --> AGUARDANDO: request (ORQ)
  AGUARDANDO --> EM_EXECUCAO: agree
  AGUARDANDO --> RECUSADA: refuse
  AGUARDANDO --> EXPIRADA: timeout
  EM_EXECUCAO --> CONCLUIDA: inform
  EM_EXECUCAO --> FALHOU: failure
  EM_EXECUCAO --> EXPIRADA: timeout
  EM_EXECUCAO --> NEGOCIANDO: propose (especialista)
  NEGOCIANDO --> EM_EXECUCAO: accept-proposal (ORQ, novo prazo)
  NEGOCIANDO --> EM_EXECUCAO: reject-proposal (ORQ)
  NEGOCIANDO --> EXPIRADA: timeout
```

| Performativo | Emissor | Esquema |
|---|---|---|
| `propose` | ROLE-CUS, ROLE-ORC, ROLE-RES, ROLE-CIN, ROLE-REL | `{tipo: str, prazo_extra: int, motivo: str}` |
| `accept-proposal` | ROLE-ORQ | `{prazo: int}` (o novo `reply_by`) |
| `reject-proposal` | ROLE-ORQ | `{motivo: str}` |

Regras do Orquestrador (qualquer uma falhando, `reject-proposal` com o motivo):

1. só prazo é negociável (`tipo: mais_prazo`); resultado parcial não é aceito;
2. nenhuma extensão num fechamento com período reservado (a reserva tem prazo e outros pedidos
   esperam por ela);
3. uma extensão por subtarefa;
4. no máximo `MAX_EXTENSAO` = 20 ticks.

Aceita, a resposta leva o novo `reply_by`; o barramento guarda o prazo vigente por conversa
(`Bus.prazos`) e o temporizador antigo deixa de ter efeito
(`test_extended_deadline_replaces_the_original_timer`). Transições inválidas que viram teste:
`propose` antes de `agree`, `inform` com proposta ainda sem resposta e segunda `propose` antes da
resposta à primeira; `propose` por quem não é especialista e `accept-proposal` por quem não é o
Orquestrador são recusados na etapa de papel
(`test_protocol_rejects_negotiation_out_of_order_or_by_the_wrong_role`).

Se o especialista que propôs nunca recebesse resposta, a subtarefa expiraria no prazo original
(`NEGOCIANDO --timeout--> EXPIRADA`); o Orquestrador sempre responde, porque é obrigação do papel.
Quem usa a negociação nesta entrega é o AG-ORC, no plano `P-NEGOCIAR-PRAZO` ({doc}`cognicao`).
