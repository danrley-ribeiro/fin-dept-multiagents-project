````{agent} Orquestrador
:id: AG-ORQ
:entrega: DSM1
:status: especificado
:llm: nao_permitido
:realizes: ROLE-ORQ
:pursues: G-01
:uses_resource: ENV-UI, ENV-PER

**Cognição:** Reativo a protocolos + biblioteca de planos (intenção → DAG)  
**LLM:** nao_permitido

**Percepções**

- Solicitação do usuário (intenção, competência, entidade)
- Mensagens agree/refuse/inform/failure dos especialistas
- Parecer e veto do Agente de Controles Internos
- Decisão do Approval Gate

**Estado interno (crenças)**

- DAG de subtarefas e status por conversation_id
- Reserva de período ativa
- Relógio lógico e prazos reply_by

**Conhecimento**

- Catálogo de intenções e planos (fechar mês, avaliar orçamento)
- Diretório de papéis e Agent Cards

**Ações**

- Enviar request a especialistas
- Reservar e liberar período
- Solicitar verificação de conformidade
- Propor publicação ao Approval Gate
- Entregar resposta final ou falha explícita

**Por que é agente:** Única fronteira com o usuário; mantém compromissos e prazos de várias conversas em paralelo.
````

````{agent} Agente de Custos
:id: AG-CUS
:entrega: DSM1
:status: especificado
:llm: nao_permitido
:realizes: ROLE-CUS
:pursues: G-02
:uses_resource: ENV-ERP, ENV-BD

**Cognição:** Deliberativo determinístico (regras de rateio + cálculo)  
**LLM:** nao_permitido

**Percepções**

- Request de apuração (competência, entidade, dimensão)
- Query-ref do Agente de Resultados
- Balancete e lançamentos via MCP

**Estado interno (crenças)**

- Custos apurados do período e versão do rateio aplicado
- Pendências de dados de origem

**Conhecimento**

- Critérios de rateio e classificação fixo/variável
- Memória aprovada de ciclos anteriores

**Ações**

- Calcular margem de contribuição e rentabilidade
- Responder inform com proveniência
- Responder failure com dado ausente

**Por que é agente:** Mantém estado de custos por período e responde a vários consumidores sob seus próprios critérios.
````

````{agent} Agente de Orçamento
:id: AG-ORC
:entrega: DSM1
:status: especificado
:llm: flag
:realizes: ROLE-ORC
:pursues: G-03
:uses_resource: ENV-PLN, ENV-ERP, ENV-TOK

**Cognição:** BDI deliberativo: crenças por conta e fonte, desejos gerados das crenças (fonte confiável, explicar desvio, alertar, encaminhar a controle, forecast, consolidar), biblioteca de planos com utilidade, replanejamento na falha e reconsideração por revisão de crença. Desde a DSM3, com cognição local ou LLM, recebe hipóteses validadas sobre a causa dos desvios e busca a evidência que as confirma ou refuta (desejo epistêmico verificar_hipotese), negociando prazo se preciso  
**LLM:** flag — Propostas de hipótese (validadas e verificadas antes de mudar qualquer crença) e narrativa dos desvios (sem gerar números)

**Percepções**

- Request de avaliação orçamentária
- Query-ref do Agente de Resultados
- Orçado e realizado via MCP (planilha e ERP)
- Inform do Agente de Controles Internos sobre lançamentos contestados
- Timeout da própria consulta
- Texto livre da planilha de orçamento e histórico mensal por conta (só com cognição local ou LLM)
- Resposta do Orquestrador a uma proposta de prazo

**Estado interno (crenças)**

- Crenças por conta (orçado, realizado por fonte, desvio bruto e ajustado, classificação)
- Desejos e intenções ativas, suspensas e abandonadas
- Forecast do trimestre e premissas

**Conhecimento**

- Limiar de desvio (% e R$), método de forecast e fonte primária do realizado
- Biblioteca de planos e pesos dos desejos permanentes (precisão, tempestividade)
- Memória aprovada de justificativas de desvio

