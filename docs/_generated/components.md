````{comp} Componente do Orquestrador
:id: COMP-ORQ
:entrega: DSM2
:status: implementado
:realizes: AG-ORQ

Componente implementado em `src/fin_mas/agents/orq.py`.
````

````{comp} Componente do Agente de Custos
:id: COMP-CUS
:entrega: DSM2
:status: implementado
:realizes: AG-CUS

Componente implementado em `src/fin_mas/agents/cus.py`.
````

````{comp} Componente do Agente de Orçamento
:id: COMP-ORC
:entrega: DSM2
:status: implementado
:realizes: AG-ORC

Componente implementado em `src/fin_mas/agents/orc.py`.
````

````{comp} Componente do Agente de Resultados
:id: COMP-RES
:entrega: DSM2
:status: implementado
:realizes: AG-RES

Componente implementado em `src/fin_mas/agents/res.py`.
````

````{comp} Componente do Agente de Controles Internos
:id: COMP-CIN
:entrega: DSM2
:status: implementado
:realizes: AG-CIN

Componente implementado em `src/fin_mas/agents/cin.py`.
````

````{comp} Componente do Agente de Relatórios
:id: COMP-REL
:entrega: DSM2
:status: implementado
:realizes: AG-REL

Componente implementado em `src/fin_mas/agents/rel.py`.
````

````{comp} Barramento/adaptador A2A
:id: COMP-A2A
:entrega: DSM2
:status: implementado
:realizes: SVC-A2A

Componente implementado em `src/fin_mas/core/bus.py`.
````

````{comp} MCP servers mock (ERP
:id: COMP-MCP
:entrega: DSM2
:status: implementado
:realizes: SVC-MCP

Componente implementado em `src/fin_mas/mcp/gateway.py`.
````

````{comp} Serviço de Auditoria (tracer JSONL)
:id: COMP-AUD
:entrega: DSM2
:status: implementado
:realizes: SVC-AUD

Componente implementado em `src/fin_mas/services/audit.py`.
````

````{comp} Registro de Modelos e gateway LLM (opcional
:id: COMP-MOD
:entrega: DSM3
:status: implementado
:realizes: SVC-MOD

Componente implementado em `src/fin_mas/services/modelos.py`.
````

````{comp} Serviço de Memória (aprovada
:id: COMP-MEM
:entrega: DSM3
:status: implementado
:realizes: SVC-MEM

Componente implementado em `src/fin_mas/services/memoria.py`.
````

````{comp} Política de Segurança e Approval Gate
:id: COMP-POL
:entrega: DSM3
:status: implementado
:realizes: SVC-POL

Componente implementado em `src/fin_mas/services/politica.py`.
````

````{comp} Redaction fail-closed e trace com hash encadeado
:id: COMP-RED
:entrega: DSM3
:status: implementado
:realizes: SVC-AUD

Componente implementado em `src/fin_mas/services/redacao.py`.
````

````{comp} Validação de envelope e esquema das mensagens A2A
:id: COMP-SCH
:entrega: DSM3
:status: implementado
:realizes: SVC-A2A

Componente implementado em `src/fin_mas/core/schema.py`.
````

````{comp} Núcleo BDI (crenças
:id: COMP-BDI
:entrega: DSM2
:status: implementado
:realizes: AG-ORC, AG-CIN

Componente implementado em `src/fin_mas/core/bdi.py`.
````

````{comp} Execução ao vivo
:id: COMP-OBS
:entrega: DSM2
:status: implementado
:realizes: SVC-AUD

Componente implementado em `web/src/App.tsx`.
````

````{comp} Modelos Excel e servidor MCP de Excel (empresa sem ERP)
:id: COMP-XLS
:entrega: DSM3
:status: implementado
:realizes: SVC-MCP

Componente implementado em `src/fin_mas/mcp/excel_server.py`.
````

````{comp} Reserva de Período
:id: COMP-LCK
:entrega: DSM2
:status: implementado
:realizes: SVC-LCK

Componente implementado em `src/fin_mas/services/locks.py`.
````
