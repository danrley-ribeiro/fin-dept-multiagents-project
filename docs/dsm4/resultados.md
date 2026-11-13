# Experimento da DSM4 — resultados

O desenho está em {doc}`experimento`, escrito e versionado antes de qualquer resultado. Esta
página responde a cada pergunta com os números obtidos, explica o comportamento coletivo
observado, lista o que **não** se confirmou e registra os desvios do pré-registro. Todas as
tabelas e todos os testes estão em {doc}`tabelas`; o dado bruto, em
`docs/dsm4/resultados/execucoes.csv`.

```bash
python -m fin_mas experimento --replicas 30 --out docs/dsm4/resultados   # ou: make experimento
```

Foram 9.360 execuções em 30 seeds (bloco A: 6.000; B: 2.160; C: 1.080; D: 120). Nenhuma
levantou exceção. Três execuções completas, em processos diferentes, produziram o mesmo
`execucoes.csv` byte a byte (SHA-256 em `manifesto.json`). Os valores abaixo são a média por
seed com o intervalo de confiança de 95% por bootstrap entre colchetes; "pp" é ponto percentual.

## Resumo

| | Pergunta | Resposta |
|---|---|---|
| RQ1 | Com as mesmas funções, o SMA entrega mais qualidade? | **Não.** Sem falhas, o SMA e o workflow equivalente deram o mesmo resultado nos 240 pares. A vantagem medida na DSM3 era das funções (veto, correção, reconciliação), não do paradigma. |
| RQ2 | Quão robusto é cada braço? | O SMA é **menos** robusto que o workflow sob falha de comunicação: 80,0% de execuções corretas com 5% de perda, 48,8% com 15%, 22,5% com 30%, contra 100% do workflow. Sob humano lento, empatam (75,8%). Nenhum dos dois publicou crítica sem tratamento. |
| RQ3 | Quanto custa coordenar? E o controle de acesso? | 15,8 mensagens de coordenação por solicitação contra 0,9, e 3,2 ticks a mais sem falhas (25,8 a mais sob falhas combinadas). O controle de acesso por pessoa não acrescentou mensagem, tick nem registro no trace. |
| RQ4 | O SMA se recupera? | Em parte. Com 5% de perda, 54% das execuções atingidas terminam com o resultado certo; com 30%, 15%. A recuperação leva de 33 a 59 ticks na mediana. **Parte das execuções fica sem resposta nenhuma** (de 5% a 47% conforme a condição): defeito do sistema, localizado abaixo. |
| RQ5 | Depende do porte e dos parâmetros? | A microempresa classifica pior (40,0% contra 86,7%). Tentativas e prazo de subtarefa mexem na robustez e na latência como previsto; o efeito do prazo de aprovação e do TTL da reserva não foi detectado; o limiar de 5% não mudou nada. |
| RQ6 | Os ataques passam quando há falha? | **Não.** 1.735 ataques tentados, nenhum aceito indevidamente; a execução atacada terminou igual à não atacada nos 480 pares. |
| RQ7 | A cognição local melhora o resultado? | Sem falhas, não muda nada. Sob perda, a diferença foi a favor em 1 ou 2 seeds de 30 e **não é estatisticamente significativa**. |

A conclusão que os números sustentam: para este problema e este tamanho, um controlador
centralizado com as mesmas regras entrega a mesma qualidade, com menos mensagens e sem a
exposição à perda de mensagens. O que a arquitetura de agentes compra (separação de autoridade
entre quem calcula, quem julga a conformidade e quem aprova; menor privilégio por agente; trilha
de quem decidiu o quê) não aparece em métrica de resultado, e este experimento só o mede
indiretamente, pelos ataques rejeitados.

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

- **H1a confirmada.** SMA básico e workflow equivalente: 0 pares diferentes em 240 (status, DRE,
  contas sinalizadas, contas atribuídas e correções). Classificação correta de 75,0%
  [63,3%; 85,8%] nos dois; conformidade e DRE corretas em 100%; nenhuma crítica publicada sem
  tratamento.
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
| `perda_baixa` (5%) | 80,0% [67,5%; 91,2%] | 100% | −20,0 pp [−32,5; −8,8] | 0,004 |
| `perda_media` (15%) | 48,8% [35,8%; 62,5%] | 100% | −51,2 pp [−64,2; −37,5] | < 0,001 |
| `perda_alta` (30%) | 22,5% [13,3%; 30,8%] | 100% | −77,5 pp [−86,7; −69,2] | < 0,001 |
| `indisponibilidade` | 92,1% [85,0%; 98,3%] | 100% | −7,9 pp [−15,0; −1,7] | 0,063 |
| `humano_lento` | 75,8% [67,1%; 84,2%] | 75,8% [67,1%; 84,2%] | idêntico em todos os pares | — |
| `combinadas` | 45,4% [33,8%; 57,5%] | 75,8% [67,1%; 84,2%] | −30,4 pp [−43,8; −17,9] | < 0,001 |

