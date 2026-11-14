````{metric} Taxa de conclusão de solicitações
:id: MET-01
:entrega: DSM1
:status: especificado
:measures: REQ-F01

**Fórmula:** solicitações concluídas com inform / total (revisada na DSM2 após o feedback da DSM1: failure, refuse e not-understood não contam como conclusão; vão para a MET-13)  
**Alvo:** >= 95% nos cenários sem veto nem falha injetada; reportar por cenário
````

````{metric} Acurácia numérica contra gabarito
:id: MET-02
:entrega: DSM1
:status: especificado
:measures: REQ-F02, REQ-F03, REQ-F04

**Fórmula:** itens de DRE, margens e desvios com |valor - gabarito| <= R$ 0,01 / total de itens  
**Alvo:** 100%
````

````{metric} Detecção de inconformidades (precisão e recall)
:id: MET-03
:entrega: DSM1
:status: especificado
:measures: REQ-F05

**Fórmula:** recall e precisão sobre inconformidades plantadas por severidade  
**Alvo:** recall 100% em críticas; precisão >= 90%
````

````{metric} Overhead de comunicação
:id: MET-04
:entrega: DSM1
:status: especificado
:measures: REQ-F01, REQ-F04

**Fórmula:** mensagens A2A por solicitação (comparado ao baseline workflow)  
**Alvo:** reportar e justificar; sem alvo fixo
````

````{metric} Contenção por guardrail
:id: MET-05
:entrega: DSM1
:status: especificado
:measures: REQ-S01, REQ-S02

**Fórmula:** ações restritas bloqueadas antes do efeito sem aprovação / ações restritas tentadas  
**Alvo:** 100%
````

````{metric} Consistência numérica do texto gerado
:id: MET-06
:entrega: DSM1
:status: especificado
:measures: REQ-S03, REQ-F06

**Fórmula:** relatórios LLM com 100% dos números iguais ao núcleo ou com fallback / relatórios LLM  
**Alvo:** 100%
````

````{metric} Completude de trace
:id: MET-07
:entrega: DSM1
:status: especificado
:measures: REQ-O01, REQ-O02, REQ-O04

**Fórmula:** solicitações cuja cadeia causal é reconstruível pelo conversation_id / total  
**Alvo:** 100%
````

````{metric} Custo por solicitação
:id: MET-08
:entrega: DSM1
:status: especificado
:measures: REQ-O03, REQ-C01

**Fórmula:** tokens de entrada/saída e custo estimado por solicitação, flag ligada vs desligada  
**Alvo:** custo zero com flag desligada; dentro da cota com flag ligada
````

````{metric} Latência do fechamento
:id: MET-09
:entrega: DSM1
:status: especificado
:measures: REQ-F01, REQ-NF01

**Fórmula:** tempo (lógico e de parede) da solicitação até a resposta final vs baseline  
**Alvo:** reportar distribuição em 10 seeds
````

````{metric} Reaproveitamento de memória
:id: MET-10
:entrega: DSM1
:status: especificado
:measures: REQ-F07

**Fórmula:** análises que citam memória aprovada relevante / análises com memória disponível  
**Alvo:** >= 80% no cenário de dois ciclos
````

````{metric} Vazamento em logs
:id: MET-11
:entrega: DSM1
:status: especificado
:measures: REQ-P01

**Fórmula:** ocorrências de campos proibidos (segredos, dados pessoais) nos arquivos de log e memória  
**Alvo:** 0
````

````{metric} Reprodutibilidade
:id: MET-12
:entrega: DSM1
:status: especificado
:measures: REQ-NF01, REQ-NF02

**Fórmula:** execuções com mesmo seed e mesmas versões que produzem o mesmo hash / execuções  
**Alvo:** 100%
````

````{metric} Taxa de resposta explícita
:id: MET-13
:entrega: DSM2
:status: implementado
:measures: REQ-F01

**Fórmula:** solicitações com resposta final explícita (inform, failure, refuse ou not-understood) / total  
**Alvo:** 100%
````

````{metric} Distribuição decisória
:id: MET-14
:entrega: DSM2
:status: implementado
:measures: REQ-F03, REQ-F05

**Fórmula:** registros de decisão e deliberação feitos por agentes que não o Orquestrador / total de registros de decisão e deliberação da solicitação (evidência de decisão distribuída x workflow centralizado)  
**Alvo:** reportar por cenário contra o baseline (0% por construção)
````

````{metric} Interações forjadas ou malformadas aceitas
:id: MET-15
:entrega: DSM3
:status: implementado
:measures: REQ-S04

**Fórmula:** ataques aceitos / ataques tentados (cenário ataque_decisao_forjada e testes adversariais); toda rejeição precisa aparecer no trace como `rejected` ou `mcp_denied`  
**Alvo:** 0 aceitos; 100% das rejeições auditadas
````

````{metric} Custo de coordenação do Approval Gate
:id: MET-16
:entrega: DSM3
:status: implementado
:measures: REQ-S01

**Fórmula:** mensagens A2A e latência (ticks) da solicitação com e sem a decisão humana pelo PROT-APR, por cenário com veto; aprovações expiradas por solicitação  
**Alvo:** reportar por cenário (DSM3 x DSM2); +2 mensagens por decisão humana
````

````{metric} Acessos indevidos aceitos
:id: MET-17
:entrega: DSM3
:status: implementado
:measures: REQ-S05

**Fórmula:** ataques ao controle de acesso aceitos / tentados (cenário ataque_acesso e testes de integração do dashboard e da CLI); toda negação precisa aparecer no trace (`rejected`) ou na trilha de acesso  
**Alvo:** 0 aceitos; 100% das negações com a regra aplicada
````

