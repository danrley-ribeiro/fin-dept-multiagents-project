# Bloco E: conferência das hipóteses pré-registradas

Versão 1.1.0; seeds 31 a 60 (30); 1140 execuções.
Critérios: docs/dsm4/experimento-bloco-e.md. Gerado por `tools/confirmar_bloco_e.py`.

**8 de 8 hipóteses confirmadas.**

| Id | Hipótese | Resultado |
|---|---|---|
| H-E1 | o mesmo mês é publicado no máximo uma vez; os demais pedidos são recusados | confirmada |
| H-E2 | com meses diferentes, o SMA termina antes do workflow em fila | confirmada |
| H-E3 | o SMA troca mais mensagens que o workflow | confirmada |
| H-E4 | com os mesmos mecanismos, os dois braços chegam ao mesmo resultado | confirmada |
| H-E5 | sob 15% de perda, o SMA publica menos e nunca publica crítica sem tratamento | confirmada |
| H-E6 | com um especialista fora do ar, o reenvio recupera | confirmada |
| H-E7 | mais irregularidades exigem mais intervenções, sem crítica publicada sem tratamento | confirmada |
| H-E8 | o tempo lógico não depende do volume; o tempo de parede, sim | confirmada |

## H-E1: confirmada

- 2 pedidos: 60 execuções, publicações indevidas 0, execuções com recusados ≠ 1: 0
- 4 pedidos: 60 execuções, publicações indevidas 0, execuções com recusados ≠ 3: 0

## H-E2: confirmada

- 2 meses, makespan SMA × workflow: 17.6333 × 32.5 (dif. -14.8667, p < 0,001)
- 4 meses, makespan SMA × workflow: 17.6333 × 63.8 (dif. -46.1667, p < 0,001)

## H-E3: confirmada

- 1/mesma, mensagens SMA × workflow: 23.1333 × 1.6 (dif. 21.5333, p < 0,001)
- 2/mesma, mensagens SMA × workflow: 25.1333 × 1.6 (dif. 23.5333, p < 0,001)
- 2/distintas, mensagens SMA × workflow: 45.1667 × 3.2 (dif. 41.9667, p < 0,001)
- 4/mesma, mensagens SMA × workflow: 29.1333 × 1.6 (dif. 27.5333, p < 0,001)
- 4/distintas, mensagens SMA × workflow: 89.1333 × 6.4 (dif. 82.7333, p < 0,001)

## H-E4: confirmada

- concorrencia: 150 pares seed a seed; pares diferentes por métrica: publicados 0, recusados 0, waivers 0, criticas_publicadas_sem_tratamento 0
- porte: 120 pares seed a seed; pares diferentes por métrica: publicados 0, recusados 0, waivers 0, criticas_publicadas_sem_tratamento 0

## H-E5: confirmada

- 2 meses, publicados SMA × workflow: 0.5 × 1.3 (dif. -0.8, p < 0,001)
- 4 meses, publicados SMA × workflow: 0.9 × 2.2 (dif. -1.3, p < 0,001)
- execuções com crítica publicada sem tratamento: 0

## H-E6: confirmada

- 2 meses, publicados SMA × workflow: 1.3 × 1.3 (dif. 0.0, p idênticos)
- 4 meses, publicados SMA × workflow: 2.2 × 2.2 (dif. 0.0, p idênticos)
- 4 meses, makespan SMA × workflow: 27.0333 × 63.8 (dif. -36.7667, p < 0,001)
- execuções com crítica publicada sem tratamento: 0

## H-E7: confirmada

- sma_basico: intervenções médias baixa 0.40, média 0.80, alta 0.97
- wf_equivalente: intervenções médias baixa 0.40, média 0.80, alta 0.97
- execuções com crítica publicada sem tratamento: 0

## H-E8: confirmada

- sma_basico: seeds em que o makespan muda com o volume: 0 de 30
- wf_equivalente: seeds em que o makespan muda com o volume: 0 de 30
- SMA, segundos 400 × 12 lançamentos: 0.0702 × 0.027 (dif. 0.0432, p < 0,001)