- **H2a confirmada** para os três níveis de perda e para as falhas combinadas. Para a
  indisponibilidade de um especialista a diferença tem o sinal previsto, mas só 5 seeds diferem
  e o teste não a distingue do acaso (p = 0,063).
- **H2b confirmada:** 80,0% > 48,8% > 22,5% (p ajustado < 0,001 nas duas comparações).
- **H2c confirmada:** com humano lento os dois braços têm exatamente o mesmo resultado. O ticket
  expira nos dois e a publicação fica bloqueada (58 de 240 execuções em cada um).
- **H2d confirmada:** nenhuma crítica publicada sem tratamento em nenhuma execução do SMA ou do
  workflow equivalente, em nenhuma condição. Quando falha, o SMA falha fechado.

O workflow ganha por construção: ele não tem mensagens entre componentes, e o modelo de falhas
só atinge essas mensagens. O que o experimento acrescenta é o tamanho da conta: a 5% de perda
por mensagem, uma em cada cinco solicitações do SMA já não termina certa.

## RQ3 — custo de coordenação e do controle de acesso

![Custo por condição](resultados/fig_custo.svg)

- **H3a confirmada.** Sem falhas: 15,75 mensagens de coordenação por solicitação no SMA contra
  0,88 no workflow (14,87 a mais [14,20; 15,53]) e 15,89 ticks contra 12,71 (3,18 a mais
  [2,87; 3,48]). Por intenção: fechar o mês custa 23,5 mensagens e 21,6 ticks no SMA contra 1,8
  e 19,4; avaliar o orçamento, 8,0 e 10,2 contra 0 e 6,0. Sob falhas combinadas a latência do
  SMA sobe para 43,7 ticks contra 18,0 (25,8 a mais [18,3; 33,6], nas 28 seeds em que houve
  resposta). Todas com p ajustado < 0,001 e delta de Cliff entre 0,77 e 1,00.
- **H3b confirmada em parte.** Ligar o SVC-IAM (decisão com atestado de pessoa) não mudou o
  número de mensagens, a latência nem o número de registros do trace em nenhuma das 30 seeds: o
  atestado viaja dentro da mensagem de aprovação. A previsão de que haveria **mais registros de
  auditoria no trace não se confirmou**; o que o controle de acesso registra a mais vai para a
  trilha de acesso, que é outro arquivo e não foi medida aqui. Tempo de parede (não
  reproduzível, uma rodada, `tempo_parede.csv`): mediana de 7,9 ms por execução com o
  SVC-IAM contra 5,7 ms sem ele, no porte médio, 60 execuções de cada lado.

## RQ4 — recuperação

Execução "atingida": houve pelo menos uma mensagem perdida ou um prazo esgotado na solicitação.

| Condição (SMA básico) | Atingidas | Mesmo resultado da nominal | Degradação segura | Sem resposta | Recuperação (mediana) |
|---|---|---|---|---|---|
| `perda_baixa` | 105 de 240 | 57 (54%) | 21 | 27 | 39 ticks |
| `perda_media` | 189 | 66 (35%) | 60 | 63 | 39,5 ticks |
| `perda_alta` | 220 | 34 (15%) | 73 | 113 | 59 ticks |
| `indisponibilidade` | 57 | 38 (67%) | 7 | 12 | 33 ticks |
| `combinadas` | 176 | 45 (26%) | 91 | 40 | 49 ticks |

- **H4a confirmada só para as falhas leves** (5% de perda e indisponibilidade). Com 15% de perda
  ou mais, e nas combinadas, menos da metade das execuções atingidas recupera o resultado.
- **H4b confirmada:** a mediana da recuperação fica entre 33 e 59 ticks, bem acima dos 10 de um
  prazo de consulta. Recuperar custa pelo menos um prazo de subtarefa (30 ticks).
