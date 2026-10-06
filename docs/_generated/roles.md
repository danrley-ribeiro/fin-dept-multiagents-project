<!-- ARQUIVO GERADO por tools/trace.py a partir de models/*.yaml — não editar à mão -->

````{role} Solicitante (humano)
:id: ROLE-SOL
:entrega: DSM1
:status: especificado
:llm: nao_aplicavel
:played_by: STK-01
:uses_protocol: PROT-SOL

**Responsabilidades (Resp)**

- Formular solicitações à controladoria
- Receber o resultado final

**Permissões (Perm)**

- Enviar request pela interface
- Consultar dashboard de observabilidade

**Obrigações (Obl)**

- Usar intenções do catálogo ou aceitar not-understood
````

````{role} Aprovador (controller humano)
:id: ROLE-APR
:entrega: DSM1
:status: especificado
:llm: nao_aplicavel
:played_by: STK-02
:uses_protocol: PROT-APR, PROT-CMP

**Responsabilidades (Resp)**

- Decidir sobre ações restritas
- Conceder waiver a não conformidades

**Permissões (Perm)**

- Aprovar ou rejeitar ActionRequest
- Ajustar configuração de modelos e cotas

**Obrigações (Obl)**

- Registrar justificativa da decisão
````

````{role} Orquestrador
:id: ROLE-ORQ
:entrega: DSM1
:status: especificado
:llm: nao_permitido
:uses_protocol: PROT-SOL, PROT-DEL, PROT-CMP, PROT-LCK, PROT-APR

**Responsabilidades (Resp)**

- Receber solicitações e mapear para intenção do catálogo
- Decompor em DAG de subtarefas e delegar aos papéis competentes
- Reservar o período e agregar a resposta final

**Permissões (Perm)**

- Delegar (request) a qualquer papel especialista
- Reservar e liberar período no PeriodLockService
- Propor publicação ao Approval Gate

**Obrigações (Obl)**

- Responder toda solicitação com resultado ou falha explícita
- Respeitar reply_by e veto de conformidade
- Liberar a reserva ao término ou falha
````

````{role} Analista de Custos e Rentabilidade
:id: ROLE-CUS
:entrega: DSM1
:status: especificado
:llm: nao_permitido
:uses_protocol: PROT-DEL, PROT-QRY

**Responsabilidades (Resp)**

- Apurar custos fixos e variáveis e aplicar rateio por critério configurado
- Calcular margem de contribuição e rentabilidade por produto, serviço e UN

**Permissões (Perm)**

- Ler ERP e base histórica via MCP
- Responder query-ref de outros papéis

**Obrigações (Obl)**

- Anexar proveniência a cada valor
- Informar falha se dado de origem estiver ausente
````

````{role} Analista de Orçamento e Controle Orçamentário
:id: ROLE-ORC
:entrega: DSM1
:status: especificado
:llm: flag
:uses_protocol: PROT-DEL, PROT-QRY, PROT-APR

**Responsabilidades (Resp)**

- Comparar orçado x realizado por conta e centro de custo
- Sinalizar desvios acima do limiar e projetar forecast

**Permissões (Perm)**

- Ler planilhas de orçamento e ERP via MCP
- Propor alteração de orçamento (restrita)
- Responder query-ref

**Obrigações (Obl)**

- Explicitar limiar e método de forecast usados
- Não alterar orçamento sem aprovação
````

````{role} Analista de Resultados e Indicadores
:id: ROLE-RES
:entrega: DSM1
:status: especificado
:llm: flag
:uses_protocol: PROT-DEL, PROT-QRY

**Responsabilidades (Resp)**

- Montar DRE gerencial, EBITDA, fluxo de caixa e KPIs
- Obter custos e orçamento dos papéis especialistas

**Permissões (Perm)**

- Iniciar query-ref para CUS e ORC
- Ler ERP e APIs de mercado via MCP

**Obrigações (Obl)**

- Não recalcular rateio próprio — usar o de CUS
- Sinalizar inconsistência de fechamento
````

````{role} Auditor de Controles Internos
:id: ROLE-CIN
:entrega: DSM1
:status: especificado
:llm: nao_permitido
:uses_protocol: PROT-DEL, PROT-CMP

**Responsabilidades (Resp)**

- Verificar alçada, segregação de funções, duplicidade, conciliação e competência
- Emitir parecer conforme / não conforme com regra e severidade

**Permissões (Perm)**

- Ler ERP e base normativa via MCP
- Vetar publicação por não conformidade crítica

**Obrigações (Obl)**

- Citar regra e evidência de cada apontamento
- Reavaliar após waiver ou correção
````

````{role} Redator de Relatórios Gerenciais
:id: ROLE-REL
:entrega: DSM1
:status: especificado
:llm: flag
:uses_protocol: PROT-DEL, PROT-APR

**Responsabilidades (Resp)**

- Sintetizar resultados em relatório executivo por template
- Acrescentar narrativa e insights quando a flag LLM estiver ativa

**Permissões (Perm)**

- Consultar memória aprovada
- Propor publicação do relatório (restrita)

**Obrigações (Obl)**

- Preservar números do núcleo determinístico
- Usar template se o texto LLM divergir
````
