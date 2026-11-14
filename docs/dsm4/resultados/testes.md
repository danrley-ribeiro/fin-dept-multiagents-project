<!-- gerado por `python -m fin_mas experimento`; não editar à mão -->
Testes bilaterais sobre a média por seed (Wilcoxon pareado) ou sobre execuções (Mann-Whitney). `p (Holm)` é o p ajustado dentro da família; `sig.` marca p (Holm) < 0,05. A diferença é a − b. Efeito: delta de Cliff (desprezível < 0,147; pequeno < 0,33; médio < 0,474; grande acima). Comparações idênticas em todos os pares não são testadas nem entram na correção.

**Família RQ1**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_basico x wf_equivalente, nominal | Classificação correta | 30 | 75,0% | 75,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico x wf_equivalente, nominal | Conformidade correta | 30 | 100,0% | 100,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico x wf_equivalente, nominal | Críticas publicadas sem tratamento | 30 | 0,00 | 0,00 | 0,00 [0,00; 0,00] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico x wf_minimo, nominal | Classificação correta | 30 | 75,0% | 36,7% | 38,3% [23,3%; 53,3%] | 17 | Wilcoxon pareado, exato: 3,0 | 0,0001 | 0,0001 | 0,33 | pequeno | sim |
| sma_basico x wf_minimo, nominal | Conformidade correta | 30 | 100,0% | 100,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico x wf_minimo, nominal | Críticas publicadas sem tratamento | 30 | 0,00 | 0,68 | -0,68 [-0,82; -0,55] | 28 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | -0,93 | grande | sim |
| wf_equivalente x wf_minimo, nominal | Classificação correta | 30 | 75,0% | 36,7% | 38,3% [23,3%; 53,3%] | 17 | Wilcoxon pareado, exato: 3,0 | 0,0001 | 0,0001 | 0,33 | pequeno | sim |
| wf_equivalente x wf_minimo, nominal | Conformidade correta | 30 | 100,0% | 100,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| wf_equivalente x wf_minimo, nominal | Críticas publicadas sem tratamento | 30 | 0,00 | 0,68 | -0,68 [-0,82; -0,55] | 28 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | -0,93 | grande | sim |

**Família RQ2**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_basico x wf_equivalente, perda_baixa | Execução correta | 30 | 94,2% | 100,0% | -5,8% [-11,7%; -0,8%] | 5 | Wilcoxon pareado, exato: 0,0 | 0,0625 | 0,1250 | -0,17 | pequeno | não |
| sma_basico x wf_equivalente, perda_media | Execução correta | 30 | 64,2% | 100,0% | -35,8% [-48,8%; -23,3%] | 19 | Wilcoxon pareado, exato: 0,0 | 0,0000 | 0,0000 | -0,63 | grande | sim |
| sma_basico x wf_equivalente, perda_alta | Execução correta | 30 | 35,0% | 100,0% | -65,0% [-77,1%; -52,5%] | 28 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | -0,93 | grande | sim |
| sma_basico x wf_equivalente, indisponibilidade | Execução correta | 30 | 97,1% | 100,0% | -2,9% [-7,9%; 0,0%] | 2 | Wilcoxon pareado, exato: 0,0 | 0,5000 | 0,5000 | -0,07 | desprezível | não |
| sma_basico x wf_equivalente, humano_lento | Execução correta | 30 | 75,8% | 75,8% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico x wf_equivalente, combinadas | Execução correta | 30 | 50,8% | 75,8% | -25,0% [-37,1%; -14,2%] | 14 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0005 | -0,45 | médio | sim |
| sma_basico x wf_equivalente, combinadas_ataque | Execução correta | 30 | 50,8% | 75,8% | -25,0% [-37,1%; -14,2%] | 14 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0005 | -0,45 | médio | sim |
| sma_basico, perda_baixa x perda_media | Execução correta | 30 | 94,2% | 64,2% | 30,0% [17,5%; 43,3%] | 15 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0004 | 0,51 | grande | sim |
| sma_basico, perda_media x perda_alta | Execução correta | 30 | 64,2% | 35,0% | 29,2% [17,5%; 42,9%] | 15 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0004 | 0,45 | médio | sim |

