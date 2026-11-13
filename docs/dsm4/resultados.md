# Experimento da DSM4 — resultados

O desenho está em {doc}`experimento`, escrito e versionado antes de qualquer resultado. Esta
página responde a cada pergunta com os números obtidos, explica o comportamento coletivo
observado, lista o que **não** se confirmou e registra os desvios do pré-registro. Todas as
tabelas e todos os testes estão em {doc}`tabelas`; o dado bruto, em
`docs/dsm4/resultados/execucoes.csv`.

```bash
python -m fin_mas experimento --replicas 30 --out docs/dsm4/resultados   # ou: make experimento
```

**O experimento rodou duas vezes, e as duas contam.** A primeira rodada revelou um defeito do
sistema; o defeito foi corrigido; a segunda rodada mede o sistema corrigido. Os números desta
página são os da segunda rodada, e a seção "Duas rodadas" põe as duas lado a lado.

Foram 9.360 execuções em 30 seeds (bloco A: 6.000; B: 2.160; C: 1.080; D: 120). Nenhuma
levantou exceção. Uma segunda execução completa, em outro processo, produziu o mesmo
`execucoes.csv` byte a byte (SHA-256 em `manifesto.json`). Os valores abaixo são a média por
seed com o intervalo de confiança de 95% por bootstrap entre colchetes; "pp" é ponto percentual.

## Resumo

| | Pergunta | Resposta |
|---|---|---|
| RQ1 | Com as mesmas funções, o SMA entrega mais qualidade? | **Não.** Sem falhas, o SMA e o workflow equivalente deram o mesmo resultado nos 240 pares. A vantagem medida na DSM3 era das funções (veto, correção, reconciliação), não do paradigma. |
| RQ2 | Quão robusto é cada braço? | O SMA é **menos** robusto que o workflow sob falha de comunicação: 94,2% de execuções corretas com 5% de perda, 62,5% com 15%, 32,5% com 30%, contra 100% do workflow. Com 5% a diferença não é significativa; com 15%, 30% e nas falhas combinadas, é grande. Sob humano lento, empatam (75,8%). Nenhum dos dois publicou crítica sem tratamento. |
| RQ3 | Quanto custa coordenar? E o controle de acesso? | 15,8 mensagens de coordenação por solicitação contra 0,9, e 3,2 ticks a mais sem falhas (31,1 a mais sob falhas combinadas). O controle de acesso por pessoa não acrescentou mensagem, tick nem registro no trace. |
| RQ4 | O SMA se recupera? | Sempre responde: 100% de resposta explícita em todas as condições. Recupera o resultado em 87% das execuções atingidas com 5% de perda, 52% com 15% e 26% com 30%; nas outras, falha de forma explícita. A recuperação leva de 28 a 59 ticks na mediana. |
| RQ5 | Depende do porte e dos parâmetros? | A microempresa classifica pior (40,0% contra 86,7%). Tentativas e prazo de subtarefa mexem na robustez e na latência como previsto; o efeito do prazo de aprovação e do TTL da reserva não foi detectado; o limiar de 5% não mudou nada. |
| RQ6 | Os ataques passam quando há falha? | **Não.** 2.227 ataques tentados, nenhum aceito indevidamente; a execução atacada terminou igual à não atacada nos 480 pares. |
| RQ7 | A cognição local melhora o resultado? | **Na medida registrada, não.** Sem falhas, o resultado é idêntico. Sob perda, a classificação correta difere em 2 seeds de 30 e nenhum teste a distingue do acaso. Numa medida que não estava designada (execução correta), o braço local fica de 7 a 9 pp acima do básico sob perda, sem significância. |

A conclusão que os números sustentam, nas duas rodadas: para este problema e este tamanho, um
controlador centralizado com as mesmas regras entrega a mesma qualidade, com menos mensagens e
sem a exposição à perda de mensagens. **Com funções iguais, o SMA empata em qualidade e perde em
custo e em robustez.** O que a arquitetura de agentes compra (separação de autoridade entre quem
calcula, quem julga a conformidade e quem aprova; menor privilégio por agente; trilha de quem
decidiu o quê) não aparece em métrica de resultado, e este experimento só o mede indiretamente,
pelos ataques rejeitados.

## Duas rodadas

| | Primeira rodada | Segunda rodada |
|---|---|---|
| Código | experimento sobre a v0.5.0 como estava (dados no commit `cfa6b6f`) | código integrado, com o defeito corrigido (dados no commit `ab4cc3a`) |
| SHA-256 do `execucoes.csv` | `c5a4e032…` | `952af6eb…` |
| Papel | revelou o defeito "resposta perdida vira silêncio" | mede o sistema depois da correção |

**A correção foi feita depois de ver os resultados da primeira rodada.** A segunda rodada,
portanto, **não é um teste confirmatório** das hipóteses de robustez e de recuperação: o sistema
foi mudado justamente onde a primeira rodada mostrou que ele falhava, e é esperado que os
números melhorem ali. Ela vale como medida do sistema que é entregue; como teste de hipótese,
vale o que as duas rodadas têm em comum. As hipóteses, as métricas, as seeds, as condições e os
testes são os do pré-registro nas duas.

