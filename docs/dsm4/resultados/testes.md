<!-- gerado por `python -m fin_mas experimento`; não editar à mão -->
Testes bilaterais sobre a média por seed (Wilcoxon pareado) ou sobre execuções (Mann-Whitney). `p (Holm)` é o p ajustado dentro da família; `sig.` marca p (Holm) < 0,05. A diferença é a − b. Efeito: delta de Cliff (desprezível < 0,147; pequeno < 0,33; médio < 0,474; grande acima).

**Família RQ1**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_basico x wf_equivalente, nominal | Classificação correta | 30 | 75,0% | 75,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico x wf_equivalente, nominal | Conformidade correta | 30 | 100,0% | 100,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico x wf_equivalente, nominal | Críticas publicadas sem tratamento | 30 | 0,00 | 0,00 | 0,00 [0,00; 0,00] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico x wf_minimo, nominal | Classificação correta | 30 | 75,0% | 36,7% | 38,3% [23,3%; 53,3%] | 17 | Wilcoxon pareado, exato: 3,0 | 0,0001 | 0,0004 | 0,33 | pequeno | sim |
| sma_basico x wf_minimo, nominal | Conformidade correta | 30 | 100,0% | 100,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico x wf_minimo, nominal | Críticas publicadas sem tratamento | 30 | 0,00 | 0,68 | -0,68 [-0,82; -0,55] | 28 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | -0,93 | grande | sim |
| wf_equivalente x wf_minimo, nominal | Classificação correta | 30 | 75,0% | 36,7% | 38,3% [23,3%; 53,3%] | 17 | Wilcoxon pareado, exato: 3,0 | 0,0001 | 0,0004 | 0,33 | pequeno | sim |
| wf_equivalente x wf_minimo, nominal | Conformidade correta | 30 | 100,0% | 100,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| wf_equivalente x wf_minimo, nominal | Críticas publicadas sem tratamento | 30 | 0,00 | 0,68 | -0,68 [-0,82; -0,55] | 28 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | -0,93 | grande | sim |

**Família RQ2**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_basico x wf_equivalente, perda_baixa | Execução correta | 30 | 80,0% | 100,0% | -20,0% [-32,5%; -8,8%] | 10 | Wilcoxon pareado, exato: 0,0 | 0,0020 | 0,0059 | -0,33 | médio | sim |
| sma_basico x wf_equivalente, perda_media | Execução correta | 30 | 48,8% | 100,0% | -51,2% [-64,2%; -37,5%] | 24 | Wilcoxon pareado, exato: 0,0 | 0,0000 | 0,0000 | -0,80 | grande | sim |
| sma_basico x wf_equivalente, perda_alta | Execução correta | 30 | 22,5% | 100,0% | -77,5% [-86,7%; -69,2%] | 30 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | -1,00 | grande | sim |
| sma_basico x wf_equivalente, indisponibilidade | Execução correta | 30 | 92,1% | 100,0% | -7,9% [-15,0%; -1,7%] | 5 | Wilcoxon pareado, exato: 0,0 | 0,0625 | 0,1250 | -0,17 | pequeno | não |
| sma_basico x wf_equivalente, humano_lento | Execução correta | 30 | 75,8% | 75,8% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico x wf_equivalente, combinadas | Execução correta | 30 | 45,4% | 75,8% | -30,4% [-43,8%; -17,9%] | 15 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0004 | -0,51 | grande | sim |
| sma_basico x wf_equivalente, combinadas_ataque | Execução correta | 30 | 45,4% | 75,8% | -30,4% [-43,8%; -17,9%] | 15 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0004 | -0,51 | grande | sim |
| sma_basico, perda_baixa x perda_media | Execução correta | 30 | 80,0% | 48,8% | 31,2% [17,5%; 45,8%] | 17 | Wilcoxon pareado, exato: 4,5 | 0,0001 | 0,0005 | 0,49 | grande | sim |
| sma_basico, perda_media x perda_alta | Execução correta | 30 | 48,8% | 22,5% | 26,2% [16,7%; 36,2%] | 15 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0004 | 0,40 | médio | sim |

