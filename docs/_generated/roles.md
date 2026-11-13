````{role} Solicitante (humano)
:id: ROLE-SOL
:entrega: DSM1
:status: especificado
:llm: nao_aplicavel
:played_by: STK-01
:uses_protocol: PROT-SOL
:grants: PERM-SIM-VER, PERM-SOL-CRIAR, PERM-DAD-VER

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
:uses_protocol: PROT-APR
:grants: PERM-SIM-VER, PERM-APR-DECIDIR, PERM-MOD-VER, PERM-MOD-CONFIG, PERM-DAD-VER, PERM-AUD-VER

**Responsabilidades (Resp)**

- Decidir sobre ações restritas
- Conceder waiver a não conformidades

**Permissões (Perm)**

- Aprovar ou rejeitar ActionRequest
- Ajustar configuração de modelos e cotas

**Obrigações (Obl)**

- Registrar justificativa da decisão
````

````{role} Operador da plataforma (humano)
:id: ROLE-OPE
:entrega: DSM3
:status: especificado
:llm: nao_aplicavel
:plataforma: sim
:played_by: STK-06
:grants: PERM-SIM-VER, PERM-SIM-OPERAR, PERM-AGT-ENERGIA, PERM-DAD-VER, PERM-DAD-ENVIAR, PERM-DAD-CONECTAR, PERM-MOD-VER, PERM-AUD-VER

**Responsabilidades (Resp)**

- Acompanhar a execução dos agentes
- Operar a simulação e as fontes de dados

**Permissões (Perm)**

- Pausar e retomar a execução
- Ligar e desligar especialistas
- Enviar planilhas validadas

**Obrigações (Obl)**

- Agir só pela interface autenticada
- Não decidir no Approval Gate sem o papel de aprovador
````

````{role} Auditor (humano)
:id: ROLE-AUD
:entrega: DSM3
:status: especificado
:llm: nao_aplicavel
:plataforma: sim
:played_by: STK-04
:grants: PERM-SIM-VER, PERM-AUD-VER, PERM-AUD-EXPORTAR, PERM-MOD-VER, PERM-DAD-VER

**Responsabilidades (Resp)**

- Examinar decisões
- aprovações e acessos
- Verificar a integridade das trilhas

**Permissões (Perm)**

- Consultar e exportar o trace e a trilha de acesso
- Ver a configuração de modelos

**Obrigações (Obl)**

- Não alterar dados nem operar a simulação
````

````{role} Administrador de acesso (humano)
:id: ROLE-ADM
:entrega: DSM3
:status: especificado
:llm: nao_aplicavel
:plataforma: sim
:played_by: STK-05
:grants: PERM-IAM-USUARIOS, PERM-IAM-PAPEIS, PERM-IAM-SESSOES, PERM-AUD-VER, PERM-AUD-EXPORTAR, PERM-SIM-VER, PERM-DAD-VER, PERM-DAD-REDE

**Responsabilidades (Resp)**

- Manter contas
- papéis e sessões
- Zelar pela trilha de acesso

**Permissões (Perm)**

- Criar e bloquear contas
- Atribuir papéis
- Revogar sessões

**Obrigações (Obl)**

- Não acumular o papel de aprovador
- Manter ao menos um administrador ativo
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
- Reservar e liberar período na Reserva de Período (SVC-LCK)
- Propor publicação ao Approval Gate

**Obrigações (Obl)**

- Responder toda solicitação com resultado ou falha explícita
- Respeitar reply_by e veto de conformidade
- Liberar a reserva ao término ou falha
- Reenviar uma vez a subtarefa expirada ou com falha; na segunda falha, abortar e informar qual subtarefa falhou
````

````{role} Analista de Custos
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

````{role} Analista de Orçamento
:id: ROLE-ORC
:entrega: DSM1
:status: especificado
:llm: flag
:uses_protocol: PROT-DEL, PROT-QRY

**Responsabilidades (Resp)**

- Comparar orçado x realizado por conta e centro de custo
- Sinalizar desvios acima do limiar e projetar forecast
- Reconciliar planilha e ERP e explicar desvios antes de sinalizá-los

**Permissões (Perm)**

- Ler planilhas de orçamento e ERP via MCP
- Propor alteração de orçamento (restrita)
- Responder query-ref
- Iniciar query-ref para ROLE-CIN

**Obrigações (Obl)**

- Explicitar limiar e método de forecast usados
- Não alterar orçamento sem aprovação
- Registrar a fonte adotada e a atribuição de cada desvio
````

````{role} Analista de Resultados
:id: ROLE-RES
:entrega: DSM1
:status: especificado
:llm: flag
:uses_protocol: PROT-DEL, PROT-QRY

**Responsabilidades (Resp)**

- Montar DRE gerencial, EBITDA, fluxo de caixa e KPIs
- Obter custos e orçamento dos papéis especialistas

**Permissões (Perm)**

- Iniciar query-ref para ROLE-CUS e ROLE-ORC
- Ler ERP e APIs de mercado via MCP

**Obrigações (Obl)**

- Não recalcular rateio próprio — usar o de ROLE-CUS
- Sinalizar inconsistência de fechamento
````

````{role} Auditor de Controles Internos
:id: ROLE-CIN
:entrega: DSM1
:status: especificado
:llm: nao_permitido
:uses_protocol: PROT-DEL, PROT-CMP, PROT-QRY

**Responsabilidades (Resp)**

- Verificar alçada, segregação de funções, duplicidade, conciliação e competência
- Emitir parecer conforme / não conforme com regra e severidade
- Sugerir correções e atestar lançamentos irregulares a outros papéis

**Permissões (Perm)**

- Ler ERP e base normativa via MCP
- Vetar publicação por não conformidade crítica
- Responder query-ref

**Obrigações (Obl)**

- Citar regra e evidência de cada apontamento
- Reavaliar após waiver ou correção
````

````{role} Redator de Relatórios
:id: ROLE-REL
:entrega: DSM1
:status: especificado
:llm: flag
:uses_protocol: PROT-DEL

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