Entre as rodadas mudou mais do que a correção. Tudo o que mudou:

1. **A correção** (`core/bus.py`): toda mensagem perdida depois da abertura de uma conversa
   entre agentes agenda um aviso de prazo ao iniciador, que reenvia uma vez ou falha de forma
   explícita. Antes, a resposta perdida não avisava ninguém. O verificador de invariantes
   também foi ajustado (aviso sem transição; parecer do AG-CIN exigido em todo fechamento
   publicado; veto reavaliado em conversa posterior).
2. **O sorteio do atraso de entrega** passou a ser feito no início do envio, antes da validação,
   para a política conferir o prazo do ticket pela entrega real. As condições com atraso
   (`combinadas` e `combinadas_ataque`) não repetem as mesmas realizações da primeira rodada.
3. **O braço "SMA com cognição local" mudou de conteúdo.** Na primeira rodada, o nível local só
   acrescentava as hipóteses do AG-ORC. Na segunda, AG-RES, AG-CUS e AG-REL também são agentes
   BDI nesse nível ({doc}`ADR-010-especialistas-bdi`, {doc}`cognicao`). O braço básico e os dois
   workflows não mudaram.

Os números principais, lado a lado (SMA básico, salvo indicação):

| Medida | Primeira rodada | Segunda rodada | Workflow equivalente (as duas) |
|---|---|---|---|
| Pares diferentes do workflow, sem falhas (RQ1) | 0 de 240 | 0 de 240 | — |
| Execução correta, perda de 5% | 80,0% | 94,2% | 100% |
| Execução correta, perda de 15% | 48,8% | 62,5% | 100% |
| Execução correta, perda de 30% | 22,5% | 32,5% | 100% |
| Execução correta, indisponibilidade | 92,1% | 97,1% | 100% |
| Execução correta, humano lento | 75,8% | 75,8% | 75,8% |
| Execução correta, falhas combinadas | 45,4% | 50,8% | 75,8% |
| Resposta explícita, perda de 5% / 15% / 30% | 88,8% / 73,8% / 52,9% | 100% / 100% / 100% | 100% |
| Execuções do SMA com invariante violado | 807 de 6.480 (todas INV-07) | 0 de 6.480 | não se aplica |
| Mensagens de coordenação, sem falhas | 15,75 | 15,75 | 0,88 |
| Latência, sem falhas (ticks) | 15,89 | 15,89 | 12,71 |
| Latência, falhas combinadas (ticks) | 43,7 (só as 28 seeds com resposta) | 49,2 | 18,1 |
| Críticas publicadas sem tratamento | 0 | 0 | 0 |
| Ataques aceitos indevidamente | 0 de 1.735 | 0 de 2.227 | não atacado |
| Ablação do reenvio, perda de 15% (com × sem) | 40,0% × 28,3% (não significativo) | 61,7% × 31,7% (p ajustado < 0,001) | — |

**O que a correção mudou.** (1) Toda solicitação passou a receber resposta: as 807 execuções sem
resposta da primeira rodada viraram, na segunda, ou resultado certo (o reenvio agora cobre
também a resposta perdida) ou falha explícita. (2) A robustez do SMA subiu de 5 a 14 pp em todas
as condições de falha de comunicação. (3) O reenvio do Orquestrador, que na primeira rodada não
tinha efeito distinguível do acaso, passou a ter efeito grande e significativo, porque agora ele
é acionado nos casos que antes travavam. (4) Mais tentativas deixaram de derrubar a resposta
explícita (era um efeito colateral do defeito). (5) Com 5% de perda, a diferença para o workflow
deixou de ser significativa (5,8 pp, 5 seeds diferentes).

**O que a correção não mudou.** (1) O SMA continua perdendo em robustez para o workflow
equivalente em toda condição de falha de comunicação, e por muito a partir de 15% de perda:
37,5 pp a menos com 15%, 67,5 pp com 30%, 25,0 pp nas falhas combinadas. Responder sempre não é
o mesmo que acertar: com 30% de perda, 145 das 240 execuções do SMA básico terminam em falha
explícita. (2) O custo de coordenação é o mesmo, e a latência sob falha ficou **maior**, porque
as execuções que antes travavam agora esperam o prazo, reenviam e entram na média. (3) A
qualidade com funções iguais continua empatada. (4) A segurança continua intacta: nenhuma
crítica publicada sem tratamento e nenhum ataque aceito indevidamente, antes e depois.

## A amostra

Os sorteios são da seed, então vale dizer o que saiu. Nas 30 seeds: 20 aprovadores diligentes e
10 cautelosos; **nenhum** rigoroso (a probabilidade era 0,10; por acaso não saiu). Plantios:
alçada em 11 seeds, SoD em 8, duplicidade em 11, competência em 11, desvio orçamentário em 11,
divergência de fonte em 10 e desvio irregular em 10 (em 4 delas com a observação parafraseada);
2 seeds sem plantio. Como as chaves de sorteio da perda não dependem do porte nem da intenção,
uma mensagem que se perde numa seed se perde nas 8 células daquela seed: os efeitos aparecem
em blocos de seed, e por isso a unidade estatística é a seed (n = 30), não a execução.