**Família RQ3**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_basico x wf_equivalente, nominal | Mensagens de coordenação | 30 | 15,75 | 0,88 | 14,87 [14,20; 15,53] | 30 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | 1,00 | grande | sim |
| sma_basico x wf_equivalente, nominal | Latência (ticks) | 30 | 15,89 | 12,71 | 3,18 [2,87; 3,48] | 30 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | 0,89 | grande | sim |
| sma_basico x wf_equivalente, combinadas | Mensagens de coordenação | 30 | 12,32 | 0,64 | 11,68 [10,38; 12,92] | 30 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | 1,00 | grande | sim |
| sma_basico x wf_equivalente, combinadas | Latência (ticks) | 28 | 43,70 | 17,95 | 25,75 [18,25; 33,60] | 26 | Wilcoxon pareado, normal: 3,0 | 0,0000 | 0,0000 | 0,77 | grande | sim |
| controle de acesso ligado x desligado, nominal, porte médio | Mensagens | 30 | 18,67 | 18,67 | 0,00 [0,00; 0,00] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| controle de acesso ligado x desligado, nominal, porte médio | Latência (ticks) | 30 | 15,88 | 15,88 | 0,00 [0,00; 0,00] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| controle de acesso ligado x desligado, nominal, porte médio | Registros de auditoria | 30 | 140,87 | 140,87 | 0,00 [0,00; 0,00] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |

**Família RQ4**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_basico: perda de mensagens x indisponibilidade | Recuperação (ticks) | 311 x 45 | 44,21 | 36,98 | 7,23 | — | Mann-Whitney, normal: 5624,0 | 0,0330 | 0,0661 | 0,20 | pequeno | não |
| sma_local x sma_basico, falhas de comunicação | Recuperação (ticks) | 497 x 492 | 44,98 | 44,14 | 0,84 | — | Mann-Whitney, normal: 119939,5 | 0,6047 | 0,6047 | 0,02 | desprezível | não |

**Família RQ5-porte**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_basico, nominal, micro x pequena | Classificação correta | 30 | 40,0% | 86,7% | -46,7% [-63,3%; -30,0%] | 14 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0015 | -0,47 | médio | sim |
| sma_basico, nominal, micro x pequena | Mensagens de coordenação | 30 | 15,93 | 15,67 | 0,27 [-0,13; 0,67] | 10 | Wilcoxon pareado, exato: 16,5 | 0,3438 | 1,0000 | 0,06 | desprezível | não |
| sma_basico, nominal, micro x media | Classificação correta | 30 | 40,0% | 86,7% | -46,7% [-63,3%; -30,0%] | 14 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0015 | -0,47 | médio | sim |
| sma_basico, nominal, micro x media | Mensagens de coordenação | 30 | 15,93 | 15,67 | 0,27 [-0,13; 0,67] | 10 | Wilcoxon pareado, exato: 16,5 | 0,3438 | 1,0000 | 0,06 | desprezível | não |
| sma_basico, nominal, micro x grande | Classificação correta | 30 | 40,0% | 86,7% | -46,7% [-63,3%; -30,0%] | 14 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0015 | -0,47 | médio | sim |
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
| sma_basico, combinadas, max_tentativas=1 x max_tentativas=3 | Execução correta | 30 | 36,7% | 50,0% | -13,3% [-21,7%; -6,7%] | 8 | Wilcoxon pareado, exato: 0,0 | 0,0078 | 0,0391 | -0,21 | pequeno | sim |
| sma_basico, combinadas, prazo_subtarefa=15 x prazo_subtarefa=60 | Latência (ticks) | 28 | 33,38 | 58,34 | -24,96 [-37,36; -14,20] | 15 | Wilcoxon pareado, exato: 0,0 | 0,0001 | 0,0004 | -0,32 | pequeno | sim |
| sma_basico, combinadas, prazo_aprovacao=10 x prazo_aprovacao=40 | Conclusão | 30 | 20,0% | 30,0% | -10,0% [-20,0%; 0,0%] | 3 | Wilcoxon pareado, exato: 0,0 | 0,2500 | 0,5000 | -0,10 | desprezível | não |
| sma_basico, nominal, limiar_percentual=5 x padrao | Classificação correta | 30 | 86,7% | 86,7% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_basico, nominal, limiar_percentual=20 x padrao | Classificação correta | 30 | 66,7% | 86,7% | -20,0% [-33,3%; -6,7%] | 6 | Wilcoxon pareado, exato: 0,0 | 0,0312 | 0,1250 | -0,20 | pequeno | não |
| sma_basico, combinadas, ttl_reserva=40 x padrao | Conclusão | 30 | 13,3% | 26,7% | -13,3% [-26,7%; -3,3%] | 4 | Wilcoxon pareado, exato: 0,0 | 0,1250 | 0,3750 | -0,13 | desprezível | não |
| sma_basico, nominal, max_correcoes=0 x padrao | Críticas corrigidas | 30 | 0,00 | 1,33 | -1,33 [-1,63; -1,07] | 27 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | -0,90 | grande | sim |