- **H4c confirmada, e pior do que o previsto.** O pré-registro previa que a perda do parecer do
  AG-CIN deixaria a solicitação sem resposta. Deixa, mas isso é um quarto do problema. Das 255
  execuções do SMA básico sem resposta nas condições de falha de comunicação, 192 pararam na
  perda da **resposta final de uma delegação** (PROT-DEL: 180 `inform` e 12 `failure`) e 63 no
  PROT-CMP (47 pareceres do AG-CIN e 16 mensagens de correção enviadas a ele). A causa é a
  mesma nos dois protocolos e está em "Defeitos encontrados".

O tempo de recuperação não diferiu de forma significativa entre perda de mensagens e
indisponibilidade (44,2 contra 37,0 ticks; p ajustado 0,066) nem entre cognição local e básica
(45,0 contra 44,1; p = 0,60).

## RQ5 — porte e parâmetros

![Sensibilidade a parâmetros](resultados/fig_sensibilidade.svg)

**Porte.** Classificação correta de 40,0% [23,3%; 56,7%] na microempresa contra 86,7% nos outros
três portes (46,7 pp a menos [−63,3; −30,0], p ajustado 0,001). **H5a confirmada:** nas 20
execuções da micro com divergência de fonte, as 20 erram, porque sem ERP não há segunda fonte
para reconciliar. Mas a divergência não explica tudo: outras 16 das 40 execuções da micro
também erram, por dois efeitos da geração de dados nesse porte (ver ameaças). O custo de
coordenação não muda com o porte (15,7 a 15,9 mensagens). O workflow equivalente tem os mesmos
números de classificação em todos os portes.

**Parâmetros** (porte médio, um por vez; H5b):

| Parâmetro | O que se viu | Veredito |
|---|---|---|
| Máximo de tentativas 1 / 2 / 3 | execução correta sob falhas combinadas: 36,7% / 46,7% / 50,0% (1 × 3: −13,3 pp [−21,7; −6,7], p ajustado 0,031). Efeito colateral: a resposta explícita **cai** de 88,3% para 78,3%, porque cada reenvio é mais uma troca exposta à perda que trava. | confirmada |
| Prazo de subtarefa 15 / 30 / 60 | latência sob falhas combinadas: 33,4 / 43,1 / 58,3 ticks (15 × 60: −25,0 [−37,4; −14,2], p ajustado < 0,001). A robustez quase não muda (45,0% / 46,7% / 50,0%). | confirmada |
| Prazo de aprovação 10 / 20 / 40 | fechamentos publicados sob falhas combinadas: 20% com prazo 10 contra 30% com 40 (3 seeds diferem; p = 0,25). No workflow, onde só o humano atrapalha, 68,3% / 75,0% / 78,3%. | sentido previsto, **não significativo** |
| Limiar de desvio 5% / 10% / 20% | 5%: nada muda (idêntico em todos os pares). 20%: a classificação cai de 86,7% para 66,7% (−20 pp [−33,3; −6,7], p = 0,031, ajustado 0,094). | **refutada para 5%**; para 20%, não significativa após a correção |
| TTL da reserva 40 / 80 / 200 | fechamentos publicados sob falhas combinadas: 13,3% com TTL 40 contra 26,7% com 200 (4 seeds; p = 0,125). | sentido previsto, **não significativo** |
| Máximo de correções 0 / 2 | críticas corrigidas no fechamento: 0 contra 1,33; publicação sem falhas cai de 100% para 83,3% (o aprovador cauteloso bloqueia o que não pode corrigir). p ajustado < 0,001. | confirmada |

## RQ6 — ataques sob falha

- **H6a confirmada.** Bloco A: 1.358 ataques ao Approval Gate em 97 execuções atacadas, com
  perda, atraso, indisponibilidade e humano lento ao mesmo tempo; 0 aceitos. Bloco D (SVC-IAM
  ligado): 377 ataques em 13 execuções; 8 registrados como aceitos, **todos o mesmo ataque e
  nenhum indevido** (explicação em "Desvios do pré-registro").
- **H6b confirmada.** A execução atacada terminou com o mesmo resultado da mesma execução sem
  ataque nos 240 pares do SMA básico e nos 240 do SMA com cognição local.

Só há ataque quando há veto pendente (os ataques miram o Approval Gate), por isso 97 de 480
execuções foram atacadas. O workflow equivalente não foi atacado: a bateria de ataques é contra o
barramento de agentes.

## RQ7 — cognição local

![Cognição local × básica](resultados/fig_cognicao.svg)