## RQ1 — qualidade com funções iguais

![Qualidade sem falhas](resultados/fig_qualidade.svg)

- **H1a confirmada, nas duas rodadas.** SMA básico e workflow equivalente: 0 pares diferentes em
  240 (status, DRE, contas sinalizadas, contas atribuídas e correções). Classificação correta de
  75,0% [63,3%; 85,8%] nos dois; conformidade e DRE corretas em 100%; nenhuma crítica publicada
  sem tratamento.
- **H1b confirmada.** O workflow mínimo da DSM3 classifica certo em 36,7% [20,0%; 53,3%]
  (38,3 pp a menos [23,3; 53,3], p ajustado < 0,001, delta de Cliff 0,33) e publica 0,68 crítica
  sem tratamento por execução [0,55; 0,82] (delta −0,93). A conformidade ele acerta em 100%:
  enxerga os mesmos achados, só não tem o que fazer com eles.

A crítica do professor estava certa. Quando o workflow recebe veto, correção, aprovação,
reconciliação de fontes e atribuição de desvio, a diferença de qualidade some. A equivalência
é conferida por teste (`tests/e2e/test_equivalencia_workflow.py`) nos 11 cenários comparáveis da
DSM3 e em cargas sorteadas fora das seeds do experimento, com mais campos do que a hipótese
pedia (KPIs, totais e forecast, achados, número de ressalvas e de notas, decisões do Approval
Gate).

A classificação não chega a 100% em nenhum braço por três situações em que o gabarito pede o que
uma resposta de rótulo único não dá; estão em "Ameaças à validade".

## RQ2 — robustez sob falha

![Robustez por condição](resultados/fig_robustez.svg)

| Condição | SMA básico | Workflow equivalente | Diferença | p ajustado |
|---|---|---|---|---|
| `perda_baixa` (5%) | 94,2% [88,3%; 99,2%] | 100% | −5,8 pp [−11,7; −0,8] | 0,125 |
| `perda_media` (15%) | 62,5% [50,0%; 74,6%] | 100% | −37,5 pp [−50,0; −25,4] | < 0,001 |
| `perda_alta` (30%) | 32,5% [21,2%; 44,2%] | 100% | −67,5 pp [−78,8; −55,8] | < 0,001 |
| `indisponibilidade` | 97,1% [92,1%; 100%] | 100% | −2,9 pp [−7,9; 0,0] | 0,500 |
| `humano_lento` | 75,8% [67,1%; 84,2%] | 75,8% [67,1%; 84,2%] | idêntico em todos os pares | — |
| `combinadas` | 50,8% [40,0%; 61,7%] | 75,8% [67,1%; 84,2%] | −25,0 pp [−37,1; −14,2] | < 0,001 |

- **H2a confirmada** para 15% e 30% de perda e para as falhas combinadas, com efeito grande
  (delta de Cliff −0,67, −0,93 e −0,45). Para 5% de perda e para a indisponibilidade de um
  especialista, a diferença tem o sinal previsto e **não é significativa** (5 e 2 seeds
  diferentes). Na primeira rodada, antes da correção, os 5% de perda eram significativos.
- **H2b confirmada:** 94,2% > 62,5% > 32,5% (p ajustado < 0,001 nas duas comparações).
- **H2c confirmada:** com humano lento os dois braços têm exatamente o mesmo resultado. O ticket
  expira nos dois e a publicação fica bloqueada (58 de 240 execuções em cada um).
- **H2d confirmada:** nenhuma crítica publicada sem tratamento em nenhuma execução do SMA ou do
  workflow equivalente, em nenhuma condição. Quando falha, o SMA falha fechado.

O workflow ganha por construção: ele não tem mensagens entre componentes, e o modelo de falhas
só atinge essas mensagens. O que o experimento acrescenta é o tamanho da conta. Depois da
correção, 5% de perda por mensagem custam pouco; a partir de 15%, mais de um terço das
solicitações do SMA não termina com o resultado certo, e o mecanismo de recuperação (um reenvio
por subtarefa) não dá conta.

## RQ3 — custo de coordenação e do controle de acesso

![Custo por condição](resultados/fig_custo.svg)

- **H3a confirmada.** Sem falhas: 15,75 mensagens de coordenação por solicitação no SMA contra
  0,88 no workflow (14,87 a mais [14,20; 15,53]) e 15,89 ticks contra 12,71 (3,18 a mais
  [2,87; 3,48]). Por intenção: fechar o mês custa 23,5 mensagens e 21,6 ticks no SMA contra 1,8
  e 19,4; avaliar o orçamento, 8,0 e 10,2 contra 0 e 6,0. Sob falhas combinadas: 13,60
  mensagens contra 0,64 e 49,2 ticks contra 18,1 (31,1 a mais [25,0; 37,5]). Todas com p
  ajustado < 0,001 e delta de Cliff entre 0,89 e 1,00.
