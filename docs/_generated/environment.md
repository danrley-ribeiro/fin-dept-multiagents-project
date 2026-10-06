<!-- ARQUIVO GERADO por tools/trace.py a partir de models/*.yaml — não editar à mão -->

````{env} ERP — razão contábil, balancete e lançamentos
:id: ENV-ERP
:entrega: DSM1
:status: especificado
:accessed_via: SVC-MCP

**Observabilidade:** Leitura via MCP (balancete, lançamentos, centros de custo, plano de contas)  
**Acionabilidade:** Escrita de ajuste contábil — ação restrita (REQUIRE_APPROVAL)  
**Exclusividade:** Período contábil exclusivo durante o fechamento  
**Autoridade:** Contabilidade do cliente (STK-03)
````

````{env} Planilhas de orçamento e premissas
:id: ENV-PLN
:entrega: DSM1
:status: especificado
:accessed_via: SVC-MCP

**Observabilidade:** Leitura via MCP (orçado por conta/centro de custo, premissas)  
**Acionabilidade:** Alteração de orçamento — ação restrita (REQUIRE_APPROVAL)  
**Exclusividade:** Não exclusiva para leitura  
**Autoridade:** Diretoria / FP&A do cliente (STK-01)
````

````{env} Base analítica histórica (data warehouse)
:id: ENV-BD
:entrega: DSM1
:status: especificado
:accessed_via: SVC-MCP

**Observabilidade:** Leitura via MCP (séries históricas, fechamentos anteriores)  
**Acionabilidade:** Nenhuma (somente leitura)  
**Exclusividade:** Não exclusiva  
**Autoridade:** TI do cliente (STK-05)
````

````{env} APIs financeiras de mercado (câmbio, IPCA, Selic)
:id: ENV-API
:entrega: DSM1
:status: especificado
:accessed_via: SVC-MCP

**Observabilidade:** Leitura via MCP; pode falhar ou atrasar  
**Acionabilidade:** Nenhuma  
**Exclusividade:** Não exclusiva (cota de chamadas)  
**Autoridade:** Provedor externo
````

````{env} Base normativa interna (políticas de alçada, SoD, manual contábil)
:id: ENV-NRM
:entrega: DSM1
:status: especificado
:accessed_via: SVC-MCP

**Observabilidade:** Leitura via MCP/RAG com proveniência (documento, trecho, versão)  
**Acionabilidade:** Nenhuma  
**Exclusividade:** Não exclusiva  
**Autoridade:** Compliance / Auditoria (STK-04)
````

````{env} Período contábil em fechamento (recurso compartilhado)
:id: ENV-PER
:entrega: DSM1
:status: especificado
:accessed_via: SVC-LCK

**Observabilidade:** Estado de reserva consultável  
**Acionabilidade:** Reservar / liberar via protocolo de reserva  
**Exclusividade:** Exclusivo por (entidade, competência), com TTL  
**Autoridade:** SVC-LCK
````

````{env} Orçamento de tokens e custo de IA (recurso consumível)
:id: ENV-TOK
:entrega: DSM1
:status: especificado
:accessed_via: SVC-MOD

**Observabilidade:** Saldo por agente/tarefa consultável no registro de modelos  
**Acionabilidade:** Consumido apenas por chamadas LLM habilitadas por flag  
**Exclusividade:** Cota por agente e por tarefa  
**Autoridade:** Controller (STK-02) via SVC-MOD
````

````{env} Interface do usuário (solicitação, aprovação e observabilidade)
:id: ENV-UI
:entrega: DSM1
:status: especificado
:accessed_via: SVC-POL

**Observabilidade:** Recebe solicitações e decisões de aprovação humanas  
**Acionabilidade:** Exibe resultado final, pedidos de aprovação e dashboard  
**Exclusividade:** Não exclusiva  
**Autoridade:** Usuários autenticados (STK-01, STK-02, STK-04)
````
