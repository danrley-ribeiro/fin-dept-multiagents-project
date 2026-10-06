<!-- ARQUIVO GERADO por tools/trace.py a partir de models/*.yaml — não editar à mão -->

````{svc} Camada de comunicação A2A
:id: SVC-A2A
:entrega: DSM1
:status: especificado

**Camada:** Comunicação  
**Responsabilidade:** Transporta mensagens entre agentes com envelope FIPA-ACL (remetente, destinatário, performativo, conteúdo, ontologia, conversation_id, reply_by) e descoberta por Agent Card.  
**Por que não é agente:** Transporte não decide; a semântica social fica nos papéis e protocolos.
````

````{svc} Gateway MCP (conectores de dados)
:id: SVC-MCP
:entrega: DSM1
:status: especificado

**Camada:** Comunicação  
**Responsabilidade:** Expõe ERP, planilhas, base histórica, APIs de mercado e base normativa como tools MCP tipadas; leitura por padrão, escrita apenas via SafetyPolicy.  
**Por que não é agente:** Conector não tem objetivo próprio; é ferramenta do agente.
````

````{svc} AuditService (governança e auditoria)
:id: SVC-AUD
:entrega: DSM1
:status: especificado

**Camada:** Governança  
**Responsabilidade:** Intercepta toda ação, mensagem e chamada de modelo e grava logs de decisão, prompt e custo em JSONL append-only, com redaction fail-closed.  
**Por que não é agente:** Interceptação central evita que cada agente logue de forma isolada.
````

````{svc} ModelRegistry (configuração de modelos)
:id: SVC-MOD
:entrega: DSM1
:status: especificado

**Camada:** Configuração  
**Responsabilidade:** Registro central por agente: flag LLM (padrão desligada), modelo, limite de tokens e orçamento; troca em runtime sem redeploy; impede LLM em papéis não permitidos e valida números do texto gerado.  
**Por que não é agente:** Configuração e validação não deliberam sobre o domínio.
````

````{svc} MemoryService (embeddings e grafo de conhecimento)
:id: SVC-MEM
:entrega: DSM1
:status: especificado

**Camada:** Memória  
**Responsabilidade:** Persiste apenas saídas aprovadas como embeddings e nós/arestas (conta, indicador, decisão, período) e responde consultas com proveniência.  
**Por que não é agente:** Memória é recurso consultado, não entidade com objetivos.
````

````{svc} SafetyPolicy e Approval Gate
:id: SVC-POL
:entrega: DSM1
:status: especificado

**Camada:** Governança  
**Responsabilidade:** Classifica toda ação proposta em ALLOW, REQUIRE_APPROVAL ou DENY (fail-closed) e retém ações restritas até decisão humana.  
**Por que não é agente:** Política determinística precisa ser previsível; não negocia.
````

````{svc} PeriodLockService (reserva de período)
:id: SVC-LCK
:entrega: DSM1
:status: especificado

**Camada:** Coordenação  
**Responsabilidade:** Mantém tabela de reservas exclusivas por (entidade, competência) com TTL, rejeitando reservas sobrepostas.  
**Por que não é agente:** Invariante de exclusão mútua é melhor garantido por serviço simples.
````