- **H3b confirmada em parte.** Ligar o SVC-IAM (decisão com atestado de pessoa) não mudou o
  número de mensagens, a latência nem o número de registros do trace em nenhuma das 30 seeds: o
  atestado viaja dentro da mensagem de aprovação. A previsão de que haveria **mais registros de
  auditoria no trace não se confirmou**; o que o controle de acesso registra a mais vai para a
  trilha de acesso, que é outro arquivo e não foi medida aqui. Tempo de parede (não
  reproduzível, uma rodada, `tempo_parede.csv`): mediana de 4,1 ms por execução com o SVC-IAM
  contra 2,7 ms sem ele, no porte médio, 60 execuções de cada lado.

## RQ4 — recuperação

Execução "atingida": houve pelo menos uma mensagem perdida ou um prazo esgotado na solicitação.

| Condição (SMA básico) | Atingidas | Mesmo resultado da nominal | Degradação segura | Sem resposta | Recuperação (mediana) |
|---|---|---|---|---|---|
| `perda_baixa` | 105 de 240 | 91 (87%) | 14 | 0 | 28 ticks |
| `perda_media` | 189 | 99 (52%) | 90 | 0 | 46 ticks |
| `perda_alta` | 220 | 58 (26%) | 162 | 0 | 59 ticks |
| `indisponibilidade` | 57 | 50 (88%) | 7 | 0 | 33 ticks |
| `combinadas` | 176 | 58 (33%) | 118 | 0 | 54 ticks |

- **H4a confirmada para falhas leves e, por pouco, para 15% de perda;** refutada para 30% de
  perda (26%) e para as falhas combinadas (33%). Na primeira rodada só as falhas leves passavam
  da metade (54% e 67%).
- **H4b confirmada:** a mediana da recuperação fica entre 28 e 59 ticks, acima dos 10 de um
  prazo de consulta. Recuperar custa, em geral, um prazo de subtarefa (30 ticks).
- **H4c (execuções sem resposta) confirmada na primeira rodada e eliminada na segunda.** Antes
  da correção ficaram sem resposta 27, 63 e 113 das 240 execuções com 5%, 15% e 30% de perda, 12
  com um especialista fora do ar e 40 nas combinadas. Depois, nenhuma. A "degradação segura" da
  tabela é quase toda falha explícita: o Orquestrador reenvia uma vez e, se perde de novo,
  responde `failure`.

Recuperar de perda de mensagem leva mais tempo que recuperar de indisponibilidade (50,2 contra
35,7 ticks em média; p ajustado < 0,001, delta de Cliff 0,33). O braço com cognição local leva
um pouco mais que o básico (53,5 contra 49,1 ticks; p = 0,031, delta 0,06, desprezível).

## RQ5 — porte e parâmetros

![Sensibilidade a parâmetros](resultados/fig_sensibilidade.svg)

**Porte.** Classificação correta de 40,0% [23,3%; 56,7%] na microempresa contra 86,7% nos outros
três portes (46,7 pp a menos [−63,3; −30,0], p ajustado 0,001). **H5a confirmada:** nas 20
execuções da micro com divergência de fonte, as 20 erram, porque sem ERP não há segunda fonte
para reconciliar. Mas a divergência não explica tudo: outras 16 das 40 execuções da micro
também erram, por dois efeitos da geração de dados nesse porte (ver ameaças). O custo de
coordenação não muda com o porte (15,7 a 15,9 mensagens). O workflow equivalente tem os mesmos
números de classificação em todos os portes. O experimento cobre os quatro portes do
pré-registro; MEI e Média empresa II, que entraram no sistema depois, ficam de fora.

**Parâmetros** (porte médio, um por vez; H5b):

| Parâmetro | O que se viu | Veredito |
|---|---|---|
| Máximo de tentativas 1 / 2 / 3 | execução correta sob falhas combinadas: 36,7% / 51,7% / 63,3% (1 × 3: −26,7 pp [−40,0; −15,0], p ajustado 0,001). O custo é latência: 29,9 / 48,7 / 57,1 ticks. | confirmada |
| Prazo de subtarefa 15 / 30 / 60 | latência sob falhas combinadas: 36,6 / 48,7 / 70,1 ticks (15 × 60: −33,6 [−45,2; −23,2], p ajustado < 0,001). A robustez muda pouco (50,0% / 51,7% / 56,7%). | confirmada |
| Prazo de aprovação 10 / 20 / 40 | fechamentos publicados sob falhas combinadas: 20,0% com prazo 10 contra 33,3% com 40 (4 seeds diferem; p = 0,125). No workflow, onde só o humano atrapalha, 68,3% / 75,0% / 78,3%. | sentido previsto, **não significativo** |
| Limiar de desvio 5% / 10% / 20% | 5%: nada muda (idêntico em todos os pares). 20%: a classificação cai de 86,7% para 66,7% (−20 pp [−33,3; −6,7], p = 0,031, ajustado 0,094). | **refutada para 5%**; para 20%, não significativa após a correção de Holm |
| TTL da reserva 40 / 80 / 200 | fechamentos publicados sob falhas combinadas: 13,3% com TTL 40 contra 26,7% com 200 (4 seeds; p = 0,125). | sentido previsto, **não significativo** |
| Máximo de correções 0 / 2 | críticas corrigidas no fechamento: 0 contra 1,33; publicação sem falhas cai de 100% para 83,3% (o aprovador cauteloso bloqueia o que não pode corrigir). p ajustado < 0,001. | confirmada |