**Família RQ6**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_basico, combinadas_ataque x combinadas | Execução correta | 30 | 45,4% | 45,4% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_local, combinadas_ataque x combinadas | Execução correta | 30 | 47,5% | 47,5% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |

**Família RQ7**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sma_local x sma_basico, nominal | Classificação correta | 30 | 75,0% | 75,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_local x sma_basico, perda_baixa | Classificação correta | 29 | 75,0% | 75,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sma_local x sma_basico, perda_media | Classificação correta | 28 | 78,6% | 75,0% | 3,6% [0,0%; 10,7%] | 1 | Wilcoxon pareado, exato: 0,0 | 1,0000 | 1,0000 | 0,05 | desprezível | não |
| sma_local x sma_basico, perda_alta | Classificação correta | 27 | 79,6% | 75,0% | 4,6% [0,0%; 13,9%] | 2 | Wilcoxon pareado, exato: 0,0 | 0,5000 | 1,0000 | 0,08 | desprezível | não |
| sma_local x sma_basico, combinadas | Classificação correta | 27 | 82,4% | 78,7% | 3,7% [0,0%; 11,1%] | 1 | Wilcoxon pareado, exato: 0,0 | 1,0000 | 1,0000 | 0,05 | desprezível | não |
| sma_local x sma_basico, perda (3 níveis), desvio irregular com pista na planilha | Classificação correta | 6 | 45,8% | 34,7% | 11,1% [0,0%; 33,3%] | 1 | Wilcoxon pareado, exato: 0,0 | 1,0000 | 1,0000 | 0,11 | desprezível | não |
| sma_local x sma_basico, perda_media | Mensagens de coordenação | 30 | 13,22 | 13,26 | -0,04 [-0,33; 0,20] | 2 | Wilcoxon pareado, exato: 1,0 | 1,0000 | 1,0000 | -0,02 | desprezível | não |

**Família Ablação**

| Comparação (a × b) | Métrica | n | Média a | Média b | Diferença [IC 95%] | Pares ≠ | Teste e estatística | p | p (Holm) | δ de Cliff | Efeito | sig. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sem_reenvio x completo, perda_media | Execução correta | 30 | 28,3% | 40,0% | -11,7% [-23,3%; -3,3%] | 5 | Wilcoxon pareado, exato: 0,0 | 0,0625 | 0,1875 | -0,16 | pequeno | não |
| sem_reserva x completo, nominal, fechar_mes | Publicações do período | 30 | 2,00 | 1,00 | 1,00 [1,00; 1,00] | 30 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | 1,00 | grande | sim |
| sem_correcao x completo, nominal, fechar_mes | Críticas corrigidas | 30 | 0,00 | 2,00 | -2,00 [-2,30; -1,70] | 30 | Wilcoxon pareado, normal: 0,0 | 0,0000 | 0,0000 | -1,00 | grande | sim |
| sem_negociacao x completo, consulta_instavel, avaliar_orcamento | Classificação correta | 30 | 50,0% | 50,0% | 0,0% [0,0%; 0,0%] | 0 | idêntico em todos os pares | — | — | 0,00 | desprezível | não |
| sem_cognicao_local x completo, consulta_instavel | Classificação correta | 30 | 40,0% | 50,0% | -10,0% [-23,3%; 0,0%] | 3 | Wilcoxon pareado, exato: 0,0 | 0,2500 | 0,5000 | -0,10 | desprezível | não |

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
