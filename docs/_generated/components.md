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

````{comp} Núcleo BDI (crenças, desejos, planos, intenções, estratégias de compromisso)
:id: COMP-BDI
:entrega: DSM2
:status: implementado
:realizes: AG-ORC, AG-CIN, AG-RES, AG-CUS, AG-REL

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

````{comp} Serviço de identidade e acesso
:id: COMP-IAM
:entrega: DSM3
:status: implementado
:realizes: SVC-IAM

Componente implementado em `src/fin_mas/services/iam.py`.
````

````{comp} Arquivo selado com trava entre processos
:id: COMP-SEL
:entrega: DSM3
:status: implementado
:realizes: SVC-IAM

Componente implementado em `src/fin_mas/services/selado.py`.
````

````{comp} Trilha de acesso encadeada
:id: COMP-TRI
:entrega: DSM3
:status: implementado
:realizes: SVC-IAM

Componente implementado em `src/fin_mas/services/trilha.py`.
````

````{comp} Linha de comando de acesso e implantação
:id: COMP-CLA
:entrega: DSM3
:status: implementado
:realizes: SVC-IAM

Componente implementado em `src/fin_mas/cli_acesso.py`.
````

````{comp} Provedores de LLM (mocks
:id: COMP-PRV
:entrega: DSM3
:status: implementado
:realizes: SVC-MOD

Componente implementado em `src/fin_mas/services/provedores.py`.
````

````{comp} Hipóteses (proposta
:id: COMP-INF
:entrega: DSM3
:status: implementado
:realizes: AG-ORC, AG-RES

Componente implementado em `src/fin_mas/core/inferencia.py`.
````

````{comp} Motor local de hipóteses (regras offline)
:id: COMP-COG
:entrega: DSM3
:status: implementado
:realizes: AG-ORC, AG-RES

Componente implementado em `src/fin_mas/cognicao/regras.py`.
````

````{comp} Verificador de invariantes do trace
:id: COMP-INV
:entrega: DSM3
:status: implementado
:realizes: SVC-AUD

Componente implementado em `src/fin_mas/invariantes.py`.
````

````{comp} Explicação de decisões e diagrama de sequência
:id: COMP-EXP
:entrega: DSM3
:status: implementado
:realizes: SVC-AUD

Componente implementado em `src/fin_mas/services/explicacao.py`.
````

````{comp} Console de administração de acesso e auditoria (TUI)
:id: COMP-TUI
:entrega: DSM3
:status: implementado
:realizes: SVC-IAM, SVC-AUD

Componente implementado em `src/fin_mas/tui/app.py`.
````

````{comp} Instalação por um comando e diagnóstico
:id: COMP-IMP
:entrega: DSM3
:status: implementado
:realizes: SVC-IAM

Componente implementado em `src/fin_mas/implantacao.py`.
````

````{comp} Agente de Resultados cognitivo (variante BDI)
:id: COMP-RESB
:entrega: DSM4
:status: implementado
:realizes: AG-RES

Componente implementado em `src/fin_mas/agents/res_bdi.py`.
````

````{comp} Agente de Custos cognitivo (variante BDI)
:id: COMP-CUSB
:entrega: DSM4
:status: implementado
:realizes: AG-CUS

Componente implementado em `src/fin_mas/agents/cus_bdi.py`.
````

````{comp} Agente de Relatórios cognitivo (variante BDI)
:id: COMP-RELB
:entrega: DSM4
:status: implementado
:realizes: AG-REL

Componente implementado em `src/fin_mas/agents/rel_bdi.py`.
````

````{comp} Registro selado de aprendizado das regras locais
:id: COMP-APD
:entrega: DSM4
:status: implementado
:realizes: SVC-APD

Componente implementado em `src/fin_mas/services/aprendizado.py`.
````

````{comp} Perfil cognitivo por porte (pesos, público, compromisso, limiares)
:id: COMP-PCG
:entrega: DSM4
:status: implementado
:realizes: AG-RES, AG-CUS, AG-REL

Componente implementado em `src/fin_mas/cognicao/perfis.py`.
````

````{comp} Base de conhecimento normativo com busca lexical (BM25)
:id: COMP-CON
:entrega: DSM4
:status: implementado
:realizes: SVC-MCP

Componente implementado em `src/fin_mas/conhecimento/base.py`.
````

````{comp} Métricas da cognição dos especialistas (MET-30 e MET-31)
:id: COMP-MCG
:entrega: DSM4
:status: implementado
:realizes: SVC-AUD

Componente implementado em `src/fin_mas/metricas_cognicao.py`.
````

````{comp} Modelo de falhas aleatórias por seed
:id: COMP-CAO
:entrega: DSM4
:status: implementado
:realizes: SVC-A2A

Componente implementado em `src/fin_mas/caos.py`.
````

````{comp} Parâmetros de coordenação injetáveis
:id: COMP-PAR
:entrega: DSM4
:status: implementado
:realizes: AG-ORQ

Componente implementado em `src/fin_mas/parametros.py`.
````

````{comp} Workflow centralizado funcionalmente equivalente (linha de base)
:id: COMP-WEQ
:entrega: DSM4
:status: implementado
:realizes: SVC-POL

Componente implementado em `src/fin_mas/baseline_eq.py`.
````

````{comp} Estatística do experimento com a biblioteca padrão
:id: COMP-EST
:entrega: DSM4
:status: implementado
:realizes: SVC-AUD

Componente implementado em `src/fin_mas/estatistica.py`.
````

````{comp} Experimento em blocos (desenho
:id: COMP-ESU
:entrega: DSM4
:status: implementado
:realizes: SVC-AUD

Componente implementado em `src/fin_mas/estudo.py`.
````

````{comp} Tabelas e figuras do experimento
:id: COMP-ESR
:entrega: DSM4
:status: implementado
:realizes: SVC-AUD

Componente implementado em `src/fin_mas/estudo_relato.py`.
````
