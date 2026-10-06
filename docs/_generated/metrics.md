<!-- ARQUIVO GERADO por tools/trace.py a partir de models/*.yaml — não editar à mão -->

````{metric} Taxa de conclusão de solicitações
:id: MET-01
:entrega: DSM1
:status: especificado
:measures: REQ-F01

**Fórmula:** solicitações com resposta final explícita (inform ou failure justificado) / total  
**Alvo:** >= 95% nos cenários controlados
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