**Família RQ3**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_basico x wf_equivalente, nominal | Mensagens de coordenação | 30 | 15,75 | 0,88 | 14,87 [14,20; 15,53] | 30 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | 1,00 | grande | sim |
| sma_basico x wf_equivalente, nominal | Latência (ticks) | 30 | 15,89 | 12,71 | 3,18 [2,87; 3,48] | 30 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | 0,89 | grande | sim |
| sma_basico x wf_equivalente, combinadas | Mensagens de coordenação | 30 | 13,60 | 0,64 | 12,96 [11,75; 14,00] | 30 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | 1,00 | grande | sim |
| sma_basico x wf_equivalente, combinadas | Latência (ticks) | 30 | 49,15 | 18,07 | 31,08 [25,02; 37,53] | 30 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | 0,95 | grande | sim |
| controle de acesso ligado x desligado, nominal, porte médio | Mensagens | 30 | 18,70 | 18,67 | 0,03 [0,00; 0,08] | 2 | Wilcoxon pareado, exato: 0,0 | 0,5000 | 1,0000 | 0,01 | desprezível | não |
| controle de acesso ligado x desligado, nominal, porte médio | Latência (ticks) | 30 | 15,88 | 15,88 | 0,00 [0,00; 0,00] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| controle de acesso ligado x desligado, nominal, porte médio | Registros de auditoria | 30 | 141,00 | 140,87 | 0,13 [0,00; 0,33] | 2 | Wilcoxon pareado, exato: 0,0 | 0,5000 | 1,0000 | 0,00 | desprezível | não |

**Família RQ4**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_basico: perda de mensagens x indisponibilidade | Recuperação (ticks) | 30 x 13 seeds | 50,57 | 33 | 17,57 | — | Mann-Whitney, normal: 67,5 | 0,0008 | 0,0016 | 0,65 | grande | sim |
| sma_local x sma_basico, falhas de comunicação | Recuperação (ticks) | 30 x 30 seeds | 53,75 | 49,06 | 4,69 | — | Mann-Whitney, normal: 374,0 | 0,2642 | 0,2642 | 0,17 | pequeno | não |

**Família RQ5-porte**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_basico, nominal, micro x pequena | Classificação correta | 30 | 40,0% | 86,7% | -46,7% [-63,3%; -30,0%] | 14 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0010 | -0,47 | médio | sim |
| sma_basico, nominal, micro x pequena | Mensagens de coordenação | 30 | 15,93 | 15,67 | 0,27 [-0,13; 0,67] | 10 | Wilcoxon pareado, exato: 16,5 | 0,3438 | 1,0000 | 0,06 | desprezível | não |
| sma_basico, nominal, micro x media | Classificação correta | 30 | 40,0% | 86,7% | -46,7% [-63,3%; -30,0%] | 14 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0010 | -0,47 | médio | sim |
| sma_basico, nominal, micro x media | Mensagens de coordenação | 30 | 15,93 | 15,67 | 0,27 [-0,13; 0,67] | 10 | Wilcoxon pareado, exato: 16,5 | 0,3438 | 1,0000 | 0,06 | desprezível | não |
| sma_basico, nominal, micro x grande | Classificação correta | 30 | 40,0% | 86,7% | -46,7% [-63,3%; -30,0%] | 14 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0010 | -0,47 | médio | sim |
| sma_basico, nominal, micro x grande | Mensagens de coordenação | 30 | 15,93 | 15,73 | 0,20 [-0,20; 0,60] | 9 | Wilcoxon pareado, exato: 15,0 | 0,5078 | 1,0000 | 0,05 | desprezível | não |
| sma_basico, nominal, pequena x media | Classificação correta | 30 | 86,7% | 86,7% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico, nominal, pequena x media | Mensagens de coordenação | 30 | 15,67 | 15,67 | 0,00 [0,00; 0,00] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico, nominal, pequena x grande | Classificação correta | 30 | 86,7% | 86,7% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico, nominal, pequena x grande | Mensagens de coordenação | 30 | 15,67 | 15,73 | -0,07 [-0,20; 0,00] | 1 | Wilcoxon pareado, exato: 0,0 | 1,0000 | 1,0000 | -0,01 | desprezível | não |
| sma_basico, nominal, media x grande | Classificação correta | 30 | 86,7% | 86,7% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico, nominal, media x grande | Mensagens de coordenação | 30 | 15,67 | 15,73 | -0,07 [-0,20; 0,00] | 1 | Wilcoxon pareado, exato: 0,0 | 1,0000 | 1,0000 | -0,01 | desprezível | não |

**Família RQ5-parametros**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_basico, combinadas, max_tentativas=1 x max_tentativas=3 | Execução correta | 30 | 36,7% | 63,3% | -26,7% [-40,0%; -15,0%] | 13 | Wilcoxon pareado, exato: 0,0 | 0,0002 | 0,0010 | -0,42 | médio | sim |
| sma_basico, combinadas, prazo_subtarefa=15 x prazo_subtarefa=60 | Latência (ticks) | 30 | 36,55 | 70,12 | -33,57 [-45,15; -23,23] | 20 | Wilcoxon pareado, exato: 0,0 | 0,0000 | 0,0000 | -0,49 | grande | sim |
| sma_basico, combinadas, prazo_aprovacao=10 x prazo_aprovacao=40 | Conclusão | 30 | 20,0% | 33,3% | -13,3% [-26,7%; -3,3%] | 4 | Wilcoxon pareado, exato: 0,0 | 0,1250 | 0,2500 | -0,13 | desprezível | não |
| sma_basico, nominal, limiar_percentual=5 x padrao | Classificação correta | 30 | 86,7% | 86,7% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico, nominal, limiar_percentual=20 x padrao | Classificação correta | 30 | 66,7% | 86,7% | -20,0% [-33,3%; -6,7%] | 6 | Wilcoxon pareado, exato: 0,0 | 0,0312 | 0,0938 | -0,20 | pequeno | não |
| sma_basico, combinadas, ttl_reserva=40 x padrao | Conclusão | 30 | 13,3% | 26,7% | -13,3% [-26,7%; -3,3%] | 4 | Wilcoxon pareado, exato: 0,0 | 0,1250 | 0,2500 | -0,13 | desprezível | não |
| sma_basico, nominal, max_correcoes=0 x padrao | Críticas corrigidas | 30 | 0,00 | 1,33 | -1,33 [-1,63; -1,07] | 27 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | -0,90 | grande | sim |