- **H7a confirmada.** Sem falhas, 0 pares diferentes em 240. A cognição local propõe e confere
  hipóteses (0,23 confirmada e 0,03 refutada por execução) sem mudar o resultado; custa meio
  registro de decisão e cerca de 5 registros de trace a mais por solicitação, nenhuma mensagem.
- **H7b não confirmada.** A classificação correta com cognição local nunca foi menor, e foi maior
  sob perda média (78,6% contra 75,0%), perda alta (79,6% contra 75,0%) e falhas combinadas
  (82,4% contra 78,7%). Mas a diferença vem de 1 ou 2 seeds em 30 e nenhum teste a distingue do
  acaso (p entre 0,5 e 1,0). No subgrupo registrado (desvio irregular com pista na planilha, sob
  perda), sobraram 6 seeds: 45,8% contra 34,7%, uma única seed diferente. **O experimento não
  tem poder para afirmar o ganho.**
- **H7c não confirmada.** O número de mensagens de coordenação é praticamente o mesmo (13,22
  contra 13,26 sob perda média).

Há um custo que as médias escondem: sob perda média, em 6 execuções (uma seed) a avaliação
orçamentária foi entregue com a cognição básica e **não** foi com a local, porque a nova
consulta consumiu o prazo da subtarefa. No mesmo nível de perda, 8 execuções (outra seed)
tiveram a classificação corrigida pela hipótese. A ablação, que força o caso em que a cognição
local deveria agir, dá a medida mais limpa (abaixo).

## Ablação

![Ablação](resultados/fig_ablacao.svg)

Base: SMA com cognição local e tudo ligado, porte médio, desvio irregular sempre plantado e, no
fechamento, um segundo pedido do mesmo mês 2 ticks depois.

| Mecanismo desligado | Medida designada | Com o mecanismo | Sem | Leitura |
|---|---|---|---|---|
| Reenvio do Orquestrador | execução correta, 15% de perda | 40,0% | 28,3% | −11,7 pp [−23,3; −3,3], 5 seeds, p = 0,063 (ajustado 0,125): **não significativo**. Sem reenvio há mais respostas explícitas (80,0% contra 66,7% no fechamento): falhar cedo evita a troca seguinte, que pode travar. |
| Reserva de período | publicações do mesmo mês, sem falhas | 1,00 | 2,00 | Nas 30 seeds, os dois pedidos concorrentes são publicados e 1,37 correção por execução falha por já ter sido feita pelo outro. p ajustado < 0,001. É o mecanismo de efeito mais nítido. |
| Veto com correção | críticas corrigidas, sem falhas | 2,00 | 0 | Sem correção, o diligente concede waiver e o cauteloso bloqueia: a publicação cai de 100% para 66,7%. p ajustado < 0,001. |
| Negociação de prazo | classificação correta, consulta instável, avaliação orçamentária | 50,0% | 50,0% | **Sem efeito na medida designada.** A negociação foi acionada em 6 de 30 execuções; em uma seed ela levou ao resultado da execução sem falha (execução correta 73,3% contra 70,0%). |
| Cognição local | classificação correta, consulta instável | 50,0% | 40,0% | −10,0 pp [−23,3; 0,0], 3 seeds, p = 0,25: **não significativo**. Na execução correta, 73,3% contra 56,7% (avaliação) e 70,0% contra 56,7% (fechamento). |

Dois dos cinco mecanismos (reserva e correção) têm contribuição clara. Os três ligados à
recuperação de falha (reenvio, negociação, cognição local) apontam no sentido esperado, mas com
30 seeds o experimento não separa o efeito do acaso.

## Comportamento coletivo observado

**Quem decidiu o quê.** No SMA sem falhas, 77% das decisões registradas foram tomadas fora do
Orquestrador (17,2 decisões por fechamento, contra 6,1 do controlador único, que toma todas). O
AG-ORC decide a fonte e a classificação de cada desvio e pergunta ao AG-CIN, sem passar pelo
Orquestrador, se há lançamento irregular na conta. O AG-CIN decide o parecer e, depois de uma
correção, percebe o ERP de novo e reconsidera (2,0 reconsiderações de intenção por fechamento).
O humano decide no Approval Gate (0,88 decisão por fechamento, em média). O Orquestrador decide a ordem, os
prazos e os reenvios. No workflow, as mesmas regras rodam em sequência dentro de um componente
que lê todas as fontes, julga a conformidade e executa a correção.