**Ações**

- Sinalizar desvio acima do limiar
- Consultar o Agente de Controles Internos (query-ref)
- Reclassificar desvio como problema de controle
- Verificar uma hipótese (nova consulta, cálculo sobre o histórico) ou arquivá-la
- Propor extensão de prazo ao Orquestrador
- Projetar forecast
- Propor alteração de orçamento (restrita)

**Por que é agente:** Decide autonomamente o que é desvio relevante sob limiares próprios e propõe correções.
````

````{agent} Agente de Resultados
:id: AG-RES
:entrega: DSM1
:status: especificado
:llm: flag
:realizes: ROLE-RES
:pursues: G-04
:uses_resource: ENV-ERP, ENV-API, ENV-TOK

**Cognição:** Determinístico (DRE, EBITDA, DFC, KPIs) com comentário LLM opcional  
**LLM:** flag — Comentário analítico sobre a variação dos indicadores

**Percepções**

- Request de consolidação de resultado
- Inform de custos (AG-CUS) e de orçamento (AG-ORC)
- Índices de mercado via MCP

**Estado interno (crenças)**

- DRE e KPIs em construção e pendências de insumos

**Conhecimento**

- Estrutura da DRE gerencial e fórmulas de KPIs
- Memória aprovada de fechamentos anteriores

**Ações**

- Enviar query-ref a AG-CUS e AG-ORC
- Consolidar DRE, EBITDA, DFC e KPIs
- Informar resultado ao Orquestrador

**Por que é agente:** Depende de informação de outros agentes (dependência de informação) e decide quando o resultado está completo.
````

````{agent} Agente de Controles Internos
:id: AG-CIN
:entrega: DSM1
:status: especificado
:llm: nao_permitido
:realizes: ROLE-CIN
:pursues: G-05
:uses_resource: ENV-ERP, ENV-NRM

**Cognição:** BDI com regras simbólicas: crenças por lançamento, desejos permanentes concorrentes (conformidade x prazo), seleção explícita entre aprovar, apontar, vetar com correção e vetar por utilidade, e reconsideração após correção ou waiver  
**LLM:** nao_permitido

**Percepções**

- Request de verificação do pacote de fechamento
- Lançamentos, aprovadores e conciliações via MCP
- Waiver ou correção informados pelo Orquestrador

**Estado interno (crenças)**

- Crenças sobre conformidade de cada lançamento e correções percebidas
- Intenções ativas e suspensas (aprovar, apontar, vetar com correção, vetar)

**Conhecimento**

- Regras de alçada, SoD, duplicidade e competência (base normativa)

**Ações**

- Emitir parecer conforme / não conforme
- Vetar publicação por não conformidade crítica
- Sugerir correções (reaprovar, estornar, reclassificar)
- Responder query-ref sobre lançamentos irregulares por conta
- Reavaliar após correção

**Por que é agente:** Autonomia de veto — sua decisão muda o espaço de opções do Orquestrador e do Agente de Relatórios.
````

````{agent} Agente de Relatórios
:id: AG-REL
:entrega: DSM1
:status: especificado
:llm: flag
:realizes: ROLE-REL
:pursues: G-06
:uses_resource: ENV-TOK, ENV-UI

**Cognição:** Template determinístico + LLM opcional (híbrido)  
**LLM:** flag — Síntese executiva e insights orientados à decisão (números vindos do núcleo)

**Percepções**

- Request de relatório com resultados consolidados e parecer de conformidade
- Memória aprovada relevante

**Estado interno (crenças)**

- Rascunho do relatório e versão do template

**Conhecimento**

- Templates de relatório executivo
- Memória aprovada (embeddings e grafo)

**Ações**

- Gerar relatório por template
- Gerar narrativa LLM (se flag ativa) e validar números
- Propor publicação (restrita)

**Por que é agente:** Única unidade que decide como comunicar à liderança; possui modo de operação configurável e fallback próprio.
````
