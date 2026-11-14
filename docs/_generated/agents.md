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
:uses_resource: ENV-ERP, ENV-BD, ENV-SEG

**Cognição:** Dois níveis (ADR-010). Básico: reativo determinístico (rateio fixo + cálculo), mantido como braço de comparação. Local e llm: BDI, com crenças sobre o direcionador de rateio do período (ok, ausente, inconsistente) e a receita por unidade, desejo de definir o critério de rateio e quatro planos alternativos (padrão, última tabela aprovada, proporcional à receita, igualitário) escolhidos pela utilidade de precisão e simplicidade do porte; o plano padrão falha ao perceber um direcionador inutilizável e o agente replaneja  
**LLM:** nao_permitido

**Percepções**

- Request de apuração (competência, entidade, dimensão)
- Query-ref do Agente de Resultados (custos por UN; custos fixos por centro, na variante BDI)
- Balancete e lançamentos via MCP
- Direcionadores de rateio do período e perfil cognitivo do porte via MCP (só na variante BDI)

**Estado interno (crenças)**

- Custos apurados do período e versão do rateio aplicado
- Pendências de dados de origem
- Crenças sobre o direcionador, critério de rateio adotado e motivo (variante BDI)

**Conhecimento**

- Critérios de rateio e classificação fixo/variável
- Última tabela de rateio aprovada (rateio-v1) e pesos dos desejos permanentes (precisão, simplicidade)

**Ações**

- Calcular margem de contribuição e rentabilidade
- Escolher o critério de rateio e registrar o critério e o motivo (proveniência, decisão e ressalva)
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
- Correções aprovadas de competências anteriores (SVC-MEM, só leitura; só com cognição local ou LLM)
- Confiança aprendida de cada regra local (SVC-APD)

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

**Cognição:** Dois níveis (ADR-010). Básico: reativo determinístico (DRE, EBITDA, KPIs), mantido como braço de comparação. Local e llm: BDI, com crenças sobre a situação de cada insumo e sobre a variação do EBITDA% contra o histórico; desejos de obter insumo, explicar variação relevante e consolidar; replanejamento quando um especialista não responde (consultar de novo, dar por indisponível) e escolha entre consolidar com ressalva e falhar explicitamente pela criticidade do insumo e pelo porte; hipóteses de regras locais sobre a causa da variação, verificadas com o AG-CUS ou no histórico antes de virar explicação  
**LLM:** flag — Comentário analítico sobre os indicadores, rotulado como texto de modelo e conferido contra os números

**Percepções**

- Request de consolidação de resultado
- Inform de custos (AG-CUS) e de orçamento (AG-ORC); timeout, recusa ou falha das consultas
- Índices de mercado via MCP
- Histórico de resultado e perfil cognitivo do porte via MCP (só na variante BDI)
- Correções aprovadas de competências anteriores (SVC-MEM, só leitura, na variante BDI)

**Estado interno (crenças)**

- DRE e KPIs em construção e pendências de insumos
- Crenças, desejos, intenções e hipóteses sobre a variação (variante BDI)

**Conhecimento**

- Estrutura da DRE gerencial e fórmulas de KPIs
- Memória aprovada de fechamentos anteriores (correções)
- Biblioteca de planos e pesos dos desejos permanentes (completude, tempestividade, explicabilidade)

**Ações**

- Enviar query-ref a AG-CUS e AG-ORC, e repetir a consulta que expirou se couber no prazo
- Pedir ao AG-CUS o detalhe de custos fixos por centro para verificar uma hipótese
- Consolidar DRE, EBITDA, DFC e KPIs, com ressalva quando falta insumo não crítico
- Informar resultado ao Orquestrador ou falhar explicitamente

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
- Trechos da base normativa com documento, trecho e versão (tool normas.buscar; fora do nível básico)

**Estado interno (crenças)**

- Crenças sobre conformidade de cada lançamento e correções percebidas
- Fundamento normativo de cada regra violada, ou a declaração de que não há evidência
- Intenções ativas e suspensas (aprovar, apontar, vetar com correção, vetar)

**Conhecimento**

- Regras de alçada, SoD, duplicidade e competência (base normativa)

**Ações**

- Emitir parecer conforme / não conforme
- Vetar publicação por não conformidade crítica
- Sugerir correções (reaprovar, estornar, reclassificar)
- Responder query-ref sobre lançamentos irregulares por conta
- Reavaliar após correção
- Citar o trecho da base normativa que fundamenta cada achado, ou declarar "sem evidência"

**Por que é agente:** Autonomia de veto — sua decisão muda o espaço de opções do Orquestrador e do Agente de Relatórios.
````

````{agent} Agente de Relatórios
:id: AG-REL
:entrega: DSM1
:status: especificado
:llm: flag
:realizes: ROLE-REL
:pursues: G-06
:uses_resource: ENV-TOK, ENV-UI, ENV-NRM

**Cognição:** Dois níveis (ADR-010). Básico: template determinístico único + LLM opcional, mantido como braço de comparação. Local e llm: BDI, com crenças sobre o que o período teve (correções, waivers, ressalvas, desvios, insights) e sobre o público; desejo de comunicar e três planos de estrutura (relatório de exceção, sumário executivo, relatório completo) escolhidos pela utilidade de clareza, completude e concisão do porte. O texto continua saindo de template determinístico  
**LLM:** flag — Síntese executiva ao fim do relatório, rotulada como texto de modelo (números vindos do núcleo)

**Percepções**

- Request de relatório com resultados consolidados e parecer de conformidade
- Memória aprovada relevante (correções de competências anteriores, só leitura, na variante BDI)
- Perfil cognitivo do porte e trechos da base normativa via MCP (só na variante BDI)

**Estado interno (crenças)**

- Rascunho do relatório e versão do template
- Crenças sobre os achados do período, público e base normativa das exceções (variante BDI)

**Conhecimento**

- Templates de relatório executivo, de exceção e de sumário
- Memória aprovada (correções)
- Pesos dos desejos permanentes (clareza, completude, concisão)

**Ações**

- Escolher a estrutura do relatório, a ordem das ressalvas e os insights a incluir
- Gerar relatório por template
- Citar a base normativa de cada exceção ou declarar que não há evidência
- Gerar narrativa LLM (se flag ativa) e validar números
- Propor publicação (restrita)

**Por que é agente:** Única unidade que decide como comunicar à liderança; possui modo de operação configurável e fallback próprio.
````