**Onde a distribuição custou.** (1) Mensagens: cada decisão local precisa de uma troca para ser
conhecida pelos outros. (2) Exposição: cada troca pode se perder; a 15% de perda, só metade das
solicitações termina certa. (3) Efeito cascata do protocolo: a recuperação existe para o pedido
que se perde (o prazo esgota, o Orquestrador reenvia), mas não para a resposta que se perde, e
essa assimetria transforma perda em silêncio. (4) Recuperar leva tempo: de 33 a 59 ticks, mais
que o dobro de uma solicitação inteira sem falha.

**Onde a distribuição ajudou.** (1) Em nada que este experimento meça como resultado, quando as
funções são iguais; é o achado central. (2) Na contenção: 1.735 ataques, vindos de identidades
falsas, de agentes legítimos fora do seu papel e da caixa do aprovador sem a pessoa certa, foram
todos rejeitados mesmo com o sistema já degradado, e nenhum mudou o desfecho. Isso depende de
cada agente ter um papel, uma credencial e uma lista de ferramentas; no workflow, o controlador
único acumula tudo e o experimento não tinha como atacá-lo do mesmo modo. (3) Na concorrência: a
reserva de período é a única coisa que impede dois fechamentos do mesmo mês de serem publicados;
sem ela isso aconteceu em 30 de 30 execuções.

**O que as falhas não quebraram.** Nenhuma crítica publicada sem tratamento em 6.480 execuções do
SMA; nenhuma violação dos invariantes de publicação, de efeito externo, de protocolo, de crença
ou de segredo. A única propriedade violada foi a de resposta explícita.

## O que não se confirmou

1. **H7b e H7c (cognição local):** o ganho sob perda existe na média e não é significativo; não
   houve mais mensagens.
2. **H4a para falhas médias e altas:** a maioria das execuções atingidas não recupera o resultado.
3. **H2a para a indisponibilidade de um especialista:** diferença no sentido previsto, p = 0,063.
4. **H5b para o limiar de 5%** (nenhum efeito), **para o limiar de 20%** (não significativo após
   Holm), **para o prazo de aprovação e para o TTL da reserva** (não significativos).
5. **H3b na parte dos registros de auditoria:** o trace não cresce com o controle de acesso.
6. **Ablação do reenvio, da negociação de prazo e da cognição local:** contribuição não
   distinguível do acaso com 30 seeds.
7. **A expectativa de zero violações de invariantes:** 807 das 6.480 execuções do SMA violaram o
   INV-07 (resposta explícita), todas em condições com perda ou indisponibilidade. Nenhum outro
   invariante foi violado.

## Defeitos encontrados pelo experimento

O modelo de falhas aleatórias exercitou caminhos que os 37 cenários fixos nunca exercitaram
(11 deles injetam perda de mensagem, sempre de um pedido).

1. **Resposta perdida vira silêncio (grave).** O barramento muda o estado da conversa quando a
   mensagem é **enviada**. Se a resposta final de um especialista (`inform`, `failure`, parecer)
   se perde na entrega, a conversa já consta como concluída, o temporizador do prazo não avisa
   ninguém e o Orquestrador espera para sempre. Vale para PROT-DEL e PROT-CMP, e também para a
   mensagem `correcao` enviada ao AG-CIN. Os cenários de falha da DSM3 só perdiam pedidos
   (`request`, `query-ref`), que o prazo cobre. Frequência medida: 11% das solicitações com 5%
   de perda, 26% com 15%, 47% com 30%, 5% com um especialista fora do ar. **Não foi corrigido
   aqui.** A correção cabe no barramento (avisar o iniciador quando o prazo esgota sem que uma
   resposta tenha sido *entregue*) e no Orquestrador (prazo também para a etapa de correção);
   depois dela, `make experimento` mede o efeito.
2. **Trace dependia do hash das strings (corrigido).** Com dois estornos no mesmo ciclo de
   correção, o AG-CIN revisava as crenças na ordem de iteração de um conjunto, que muda de um
   processo para outro. O hash do trace deixava de se repetir entre processos, sem mudar nenhum
   resultado. `cenarios --verificar` não via porque compara duas execuções no mesmo processo.
   Corrigido em `agents/cin.py` (ordem fixa); sem isso o `execucoes.csv` não seria reproduzível.
3. **Falso positivo do INV-03 na v0.5.0.** O aviso de prazo do PROT-CMP não muda o estado
   (`de` = `para`) e o verificador o contava como transição fora do protocolo: 165 ocorrências.
   O experimento as conta à parte (coluna `inv03_aviso_sem_transicao`); o verificador não foi
   alterado nesta branch.