## RQ6 — ataques sob falha

- **H6a confirmada.** Bloco A: 1.792 ataques ao Approval Gate em 128 execuções atacadas, com
  perda, atraso, indisponibilidade e humano lento ao mesmo tempo; 0 aceitos. Bloco D (SVC-IAM
  ligado): 435 ataques em 15 execuções; 9 registrados como aceitos, **todos o mesmo ataque e
  nenhum indevido** (explicação em "Desvios do pré-registro").
- **H6b confirmada.** A execução atacada terminou com o mesmo resultado da mesma execução sem
  ataque nos 240 pares do SMA básico e nos 240 do SMA com cognição local.

Só há ataque quando há veto pendente (os ataques miram o Approval Gate), por isso 128 de 480
execuções foram atacadas; são mais que na primeira rodada (97) porque menos execuções travam
antes de chegar ao veto. O workflow equivalente não foi atacado: a bateria de ataques é contra o
barramento de agentes.

## RQ7 — cognição local

![Cognição local × básica](resultados/fig_cognicao.svg)

O braço mudou de conteúdo entre as rodadas (ver "Duas rodadas" e "Desvios"): na segunda, além
das hipóteses do AG-ORC, os agentes de Resultados, Custos e Relatórios são BDI. O que se mede
aqui é esse pacote inteiro contra o SMA básico.

- **H7a confirmada.** Sem falhas, 0 pares diferentes em 240, nenhuma mensagem e nenhum tick a
  mais. O custo aparece em decisões e em trace: 18,0 decisões registradas por solicitação
  contra 13,4, e 253,5 registros de trace por fechamento contra 181,7. As hipóteses do AG-ORC
  seguem como antes (0,23 confirmada e 0,03 refutada por execução).
- **H7b não confirmada.** Na medida registrada, a classificação correta, o braço local fica um
  pouco acima sob perda média (75,3% contra 72,5%), perda alta (73,7% contra 69,8%) e falhas
  combinadas (79,5% contra 78,6%), sempre por 2 seeds em 30, e nenhum teste distingue a
  diferença do acaso (p entre 0,5 e 1,0). No subgrupo registrado (desvio irregular com pista na
  planilha, sob perda) sobraram 6 seeds: 41,7% contra 30,6%, uma única seed diferente. É o
  mesmo quadro da primeira rodada.
- **H7c não confirmada.** Mensagens de coordenação sob perda média: 15,95 contra 15,42 (0,53 a
  mais [−0,13; 1,27], p = 0,17).

**O ganho da cognição apareceu?** Na hipótese que foi registrada, não. Há um sinal numa medida
que não era a designada, e ele precisa ser lido como exploratório: a execução correta do braço
local fica acima da do básico em todas as condições de falha de comunicação.

| Condição | SMA básico | SMA com cognição local | Diferença | Seeds diferentes | p (sem correção) |
|---|---|---|---|---|---|
| `perda_baixa` | 94,2% | 97,5% | +3,3 pp [0,0; 8,3] | 2 | 0,50 |
| `perda_media` | 62,5% | 71,2% | +8,8 pp [0,4; 18,3] | 6 | 0,063 |
| `perda_alta` | 32,5% | 40,4% | +7,9 pp [1,7; 16,3] | 4 | 0,125 |
| `indisponibilidade` | 97,1% | 98,3% | +1,3 pp [0,0; 3,8] | 1 | 1,00 |
| `combinadas` | 50,8% | 57,9% | +7,1 pp [−0,4; 16,7] | 5 | 0,125 |

Nenhuma dessas diferenças é significativa, nem antes de corrigir para cinco comparações. Elas
não constavam do plano de análise, foram calculadas depois de ver os dados e vêm de um braço
cujo conteúdo mudou depois do pré-registro. O que se pode dizer: o sinal é consistente no
sentido (em 24 execuções com 15% de perda o braço local acerta onde o básico falha, e em 3
acontece o contrário), é pequeno, e este experimento não tem poder para afirmá-lo. Mesmo com
ele, o braço local continua muito abaixo do workflow equivalente: 71,2% contra 100% com 15% de
perda, 40,4% contra 100% com 30%.

## Ablação

![Ablação](resultados/fig_ablacao.svg)

Base: SMA com cognição local e tudo ligado (na segunda rodada, com os especialistas BDI), porte
médio, desvio irregular sempre plantado e, no fechamento, um segundo pedido do mesmo mês 2 ticks
depois.

