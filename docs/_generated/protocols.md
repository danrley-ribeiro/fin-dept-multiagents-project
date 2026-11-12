````{prot} Solicitação do usuário (FIPA-Request externo)
:id: PROT-SOL
:entrega: DSM1
:status: especificado
:participants: ROLE-SOL, ROLE-ORQ

**Propósito:** Receber um pedido da liderança e devolver resultado ou falha explícita.  
**Meio:** Interface (ENV-UI)  
**Performativos:** request, agree, not-understood, refuse, inform, failure

**Diagrama: Máquina de estados PROT-SOL** (`entregas/dsm1/modelos-editaveis/protocols_fsm_PROT-SOL.mmd`)

```{mermaid}
stateDiagram-v2
    [*] --> RECEBIDA
    RECEBIDA --> RECUSADA: not-understood
    RECEBIDA --> RECUSADA: refuse
    RECEBIDA --> EM_EXECUCAO: agree
    EM_EXECUCAO --> CONCLUIDA: inform
    EM_EXECUCAO --> FALHOU: failure
    CONCLUIDA --> [*]
    FALHOU --> [*]
    RECUSADA --> [*]
```

**Transições inválidas (origem de testes negativos)**

- `RECEBIDA` + `inform` → rejeitar (resultado antes de aceitar a solicitação)
- `CONCLUIDA` + `inform` → rejeitar (segundo resultado para a mesma conversa)
````

````{prot} Delegação de subtarefa (FIPA-Request via A2A)
:id: PROT-DEL
:entrega: DSM1
:status: especificado
:participants: ROLE-ORQ, ROLE-CUS, ROLE-ORC, ROLE-RES, ROLE-CIN, ROLE-REL

**Propósito:** Orquestrador atribui uma subtarefa do DAG a um papel especialista com prazo reply_by.  
**Meio:** SVC-A2A  
**Performativos:** request, agree, refuse, inform, failure

**Diagrama: Máquina de estados PROT-DEL** (`entregas/dsm1/modelos-editaveis/protocols_fsm_PROT-DEL.mmd`)

```{mermaid}
stateDiagram-v2
    [*] --> CRIADA
    CRIADA --> AGUARDANDO: request
    AGUARDANDO --> EM_EXECUCAO: agree
    AGUARDANDO --> RECUSADA: refuse
    AGUARDANDO --> EXPIRADA: timeout
    EM_EXECUCAO --> CONCLUIDA: inform
    EM_EXECUCAO --> FALHOU: failure
    EM_EXECUCAO --> EXPIRADA: timeout
    CONCLUIDA --> [*]
    FALHOU --> [*]
    RECUSADA --> [*]
    EXPIRADA --> [*]
```

**Transições inválidas (origem de testes negativos)**

- `AGUARDANDO` + `inform` → rejeitar (resultado antes de agree)
- `EXPIRADA` + `inform` → rejeitar (resposta após reply_by é descartada)
````

````{prot} Consulta entre especialistas (FIPA-Query-Ref via A2A)
:id: PROT-QRY
:entrega: DSM1
:status: especificado
:participants: ROLE-RES, ROLE-CUS, ROLE-ORC, ROLE-CIN

**Propósito:** Um especialista obtém informação de outro sem acessar suas regras internas: o Agente de Resultados consulta Custos e Orçamento; o Agente de Orçamento consulta Controles Internos para explicar um desvio (decisão do próprio agente, sem o Orquestrador).  
**Meio:** SVC-A2A  
**Performativos:** query-ref, inform, refuse, failure

**Diagrama: Máquina de estados PROT-QRY** (`entregas/dsm1/modelos-editaveis/protocols_fsm_PROT-QRY.mmd`)

```{mermaid}
stateDiagram-v2
    [*] --> CRIADA
    CRIADA --> AGUARDANDO: query-ref
    AGUARDANDO --> RESPONDIDA: inform
    AGUARDANDO --> RECUSADA: refuse
    AGUARDANDO --> FALHOU: failure
    AGUARDANDO --> EXPIRADA: timeout
    RESPONDIDA --> [*]
    RECUSADA --> [*]
    FALHOU --> [*]
    EXPIRADA --> [*]
```

**Transições inválidas (origem de testes negativos)**

- `CRIADA` + `inform` → rejeitar (inform não solicitado (conversation_id desconhecido))
````

