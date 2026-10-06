<!-- ARQUIVO GERADO por tools/trace.py a partir de models/*.yaml — não editar à mão -->

````{prot} Solicitação do usuário (FIPA-Request externo)
:id: PROT-SOL
:entrega: DSM1
:status: especificado
:participants: ROLE-SOL, ROLE-ORQ

**Propósito:** Receber um pedido da liderança e devolver resultado ou falha explícita.  
**Meio:** Interface (ENV-UI)  
**Performativos:** request, agree, not-understood, refuse, inform, failure

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
:participants: ROLE-RES, ROLE-CUS, ROLE-ORC

**Propósito:** Resultados obtém custos e orçamento consolidados sem acessar as regras internas de outro papel.  
**Meio:** SVC-A2A  
**Performativos:** query-ref, inform, refuse, failure

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
:participants: ROLE-ORQ, ROLE-CIN, ROLE-APR

**Propósito:** Controles Internos avalia o pacote do fechamento e pode bloquear a publicação.  
**Meio:** SVC-A2A  
**Performativos:** request, inform(conforme), inform(nao_conforme), veto, waiver, request(reavaliar)

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
:entrega: DSM1
:status: especificado
:participants: ROLE-ORQ, ROLE-REL, ROLE-ORC, ROLE-APR, SVC-POL

**Propósito:** Reter ações com efeito externo até decisão humana explícita.  
**Meio:** SVC-POL + ENV-UI  
**Performativos:** propose-action, classify, approve, reject, execute, expire

```{mermaid}
stateDiagram-v2
    [*] --> PROPOSTA
    PROPOSTA --> EXECUTADA: allow
    PROPOSTA --> NEGADA: deny
    PROPOSTA --> PENDENTE: require_approval
    PENDENTE --> EXECUTADA: approve
    PENDENTE --> REJEITADA: reject
    PENDENTE --> EXPIRADA: timeout
    EXECUTADA --> [*]
    NEGADA --> [*]
    REJEITADA --> [*]
    EXPIRADA --> [*]
```

**Transições inválidas (origem de testes negativos)**

- `PENDENTE` + `execute` → rejeitar (execução sem aprovação humana)
- `NEGADA` + `approve` → rejeitar (ação DENY não admite aprovação)
````