| Mecanismo desligado | Medida designada | Com o mecanismo | Sem | Leitura |
|---|---|---|---|---|
| Reenvio do Orquestrador | execução correta, 15% de perda | 61,7% | 31,7% | −30,0 pp [−43,3; −16,7], 13 seeds, p ajustado < 0,001, delta −0,39. **É o mecanismo de recuperação que funciona.** Na primeira rodada a diferença era de 11,7 pp e não significativa: o reenvio só passou a valer para a resposta perdida depois da correção. |
| Reserva de período | publicações do mesmo mês, sem falhas | 1,00 | 2,00 | Nas 30 seeds, os dois pedidos concorrentes são publicados e 1,37 correção por execução falha por já ter sido feita pelo outro. p ajustado < 0,001. Igual nas duas rodadas. |
| Veto com correção | críticas corrigidas, sem falhas | 2,00 | 0 | Sem correção, o diligente concede waiver e o cauteloso bloqueia: a publicação cai de 100% para 66,7%. p ajustado < 0,001. Igual nas duas rodadas. |
| Negociação de prazo | classificação correta, consulta instável, avaliação orçamentária | 50,0% | 50,0% | **Sem efeito na medida designada**, nas duas rodadas. A negociação foi acionada em 6 de 30 execuções; em uma seed ela levou ao resultado da execução sem falha (execução correta 73,3% contra 70,0%). |
| Cognição local | classificação correta, consulta instável | 50,0% | 40,0% | −10,0 pp [−23,3; 0,0], 3 seeds, p = 0,25: **não significativo**, nas duas rodadas. Na execução correta, 73,3% contra 56,7% (avaliação) e 70,0% contra 56,7% (fechamento). |

Três dos cinco mecanismos têm contribuição clara: reserva, correção e, depois da correção do
barramento, reenvio. A negociação de prazo não mostrou efeito. A cognição local aponta no
sentido esperado sem significância na medida designada; fora dela (exploratório), no fechamento
com 15% de perda, a execução correta cai de 50,0% para 30,0% quando a cognição local é desligada
(6 seeds, p = 0,031 sem correção).

## Comportamento coletivo observado

**Quem decidiu o quê.** No SMA básico sem falhas, 77% das decisões registradas foram tomadas
fora do Orquestrador (17,2 decisões por fechamento, contra 6,1 do controlador único, que toma
todas); com os especialistas BDI, 85% (24,7 decisões por fechamento). O AG-ORC decide a fonte e
a classificação de cada desvio e pergunta ao AG-CIN, sem passar pelo Orquestrador, se há
lançamento irregular na conta. O AG-CIN decide o parecer e, depois de uma correção, percebe o
ERP de novo e reconsidera (2,0 reconsiderações de intenção por fechamento). O humano decide no
Approval Gate (0,88 decisão por fechamento, em média). O Orquestrador decide a ordem, os prazos
e os reenvios. No workflow, as mesmas regras rodam em sequência dentro de um componente que lê
todas as fontes, julga a conformidade e executa a correção.

**Onde a distribuição custou.** (1) Mensagens: cada decisão local precisa de uma troca para ser
conhecida pelos outros. (2) Exposição: cada troca pode se perder; a 15% de perda, 62,5% das
solicitações terminam certas, e a 30%, um terço. (3) Recuperar leva tempo: de 28 a 59 ticks na
mediana, de duas a quatro vezes uma solicitação inteira sem falha. (4) Um reenvio por subtarefa
é pouco quando a perda é alta: com 30%, 145 de 240 execuções acabam em falha explícita.

**Onde a distribuição ajudou.** (1) Em nada que este experimento meça como resultado, quando as
funções são iguais; é o achado central, nas duas rodadas. (2) Na contenção: 2.227 ataques,
vindos de identidades falsas, de agentes legítimos fora do seu papel e da caixa do aprovador sem
a pessoa certa, foram todos rejeitados mesmo com o sistema já degradado, e nenhum mudou o
desfecho. Isso depende de cada agente ter um papel, uma credencial e uma lista de ferramentas;
no workflow, o controlador único acumula tudo e o experimento não tinha como atacá-lo do mesmo
modo. (3) Na concorrência: a reserva de período é a única coisa que impede dois fechamentos do
mesmo mês de serem publicados; sem ela isso aconteceu em 30 de 30 execuções.

**O que as falhas não quebraram.** Nenhuma crítica publicada sem tratamento em 6.480 execuções do
SMA, em nenhuma das rodadas. Na segunda, nenhum invariante violado: nem publicação, nem efeito
externo, nem protocolo, nem crença, nem segredo, nem resposta explícita.

## O que não se confirmou

1. **H7b e H7c (cognição local):** a classificação correta não melhora de forma distinguível do
   acaso, e não houve mais mensagens. O sinal na execução correta é exploratório e não
   significativo.
2. **H2a para 5% de perda e para a indisponibilidade de um especialista** (segunda rodada):
   diferença no sentido previsto, não significativa.
3. **H4a para 30% de perda e para as falhas combinadas:** a maioria das execuções atingidas não
   recupera o resultado; termina em falha explícita.
4. **H5b para o limiar de 5%** (nenhum efeito), **para o limiar de 20%** (não significativo após
   Holm), **para o prazo de aprovação e para o TTL da reserva** (não significativos).
