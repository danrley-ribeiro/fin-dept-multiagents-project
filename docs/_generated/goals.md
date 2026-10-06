<!-- ARQUIVO GERADO por tools/trace.py a partir de models/*.yaml — não editar à mão -->

````{goal} Controladoria terceirizada coordenada e auditável
:id: G-00
:entrega: DSM1
:status: especificado
:addresses: PROB-01, PROB-02, PROB-03, PROB-04, PROB-05, PROB-06, PROB-07, PROB-08
:concerns: STK-01, STK-02, STK-04

Executar as rotinas de controladoria da empresa cliente de forma terceirizada e coordenada, entregando à liderança o resultado do período e análises confiáveis, respeitando alçadas, sigilo e aprovação humana, com evidência reconstruível de cada decisão.
````

````{goal} Atender solicitações decompondo-as em tarefas coordenadas
:id: G-01
:entrega: DSM1
:status: especificado
:refines: G-00
:addresses: PROB-01
:concerns: STK-01

Transformar pedidos da liderança em subtarefas atribuídas e uma resposta final agregada.
````

````{goal} Apurar custos, margens e rentabilidade
:id: G-02
:entrega: DSM1
:status: especificado
:refines: G-00
:addresses: PROB-02
:concerns: STK-01, STK-03

Custos fixos/variáveis, margem de contribuição e rentabilidade por produto, serviço ou UN.
````

````{goal} Controlar o orçamento
:id: G-03
:entrega: DSM1
:status: especificado
:refines: G-00
:addresses: PROB-03
:concerns: STK-01

Orçado x realizado contínuo, desvios sinalizados e forecast.
````

````{goal} Consolidar resultado e indicadores
:id: G-04
:entrega: DSM1
:status: especificado
:refines: G-00
:addresses: PROB-01
:concerns: STK-01, STK-04

DRE gerencial, EBITDA, fluxo de caixa e KPIs corporativos consistentes.
````

````{goal} Garantir conformidade antes da publicação
:id: G-05
:entrega: DSM1
:status: especificado
:refines: G-00
:addresses: PROB-04
:concerns: STK-04, STK-03

Validar políticas, alçadas e regras contábeis e impedir publicação de resultado não conforme.
````

````{goal} Entregar relatórios executivos acionáveis
:id: G-06
:entrega: DSM1
:status: especificado
:refines: G-00
:addresses: PROB-05
:concerns: STK-01

Relatório claro, consistente com a DRE e orientado à decisão.
````

````{goal} Manter auditabilidade total e custo de IA sob controle
:id: G-07
:entrega: DSM1
:status: especificado
:refines: G-00
:addresses: PROB-06
:concerns: STK-04, STK-05, STK-06, STK-07

Registrar decisões, prompts, fontes e custos de forma segura e reconstruível.
````

````{goal} Reutilizar conhecimento aprovado
:id: G-08
:entrega: DSM1
:status: especificado
:refines: G-00
:addresses: PROB-07
:concerns: STK-01, STK-06

Análises aprovadas viram memória consultável com proveniência.
````

````{goal} Restringir efeitos externos à autorização humana
:id: G-09
:entrega: DSM1
:status: especificado
:refines: G-00
:addresses: PROB-08
:concerns: STK-02, STK-05

Nenhuma ação com efeito no mundo real sem classificação de política e aprovação quando exigida.
````
