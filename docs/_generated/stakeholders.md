<!-- ARQUIVO GERADO por tools/trace.py a partir de models/*.yaml — não editar à mão -->

````{stk} CFO / Diretoria contratante
:id: STK-01
:entrega: DSM1
:status: especificado

**Interesse:** Resultado do período confiável, no prazo, e insights para decisão.

**Restrições:** Não aceita números divergentes entre relatório e DRE.
````

````{stk} Controller humano (aprovador)
:id: STK-02
:entrega: DSM1
:status: especificado

**Interesse:** Revisar e aprovar ações restritas e publicações (human-in-the-loop).

**Restrições:** Toda ação com efeito externo passa por sua aprovação explícita.
````

````{stk} Contabilidade da empresa cliente
:id: STK-03
:entrega: DSM1
:status: especificado

**Interesse:** Receber apontamentos e ajustes propostos com justificativa.

**Restrições:** É a autoridade sobre o razão contábil no ERP.
````

````{stk} Auditoria interna / externa
:id: STK-04
:entrega: DSM1
:status: especificado

**Interesse:** Trilha completa de decisões, critérios, fontes e aprovações.

**Restrições:** Evidência reconstruível por identificador de conversa.
````

````{stk} TI, Segurança da Informação e DPO (LGPD)
:id: STK-05
:entrega: DSM1
:status: especificado

**Interesse:** Sigilo de dados financeiros, minimização e retenção de dados pessoais.

**Restrições:** Nenhum segredo ou dado pessoal desnecessário em logs e memória.
````

````{stk} Equipe de desenvolvimento (autores)
:id: STK-06
:entrega: DSM1
:status: especificado

**Interesse:** Rastreabilidade entre requisito, modelo, código e teste.

**Restrições:** Execução offline e reprodutível, sem API paga obrigatória.
````

````{stk} Avaliador da disciplina (INE5628)
:id: STK-07
:entrega: DSM1
:status: especificado

**Interesse:** Evidência verificável e reprodutível de cada critério.

**Restrições:** Documentação e autoria explícitas, incluindo uso de IA.
````
