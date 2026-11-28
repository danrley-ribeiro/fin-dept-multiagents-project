# Bloco E — pré-registro da replicação confirmatória

O bloco E ({doc}`resultados`, seção "Bloco E") foi desenhado depois dos resultados dos blocos A a D e rodado nas
seeds 1 a 30: é **exploratório** (desvio 14 do pré-registro principal, {doc}`experimento`). Este documento
transforma o que ele mostrou em hipóteses fechadas e fixa, **antes de rodar**, como elas serão testadas numa
**replicação com seeds novas (31 a 60)**, que nenhuma rodada anterior usou. O commit que introduz este arquivo é
anterior ao commit com os resultados da replicação; o histórico do git (e o push do PR) é a prova da ordem.

Nada do aparato muda entre o exploratório e a replicação: o mesmo código (`src/fin_mas/estudo_e.py`), os mesmos
fatores, níveis, braços, métricas e análise (média por seed, desvio-padrão, IC de 95% por bootstrap, Wilcoxon
pareado por seed, Holm dentro de cada fator). Só as seeds mudam.

```bash
python -m fin_mas.estudo_e --replicas 30 --primeira-seed 31 --out docs/dsm4/resultados/bloco_e_confirmatorio
```

## Hipóteses e critérios de decisão

Uma hipótese é **confirmada** se o critério valer na replicação; caso contrário, é **refutada** e relatada como tal.
"Idêntico" quer dizer o mesmo valor em todas as 30 seeds; diferença "significativa" quer dizer p ajustado por Holm
menor que 0,05, no sentido indicado.

| Id | Fator | Hipótese | Critério |
|---|---|---|---|
| H-E1 | concorrência, mesmo mês (2 e 4 pedidos) | Nos dois braços, o mesmo mês é publicado no máximo uma vez e os demais pedidos são recusados. | publicações indevidas = 0 e recusados = n − 1 em todas as seeds, nos dois braços |
| H-E2 | concorrência, meses diferentes (2 e 4) | O SMA termina antes do workflow em fila. | makespan SMA < workflow, significativo, nos dois níveis |
| H-E3 | concorrência (todos os níveis) | O SMA troca mais mensagens que o workflow. | mensagens SMA > workflow, significativo, em todos os níveis |
| H-E4 | concorrência e porte | Com os mesmos mecanismos (memória da POL-06, recusa de mês já atendido), os dois braços chegam ao mesmo resultado. | publicados, recusados, waivers e críticas publicadas sem tratamento idênticos entre os braços, seed a seed, em todos os níveis |
| H-E5 | concorrência sob 15% de perda (2 e 4) | O SMA publica menos que o workflow e nunca publica crítica sem tratamento. | publicados SMA < workflow, significativo, nos dois níveis; críticas sem tratamento = 0 em todas as seeds |
| H-E6 | concorrência com um especialista fora do ar (2 e 4) | O reenvio recupera: o SMA publica o mesmo que o workflow, termina antes com 4 meses e nunca publica crítica sem tratamento. | \|diferença média de publicados\| ≤ 0,1 e sem diferença significativa, nos dois níveis; makespan SMA < workflow, significativo, com 4; críticas sem tratamento = 0 |
| H-E7 | frequência de irregularidades | Mais irregularidades exigem mais intervenções humanas, sem publicar crítica sem tratamento. | intervenções médias crescentes de baixa para média para alta, nos dois braços; críticas sem tratamento = 0 em todas as seeds |
| H-E8 | volume | O tempo lógico não depende do volume; o tempo de parede, sim. | makespan idêntico entre 12, 96 e 400 lançamentos em todas as seeds, nos dois braços; segundos 400 > 12 no SMA, significativo |

## O que conta como desvio

Qualquer mudança no aparato, nos critérios ou nas seeds depois deste commit é desvio e será declarada em
{doc}`resultados`. O tempo de parede depende da máquina; só a direção (H-E8) é testada, não o valor.