5. **H3b na parte dos registros de auditoria:** o trace não cresce com o controle de acesso.
6. **Ablação da negociação de prazo e da cognição local:** contribuição não distinguível do
   acaso com 30 seeds, nas duas rodadas.
7. **A expectativa de zero violações de invariantes, na primeira rodada:** 807 das 6.480
   execuções do SMA violaram o INV-07 (resposta explícita). Na segunda, zero.

## Defeitos encontrados pelo experimento

O modelo de falhas aleatórias exercitou caminhos que os cenários fixos nunca tinham exercitado
(na primeira rodada, os cenários que injetavam perda perdiam sempre um pedido, nunca uma
resposta).

1. **Resposta perdida virava silêncio (grave; corrigido entre as rodadas).** O barramento muda o
   estado da conversa quando a mensagem é **enviada**. Se a resposta final de um especialista
   (`inform`, `failure`, parecer) se perdia na entrega, a conversa já constava como concluída, o
   temporizador do prazo não avisava ninguém e o Orquestrador esperava para sempre. Valia para
   PROT-DEL e PROT-CMP, e para a mensagem `correcao` enviada ao AG-CIN. Frequência na primeira
   rodada: 11% das solicitações com 5% de perda, 26% com 15%, 47% com 30%, 5% com um
   especialista fora do ar. Das 255 execuções do SMA básico sem resposta sob falha de
   comunicação, 192 pararam na resposta final de uma delegação (180 `inform` e 12 `failure`) e
   63 no PROT-CMP (47 pareceres do AG-CIN e 16 mensagens de correção). Correção: a perda de
   qualquer mensagem depois da abertura da conversa avisa o iniciador (`Bus._perdida`). Na
   segunda rodada: 0 execuções sem resposta em 6.480.
2. **Trace dependia do hash das strings (corrigido antes da primeira rodada).** Com dois estornos
   no mesmo ciclo de correção, o AG-CIN revisava as crenças na ordem de iteração de um conjunto,
   que muda de um processo para outro. O hash do trace deixava de se repetir entre processos,
   sem mudar nenhum resultado. `cenarios --verificar` não via porque compara duas execuções no
   mesmo processo. Sem a correção, o `execucoes.csv` não seria reproduzível.
3. **Falso positivo do INV-03 (corrigido entre as rodadas).** O aviso de prazo do PROT-CMP não
   muda o estado (`de` = `para`) e o verificador o contava como transição fora do protocolo: 165
   ocorrências na primeira rodada, contadas à parte pelo experimento. Na segunda, o verificador
   já trata o caso e a contagem é zero.

## Desvios do pré-registro

1. **Correção do sistema entre duas rodadas.** O pré-registro dizia que o experimento não
   corrigiria o defeito previsto, só mediria. O defeito foi corrigido depois da primeira rodada e
   o experimento foi rodado de novo. As duas rodadas estão relatadas; a segunda não é teste
   confirmatório das hipóteses de robustez e recuperação (ver "Duas rodadas").
2. **O braço "SMA com cognição local" mudou de conteúdo.** No pré-registro, e na primeira rodada,
   o nível local acrescentava só as hipóteses do AG-ORC. Na segunda, AG-RES, AG-CUS e AG-REL
   também são agentes BDI nesse nível ({doc}`ADR-010-especialistas-bdi`). RQ7 e a ablação da
   cognição local comparam, na segunda rodada, o pacote inteiro com o SMA básico; não dá para
   separar o que vem das hipóteses do AG-ORC do que vem dos especialistas BDI.
3. **Sorteio do atraso de entrega mudou de lugar** entre as rodadas (item 2 de "Duas rodadas").
   As condições com atraso não são a mesma realização nas duas.
4. **Portes fixados nos quatro do pré-registro.** O sistema ganhou MEI e Média empresa II
   depois; ficam fora do experimento porque o workflow equivalente não implementa as regras
   deles, e a equivalência não foi testada nesses portes.
5. **Defeito previsto mais amplo que o previsto.** O pré-registro apontava o PROT-CMP; o mesmo
   defeito estava no PROT-DEL e respondia por três quartos das execuções sem resposta.