````{prot} Verificação de conformidade com veto
:id: PROT-CMP
:entrega: DSM1
:status: especificado
:participants: ROLE-ORQ, ROLE-CIN

**Propósito:** O Agente de Controles Internos avalia o pacote do fechamento e pode bloquear a publicação.  
**Meio:** SVC-A2A  
**Performativos:** request, conforme, nao_conforme_nao_critico, veto, correcao, waiver_humano, prazo_esgotado, publicar

**Diagrama: Máquina de estados PROT-CMP** (`entregas/dsm1/modelos-editaveis/protocols_fsm_PROT-CMP.mmd`)

```{mermaid}
stateDiagram-v2
    [*] --> CRIADA
    CRIADA --> EM_ANALISE: request
    EM_ANALISE --> LIBERADO: conforme
    EM_ANALISE --> LIBERADO_COM_RESSALVA: nao_conforme_nao_critico
    EM_ANALISE --> VETADO: veto
    LIBERADO_COM_RESSALVA --> LIBERADO: publicar
    VETADO --> EM_ANALISE: correcao
    VETADO --> LIBERADO_COM_RESSALVA: waiver_humano
    VETADO --> BLOQUEADO: prazo_esgotado
    LIBERADO --> [*]
    BLOQUEADO --> [*]
```

**Transições inválidas (origem de testes negativos)**

- `VETADO` + `publicar` → rejeitar (publicar resultado vetado sem waiver ou correção)
````

````{prot} Reserva de período contábil
:id: PROT-LCK
:entrega: DSM1
:status: especificado
:participants: ROLE-ORQ, SVC-LCK

**Propósito:** Garantir exclusão mútua de um fechamento por (entidade, competência).  
**Meio:** Chamada local ao serviço  
**Performativos:** reserve, reserve-accept, reserve-failure, release

**Diagrama: Máquina de estados PROT-LCK** (`entregas/dsm1/modelos-editaveis/protocols_fsm_PROT-LCK.mmd`)

```{mermaid}
stateDiagram-v2
    [*] --> LIVRE
    LIVRE --> RESERVADO: reserve
    RESERVADO --> RESERVADO: reserve_outro_dono
    RESERVADO --> LIVRE: release
    RESERVADO --> LIVRE: ttl_expirado
    LIVRE --> [*]
```

**Transições inválidas (origem de testes negativos)**

- `RESERVADO` + `reserve_outro_dono_aceito` → rejeitar (segunda reserva sobreposta aceita)
- `LIVRE` + `release` → rejeitar (liberar reserva inexistente)
````

````{prot} Approval Gate (human-in-the-loop)
:id: PROT-APR
:entrega: DSM3
:status: pendente
:participants: ROLE-ORQ, ROLE-APR, SVC-POL

**Propósito:** Reter ações restritas (waiver de veto, correção no ERP) até decisão humana explícita, vinculada à solicitação, ao veto (hash dos achados), à identidade do aprovador e a um prazo; cada aprovação é de uso único.  
**Meio:** SVC-A2A + SVC-POL  
**Performativos:** propose-action, approve, reject

**Diagrama: Máquina de estados PROT-APR** (`entregas/dsm1/modelos-editaveis/protocols_fsm_PROT-APR.mmd`)

```{mermaid}
stateDiagram-v2
    [*] --> CRIADA
    CRIADA --> PROPOSTA: propose-action
    PROPOSTA --> EXECUTADA: allow
    PROPOSTA --> NEGADA: deny
    PROPOSTA --> PENDENTE: require_approval
    PENDENTE --> APROVADA: approve
    PENDENTE --> REJEITADA: reject
    PENDENTE --> EXPIRADA: timeout
    APROVADA --> EXECUTADA: execute
    APROVADA --> EXPIRADA: timeout
    EXECUTADA --> [*]
    NEGADA --> [*]
    REJEITADA --> [*]
    EXPIRADA --> [*]
```

**Transições inválidas (origem de testes negativos)**

- `PENDENTE` + `execute` → rejeitar (execução sem aprovação humana)
- `NEGADA` + `approve` → rejeitar (ação DENY não admite aprovação)
- `APROVADA` + `approve` → rejeitar (aprovação duplicada)
- `EXECUTADA` + `approve` → rejeitar (aprovação reutilizada após a execução)
- `EXPIRADA` + `approve` → rejeitar (aprovação após o prazo é descartada)
````
