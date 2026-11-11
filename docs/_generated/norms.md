````{norm} Efeito externo exige aprovação humana
:id: NORM-01
:entrega: DSM1
:status: especificado
:enforced_by: SVC-POL

**Escopo:** Lançar ajuste no ERP, alterar orçamento, publicar relatório à diretoria  
**Condição:** Qualquer papel propõe ação com efeito fora do sistema  
**Consequência:** Ação retida no Approval Gate até approve; timeout expira sem executar  
**Decisão:** `REQUIRE_APPROVAL`
````

````{norm} Fora da allowlist do papel é negado
:id: NORM-02
:entrega: DSM1
:status: especificado
:enforced_by: SVC-POL, SVC-MCP

**Escopo:** Toda tool MCP e ação de escrita  
**Condição:** Ação não consta da allowlist do papel solicitante  
**Consequência:** Bloqueio fail-closed, sem opção de aprovação, registrado em log  
**Decisão:** `DENY`
````

````{norm} Período em fechamento é exclusivo
:id: NORM-03
:entrega: DSM1
:status: especificado
:enforced_by: SVC-LCK

**Escopo:** Par (entidade, competência)  
**Condição:** Já existe reserva ativa de outro dono  
**Consequência:** reserve-failure explicado; reserva expira por TTL  
**Decisão:** `DENY`
````

````{norm} Não conformidade crítica bloqueia publicação
:id: NORM-04
:entrega: DSM1
:status: especificado
:enforced_by: SVC-POL

**Escopo:** Resultado do período e relatório executivo  
**Condição:** Parecer do Agente de Controles Internos com severidade crítica  
**Consequência:** Publicação vetada até correção reavaliada ou waiver humano justificado  
**Decisão:** `DENY`
````

````{norm} LLM não calcula números nem autoriza ações
:id: NORM-05
:entrega: DSM1
:status: especificado
:enforced_by: SVC-MOD, SVC-POL

**Escopo:** Toda saída de LLM (AG-REL, AG-RES, AG-ORC)  
**Condição:** Texto gerado contém número divergente do núcleo determinístico ou propõe ação  
**Consequência:** Texto descartado e substituído pelo template; proposta tratada como não autorizada  
**Decisão:** `DENY`
````

````{norm} Logs e memória sem segredos nem dados pessoais desnecessários
:id: NORM-06
:entrega: DSM1
:status: especificado
:enforced_by: SVC-AUD, SVC-MEM

**Escopo:** Traces JSONL, logs de prompt, memória de longo prazo  
**Condição:** Conteúdo contém credencial, token, chave ou dado pessoal fora da finalidade  
**Consequência:** Redaction; se a sanitização falhar, a gravação é recusada (fail-closed)  
**Decisão:** `OBRIGACAO`
````

````{norm} LLM só por flag, só em papéis permitidos, dentro da cota
:id: NORM-07
:entrega: DSM1
:status: especificado
:enforced_by: SVC-MOD

**Escopo:** Configuração de modelos por agente  
**Condição:** Flag desligada, papel não permitido (AG-ORQ, AG-CUS, AG-CIN) ou cota de tokens esgotada  
**Consequência:** Chamada LLM bloqueada e agente segue em modo determinístico (template)  
**Decisão:** `DENY`
````

````{norm} Somente saída aprovada vira memória
:id: NORM-08
:entrega: DSM1
:status: especificado
:enforced_by: SVC-MEM

**Escopo:** Serviço de Memória (SVC-MEM)  
**Condição:** Saída sem aprovação humana registrada  
**Consequência:** Não é indexada em embeddings nem no grafo  
**Decisão:** `DENY`
````

````{norm} Só mensagem autêntica, do papel certo e bem formada muda o estado de uma conversa
:id: NORM-09
:entrega: DSM3
:status: pendente
:enforced_by: SVC-A2A

**Escopo:** Toda mensagem A2A e toda transição local de FSM (SVC-A2A)  
**Condição:** Remetente não registrado ou sem credencial, papel sem permissão para o performativo ou evento, destinatário fora da conversa, esquema inválido ou transição fora da FSM  
**Consequência:** Mensagem ou transição rejeitada e registrada (`rejected`); nenhum estado muda; a simulação segue  
**Decisão:** `DENY`
````

````{norm} Decisão humana vinculada, com política explícita e de uso único
:id: NORM-10
:entrega: DSM3
:status: pendente
:enforced_by: SVC-POL

**Escopo:** Liberação de veto (waiver) e correção no ERP (Approval Gate, SVC-POL)  
**Condição:** Decisão sem ticket do SVC-POL, de outro aprovador, com hash de veto diferente, fora do prazo, fora das opções abertas, sem justificativa, por pessoa envolvida no lançamento, reutilizada ou repetida após waiver anterior do mesmo padrão  
**Consequência:** Decisão rejeitada no barramento; o veto continua valendo; sem decisão válida no prazo, bloqueio  
**Decisão:** `DENY`
````