## Desvios do pré-registro

1. **Defeito previsto mais amplo que o previsto.** O pré-registro apontava o PROT-CMP; o mesmo
   defeito está no PROT-DEL e responde por três quartos das execuções sem resposta.
2. **Métrica de ataques desdobrada.** Um dos 15 ataques de `env/ataques_acesso.py` ("aprovador
   que participou do lançamento vetado decide sobre ele") supõe que a analista ana participou do
   lançamento. Com plantios sorteados isso nem sempre é verdade; quando ela não está entre os
   envolvidos do ticket, a decisão dela é a de uma aprovadora autorizada, com atestado válido e
   sem conflito, e a política a aceita corretamente. Foram 8 casos. O CSV traz `ataques_aceitos`
   (bruto), `ataques_sem_premissa` (esses casos) e a diferença, que é zero. A regra foi
   acrescentada depois de ver o primeiro caso, numa rodada de teste do aparato.
3. **Métrica exploratória acrescentada:** `sinalizacao_correta` (só as contas sinalizadas, a
   definição da DSM3), para mostrar quanto do erro de classificação vem das contas atribuídas a
   controle. Não entra em nenhum teste de hipótese.
4. **Correção do verificador contornada na medição** (item 3 dos defeitos), para o resultado não
   depender dela.
5. **Rodadas do aparato antes do experimento.** Enquanto o código era escrito, foram olhadas uma
   rodada de fumaça nas seeds 1 a 30 com uma configuração que não é nenhuma condição do
   experimento (contagem de status e quatro traces) e rodadas do modo rápido (seeds 1 a 3). A
   equivalência do workflow foi desenvolvida em seeds fora de 1 a 30. O tamanho da amostra, as
   seeds, as condições e as comparações não mudaram depois disso.
6. **Reexecuções.** O experimento completo rodou quatro vezes: a primeira, duas de conferência
   de reprodutibilidade (mesmo CSV) e uma depois de ajustar a correção de Holm para deixar de
   fora as comparações idênticas em todos os pares, como o plano de análise já dizia. O
   `execucoes.csv` é o mesmo nas quatro; só os p ajustados mudaram, e nenhuma decisão de
   significância mudou.
7. **Falta o bloco de fuzz** citado no plano geral do projeto (invariantes em milhares de seeds):
   não estava no pré-registro e não foi feito.

## Ameaças à validade

As previstas no pré-registro continuam valendo. O que a execução mostrou a mais:

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
- **Interna — o defeito do item 1 domina as medidas de robustez e de recuperação.** Depois de
  corrigido, os números de RQ2, RQ4 e da ablação do reenvio mudam; os de RQ1, RQ3 sem falhas e
  RQ6 não dependem dele.
- **Conclusão — pouco poder para efeitos raros.** Como as perdas são sorteadas por mensagem com
  chave comum, as 8 células de uma seed compartilham o destino das mensagens. Isso emparelha bem
  os braços, mas faz o efeito aparecer em poucas seeds inteiras: as comparações de cognição
  local, negociação e reenvio têm de 1 a 5 seeds diferentes em 30.
- **Conclusão — a amostra não teve aprovador rigoroso.** O caminho "bloqueia sempre" não foi
  exercitado no experimento (é exercitado nos cenários da DSM3).
- **Externa — um defeito de protocolo específico deste sistema** responde pela maior parte da
  perda de robustez. Não é uma propriedade de sistemas multiagentes em geral.
- **Tempo de parede** medido numa máquina, numa rodada, com o YAML dos protocolos em cache; serve
  de ordem de grandeza (mediana de 5,7 ms por execução do SMA básico sem falhas, 7,2 ms com
  cognição local e 0,3 ms do workflow equivalente) e nada mais.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `resultados/execucoes.csv` | Uma linha por execução (9.360), com chave, carga sorteada, métricas e hash do trace. Reproduzível byte a byte. |
| `resultados/resumo.json` e `resumo.md` | Tabelas por pergunta, com média por seed e IC de 95%. |
| `resultados/testes.md` | Testes de hipótese com tamanho de efeito e p ajustado, e a conferência da biblioteca estatística. |
| `resultados/fig_*.svg` | Seis figuras em pequenos múltiplos. |
| `resultados/manifesto.json` | Versão, seeds, condições, parâmetros, probabilidades do modelo de falhas e SHA-256 do CSV. |
| `resultados/tempo_parede.csv` | Milissegundos por execução. **Não reproduzível.** |