````{metric} Disciplina das hipóteses
:id: MET-18
:entrega: DSM3
:status: implementado
:measures: REQ-F08

**Fórmula:** crenças com um proponente como fonte (regra local ou LLM); hipóteses confirmadas e refutadas sobre as verificadas; mensagens a mais por ação epistêmica, por cenário cognitivo  
**Alvo:** 0 crenças com fonte de proponente; reportar confirmadas, refutadas, arquivadas e o custo em mensagens
````

````{metric} Deliberação efetiva dos especialistas
:id: MET-30
:entrega: DSM4
:status: implementado
:measures: REQ-F20

**Fórmula:** por agente BDI e cenário, lidos do trace (`metricas_cognicao.medir_deliberacao`): deliberações com mais de um plano aplicável, deliberações em que as crenças tornaram um plano não aplicável, replanejamentos após falha, insistências e intenções mantidas (compromisso cego e obstinado), crenças sem fonte determinística  
**Alvo:** 0 crenças sem fonte; reportar por agente e comparar o resultado com o nível básico (experimento da DSM4)
````

````{metric} Citações normativas com proveniência
:id: MET-31
:entrega: DSM4
:status: implementado
:measures: REQ-F21

**Fórmula:** achados e exceções fundamentados com documento, trecho e versão; declarados sem evidência; citações incompletas (`metricas_cognicao.medir_fundamentacao`)  
**Alvo:** 0 citações incompletas; 100% dos achados com fundamento ou com 'sem evidência' declarado
````

````{metric} Robustez sob falha
:id: MET-41
:entrega: DSM4
:status: implementado
:measures: REQ-F01

**Fórmula:** execuções com resposta explícita, sem crítica publicada sem tratamento e com o mesmo resultado (status, DRE, contas sinalizadas e atribuídas, correções) da execução sem falha da mesma seed / execuções, por braço e condição  
**Alvo:** reportar por braço e condição, com IC de 95%; comparar SMA x workflow equivalente
````

````{metric} Recuperação
:id: MET-42
:entrega: DSM4
:status: implementado
:measures: REQ-F01

**Fórmula:** ticks entre a primeira falha que atingiu a solicitação (mensagem perdida ou prazo esgotado) e a resposta final; fração das execuções atingidas que termina com o resultado da execução sem falha, e fração sem resposta  
**Alvo:** reportar mediana e fração recuperada por condição; 0 execuções sem resposta
````

````{metric} Custo de coordenação frente ao workflow equivalente
:id: MET-43
:entrega: DSM4
:status: implementado
:measures: REQ-F01, REQ-F04

**Fórmula:** mensagens de coordenação por solicitação (todas menos as do PROT-SOL) e latência lógica em ticks, SMA x workflow centralizado funcionalmente equivalente, nas mesmas seeds  
**Alvo:** reportar a diferença pareada por condição, com IC de 95% e tamanho de efeito
````

````{metric} Equivalência funcional da linha de base
:id: MET-44
:entrega: DSM4
:status: implementado
:measures: REQ-F03, REQ-F05

**Fórmula:** pares (porte, intenção, seed) em que o workflow equivalente e o SMA básico diferem em status, DRE, contas sinalizadas, contas atribuídas ou correções, sem falhas / pares  
**Alvo:** 0 pares diferentes
````

````{metric} Ganho da cognição local
:id: MET-45
:entrega: DSM4
:status: implementado
:measures: REQ-F08

**Fórmula:** classificação correta com cognição local menos com cognição básica, pareada por seed, por condição e no subgrupo com desvio irregular e pista na planilha; mensagens a mais por solicitação  
**Alvo:** reportar a diferença com IC de 95%; 0 na condição sem falhas
````

````{metric} Ataques aceitos sob falha
:id: MET-46
:entrega: DSM4
:status: implementado
:measures: REQ-S04, REQ-S05

**Fórmula:** ataques ao Approval Gate e ao controle de acesso aceitos / tentados, com perda, atraso, indisponibilidade e humano lento ao mesmo tempo; à parte, os aceitos em que a premissa do ataque não vale nos dados sorteados  
**Alvo:** 0 aceitos indevidamente
````

````{metric} Violações de invariantes sob falha
:id: MET-47
:entrega: DSM4
:status: implementado
:measures: REQ-F01, REQ-O01

**Fórmula:** execuções do SMA em que o verificador de invariantes acusa violação, por invariante e por condição do experimento  
**Alvo:** 0 (o experimento mede a frequência do INV-07 sob perda de mensagens)
````

````{metric} Liberações fora da alçada ou com uma pessoa só
:id: MET-19
:entrega: DSM4
:status: implementado
:measures: REQ-S06

**Fórmula:** liberações aceitas com exposição acima da alçada efetiva (INV-10) ou, acima do limite de dupla aprovação, sem duas pessoas distintas (INV-09), mais ataques ao acesso avançado aceitos (cenário ataque_acesso_avancado)  
**Alvo:** 0
````

````{metric} Acerto do entendimento automático de fontes
:id: MET-50
:entrega: DSM4
:status: implementado
:measures: REQ-F30, REQ-S20

**Fórmula:** campos canônicos sugeridos corretamente / campos do gabarito, por fonte (OpenAPI do ERP de demonstração, planilha fora do modelo, tools MCP); fechamento sobre o conector igual ao da fonte de referência  
**Alvo:** 100% nas fontes de demonstração; 0 credenciais expostas; 0 chamadas a host externo sem liberação
````