**Família RQ6**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_basico, combinadas_ataque x combinadas | Execução correta | 30 | 50,8% | 50,8% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_local, combinadas_ataque x combinadas | Execução correta | 30 | 57,9% | 57,9% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |

**Família RQ7**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_local x sma_basico, nominal | Classificação correta | 30 | 75,0% | 75,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_local x sma_basico, perda_baixa | Classificação correta | 30 | 75,0% | 75,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_local x sma_basico, perda_media | Classificação correta | 30 | 75,3% | 72,5% | 2,8% [-1,0%; 10,0%] | 2 | Wilcoxon pareado, exato: 1,0 | 1,0000 | 1,0000 | 0,03 | desprezível | não |
| sma_local x sma_basico, perda_alta | Classificação correta | 29 | 73,7% | 69,8% | 3,8% [0,0%; 11,1%] | 2 | Wilcoxon pareado, exato: 0,0 | 0,5000 | 1,0000 | 0,06 | desprezível | não |
| sma_local x sma_basico, combinadas | Classificação correta | 28 | 79,5% | 78,6% | 0,9% [-8,0%; 10,7%] | 2 | Wilcoxon pareado, exato: 1,0 | 1,0000 | 1,0000 | 0,03 | desprezível | não |
| sma_local x sma_basico, perda (3 níveis), desvio irregular com pista na planilha | Classificação correta | 6 | 41,7% | 30,6% | 11,1% [0,0%; 33,3%] | 1 | Wilcoxon pareado, exato: 0,0 | 1,0000 | 1,0000 | 0,11 | desprezível | não |
| sma_local x sma_basico, perda_media | Mensagens de coordenação | 30 | 16,02 | 15,49 | 0,53 [-0,13; 1,27] | 10 | Wilcoxon pareado, exato: 13,5 | 0,1699 | 0,8496 | 0,06 | desprezível | não |

**Família Ablação**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sem_reenvio x completo, perda_media | Execução correta | 30 | 31,7% | 63,3% | -31,7% [-46,7%; -18,3%] | 13 | Wilcoxon pareado, exato: 0,0 | 0,0002 | 0,0005 | -0,41 | médio | sim |
| sem_reserva x completo, nominal, fechar_mes | Publicações do período | 30 | 2,00 | 1,00 | 1,00 [1,00; 1,00] | 30 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | 1,00 | grande | sim |
| sem_correcao x completo, nominal, fechar_mes | Críticas corrigidas | 30 | 0,00 | 2,00 | -2,00 [-2,30; -1,70] | 30 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | -1,00 | grande | sim |
| sem_negociacao x completo, consulta_instavel, avaliar_orcamento | Classificação correta | 30 | 50,0% | 50,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sem_cognicao_local x completo, consulta_instavel | Classificação correta | 30 | 40,0% | 50,0% | -10,0% [-23,3%; 0,0%] | 3 | Wilcoxon pareado, exato: 0,0 | 0,2500 | 0,2500 | -0,10 | desprezível | não |

**Conferência da biblioteca estatística** (exemplos pequenos, com resultado calculado à mão; o teste de integração confere estes valores)

| Exemplo | Valor calculado pelo código |
|---|---|
| média, desvio amostral e mediana de 2, 4, 4, 4, 5, 5, 7, 9 | 5; 2.13809; 4.5 |
| Wilcoxon exato, diferenças 8, −3, 5, 12, −1, 7, 10, 2 | W− = 4.0; p = 0.0546875 |
| Wilcoxon normal com empates, diferenças 1, 1, 2, −2, 3, 3, −1, 4, 5, 5 | W− = 6.5; z = 2.0991; p = 0.0358 |
| Mann-Whitney exato, x = 19, 22, 16, 29, 24 e y = 20, 11, 17, 12 | U = 17.0 e 3.0; p = 0.111111 |
| o mesmo, aproximação normal | z = 1.5922; p = 0.1113 |
| delta de Cliff dos mesmos x e y | 0.7 (grande) |
| Holm sobre p = 0,01; 0,04; 0,03; 0,005 | 0.03; 0.06; 0.06; 0.02 |
| bootstrap com semente fixa | reprodutível: True; contém a média: True |
