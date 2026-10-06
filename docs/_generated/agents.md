<!-- ARQUIVO GERADO por tools/trace.py a partir de models/*.yaml — não editar à mão -->

````{agent} Orquestrador (Controladoria Master)
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
- Parecer e veto de Controles Internos
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

````{agent} Agente de Custos e Rentabilidade
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
- Query-ref de Resultados
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

````{agent} Agente de Orçamento e Controle Orçamentário
:id: AG-ORC
:entrega: DSM1
:status: especificado
:llm: flag
:realizes: ROLE-ORC
:pursues: G-03
:uses_resource: ENV-PLN, ENV-ERP, ENV-TOK

**Cognição:** Determinístico (variância + forecast) com narrativa LLM opcional  
**LLM:** flag — Narrativa explicativa dos desvios (sem gerar números)

**Percepções**

- Request de avaliação orçamentária
- Query-ref de Resultados
- Orçado e realizado via MCP

**Estado interno (crenças)**

- Desvios por conta e centro de custo
- Forecast do trimestre e premissas

**Conhecimento**

- Limiar de desvio (% e R$) e método de forecast
- Memória aprovada de justificativas de desvio

**Ações**

- Sinalizar desvio acima do limiar
- Projetar forecast
- Propor alteração de orçamento (restrita)

**Por que é agente:** Decide autonomamente o que é desvio relevante sob limiares próprios e propõe correções.
````

````{agent} Agente de Resultados e Indicadores
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
- Inform de custos (CUS) e de orçamento (ORC)
- Índices de mercado via MCP

**Estado interno (crenças)**

- DRE e KPIs em construção e pendências de insumos

**Conhecimento**

- Estrutura da DRE gerencial e fórmulas de KPIs
- Memória aprovada de fechamentos anteriores

**Ações**

- Enviar query-ref a CUS e ORC
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

**Cognição:** BDI com regras simbólicas (crenças sobre lançamentos, intenção de vetar)  
**LLM:** nao_permitido

**Percepções**

- Request de verificação do pacote de fechamento
- Lançamentos, aprovadores e conciliações via MCP
- Waiver ou correção informados pelo Orquestrador

**Estado interno (crenças)**

- Crenças sobre conformidade de cada lançamento
- Intenções ativas (aprovar, apontar, vetar)

**Conhecimento**

- Regras de alçada, SoD, duplicidade e competência (base normativa)

**Ações**

- Emitir parecer conforme / não conforme
- Vetar publicação por não conformidade crítica
- Reavaliar após correção

**Por que é agente:** Autonomia de veto — sua decisão muda o espaço de opções do Orquestrador e de Relatórios.
````

````{agent} Agente de Relatórios Gerenciais e Análises
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