6. **Métrica de ataques desdobrada.** Um dos 15 ataques de `env/ataques_acesso.py` ("aprovador
   que participou do lançamento vetado decide sobre ele") supõe que a analista ana participou do
   lançamento. Com plantios sorteados isso nem sempre é verdade; quando ela não está entre os
   envolvidos do ticket, a decisão dela é a de uma aprovadora autorizada, com atestado válido e
   sem conflito, e a política a aceita corretamente. Foram 8 casos na primeira rodada e 9 na
   segunda. O CSV traz `ataques_aceitos` (bruto), `ataques_sem_premissa` (esses casos) e a
   diferença, que é zero. A regra foi acrescentada depois de ver o primeiro caso, numa rodada de
   teste do aparato.
7. **Medidas exploratórias.** `sinalizacao_correta` (só as contas sinalizadas, a definição da
   DSM3) e a comparação da execução correta entre o braço local e o básico (RQ7) não estavam no
   plano de análise. Estão marcadas como exploratórias e não entram em nenhuma família de testes.
8. **Rodadas do aparato antes do experimento.** Enquanto o código era escrito, foram olhadas uma
   rodada de fumaça nas seeds 1 a 30 com uma configuração que não é nenhuma condição do
   experimento (contagem de status e quatro traces) e rodadas do modo rápido (seeds 1 a 3). A
   equivalência do workflow foi desenvolvida em seeds fora de 1 a 30. O tamanho da amostra, as
   seeds, as condições e as comparações não mudaram em nenhum momento.
9. **Reexecuções.** A primeira rodada foi executada cinco vezes (uma, duas de conferência de
   reprodutibilidade, uma depois de ajustar a correção de Holm para deixar de fora as
   comparações idênticas em todos os pares, como o plano de análise já dizia, e mais uma de
   conferência), sempre com o mesmo CSV. A segunda rodada foi executada duas vezes, com o mesmo
   CSV.
10. **Falta o bloco de fuzz** citado no plano geral do projeto (invariantes em milhares de
    seeds): não estava no pré-registro e não foi feito.

## Ameaças à validade

As previstas no pré-registro continuam valendo. O que a execução mostrou a mais:

- **Interna — a segunda rodada foi medida depois de corrigir o que a primeira mostrou.** Os
  ganhos de robustez e de recuperação da segunda rodada são efeito de uma mudança escolhida à
  vista dos resultados; não confirmam hipótese nenhuma. O que as duas rodadas têm em comum
  (empate de qualidade, custo maior, robustez menor que a do workflow sob perda, zero ataque
  aceito, zero crítica publicada) não depende da correção.
- **Interna — três coisas mudaram entre as rodadas, não uma.** A correção, o lugar do sorteio do
  atraso e o conteúdo do braço local. Para o SMA básico nas condições sem atraso (perda nos três
  níveis e indisponibilidade), a diferença entre as rodadas é atribuível à correção e ao
  verificador; nas condições com atraso e no braço local, não dá para separar.
- **Construto — a robustez favorece o workflow por construção,** como previsto. O resultado diz
  quanto a distribuição custa neste sistema; não diz que um workflow distribuído (controlador com
  serviços remotos) seria imune.
- **Construto — o gabarito de classificação tem teto abaixo de 100%.** Três situações em que
  nenhum braço pode acertar pela definição registrada: (a) desvio orçamentário e desvio irregular
  caem na mesma conta (4 seeds): o gabarito a lista como desvio **e** como atribuída a controle,
  e a classificação é de rótulo único; (b) na micro, o desvio irregular é plantado exatamente no
  limiar de 15% do porte e, pelo arredondamento, não chega a ser desvio; (c) na micro, uma
  duplicidade plantada na conta que tem desvio orçamentário é descontada do desvio, embora o
  lançamento duplicado não tenha inflado o realizado, porque ali os lançamentos são grandes
  perto do orçamento. As três atingem SMA e workflow equivalente por igual e não mudam nenhuma
  comparação entre eles; mudam o nível absoluto e explicam parte da diferença da micro.
- **Conclusão — pouco poder para efeitos raros.** Como as perdas são sorteadas por mensagem com
  chave comum, as 8 células de uma seed compartilham o destino das mensagens. Isso emparelha bem
  os braços, mas faz o efeito aparecer em poucas seeds inteiras: as comparações de cognição
  local e de negociação têm de 1 a 6 seeds diferentes em 30.
- **Conclusão — a amostra não teve aprovador rigoroso.** O caminho "bloqueia sempre" não foi
  exercitado no experimento (é exercitado nos cenários fixos).
- **Externa — um só nível de recuperação.** O Orquestrador reenvia uma vez. A distância para o
  workflow sob perda alta depende dessa escolha (a varredura mostra 63,3% com três tentativas
  contra 51,7% com duas, nas falhas combinadas); não é uma propriedade de sistemas multiagentes
  em geral.
- **Tempo de parede** medido numa máquina, numa rodada, com o YAML dos protocolos em cache; serve
  de ordem de grandeza (mediana de 2,7 ms por execução do SMA básico sem falhas, 3,9 ms com
  cognição local e 0,2 ms do workflow equivalente) e nada mais.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `resultados/execucoes.csv` | Uma linha por execução (9.360), com chave, carga sorteada, métricas e hash do trace. Reproduzível byte a byte. Segunda rodada; a primeira está no histórico do git (commit `cfa6b6f`). |
| `resultados/resumo.json` e `resumo.md` | Tabelas por pergunta, com média por seed e IC de 95%. |
| `resultados/testes.md` | Testes de hipótese com tamanho de efeito e p ajustado, e a conferência da biblioteca estatística. |
| `resultados/fig_*.svg` | Seis figuras em pequenos múltiplos. |
| `resultados/manifesto.json` | Versão, seeds, condições, parâmetros, probabilidades do modelo de falhas e SHA-256 do CSV. |
| `resultados/tempo_parede.csv` | Milissegundos por execução. **Não reproduzível.** |
