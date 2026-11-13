# Experimento da DSM4 — pré-registro

Este documento foi escrito e versionado **antes** de existir qualquer resultado, antes mesmo de
existir o código que roda o experimento. O commit que o introduz é anterior a todos os commits
de `src/fin_mas/{caos,baseline_eq,estatistica,estudo}.py` e de `docs/dsm4/resultados/`; o
histórico do git é a prova. O que foi medido e o que não se confirmou está em
`docs/dsm4/resultados.md`; qualquer desvio do que está escrito aqui é listado lá, na seção "Desvios do
pré-registro".

## Por que refazer o experimento

O experimento da DSM3 (`python -m fin_mas comparar`) recebeu duas críticas, ambas procedentes:

1. **Funções diferentes.** O workflow centralizado usado como linha de base não tem veto,
   correção nem aprovação. Parte da vantagem do SMA vem dessa diferença de *funções*, não do
   paradigma (agentes, autonomia, coordenação).
2. **Variância zero.** As 10 seeds mudam os valores dos dados, mas as métricas dependem dos
   plantios, que eram fixos por cenário. As réplicas só confirmavam o determinismo.

O redesenho responde às duas: um **workflow centralizado funcionalmente equivalente**, com a
equivalência garantida por teste, e **aleatoriedade controlada** (plantios, falhas, humano e
ataque sorteados por seed, reproduzíveis).

## Perguntas de pesquisa e hipóteses

Cada hipótese diz o que a derrubaria. "Par" é o mesmo porte, intenção e seed em dois braços ou
duas condições.

| | Pergunta | Hipótese | O que a refuta |
|---|---|---|---|
| RQ1 | Com as mesmas funções, o SMA entrega mais qualidade que um workflow centralizado? | **H1a:** sem falhas, o SMA básico e o workflow equivalente produzem o mesmo resultado em 100% dos pares (mesmo status, DRE, contas sinalizadas, contas atribuídas a controle e correções). **H1b:** o workflow mínimo da DSM3 classifica pior e publica críticas sem tratamento; essa diferença é de função. | H1a: qualquer par diferente. H1b: workflow mínimo igual ou melhor. |
| RQ2 | Quão robusto é cada braço quando a comunicação e as pessoas falham? | **H2a:** sob perda de mensagens, indisponibilidade de agente e falhas combinadas, a fração de execuções corretas do SMA é **menor** que a do workflow equivalente, que não tem mensagens entre componentes para perder. **H2b:** a robustez do SMA cai com o nível de perda (baixa > média > alta). **H2c:** sob humano lento, os dois empatam (o Approval Gate é o mesmo). **H2d:** nenhum braço com veto publica crítica sem tratamento, em nenhuma condição. | H2a: SMA igual ou melhor em alguma condição de comunicação. H2b: ordem diferente. H2c: diferença significativa. H2d: qualquer crítica publicada sem tratamento. |
| RQ3 | Quanto custa coordenar e quanto custa o controle de acesso? | **H3a:** o SMA troca mais mensagens e leva mais ticks que o workflow equivalente em todas as condições. **H3b:** ligar o controle de acesso por pessoa (SVC-IAM) não acrescenta mensagens nem ticks; acrescenta registros de auditoria e tempo de parede. | H3a: SMA igual ou mais barato. H3b: mensagens ou ticks a mais. |
| RQ4 | Quando uma falha atinge o SMA, ele se recupera? Em quanto tempo? | **H4a:** a maior parte das execuções atingidas termina com o mesmo resultado da execução sem falha. **H4b:** a recuperação custa pelo menos um prazo de consulta (10 ticks) na mediana. **H4c (defeito previsto, ver abaixo):** uma parte das execuções com perda fica **sem resposta explícita**. | H4a: menos da metade recupera. H4b: mediana menor que 10. H4c: nenhuma execução sem resposta. |
| RQ5 | O resultado depende do porte e dos parâmetros? | **H5a:** a microempresa (sem ERP) classifica pior quando a planilha diverge, porque não há segunda fonte para reconciliar. **H5b:** mais tentativas aumentam a robustez; prazo de subtarefa maior aumenta a latência sob falha; prazo de aprovação maior reduz bloqueios com humano lento; limiar de desvio mal ajustado derruba a classificação; TTL da reserva curto aborta fechamentos; sem correção não há publicação limpa de pacote com crítica. | Cada uma: efeito nulo ou no sentido oposto. |
| RQ6 | Os ataques continuam sendo rejeitados quando o sistema já está sob falha? | **H6a:** zero ataques aceitos. **H6b:** o resultado da execução atacada é igual ao da mesma execução sem o ataque. | H6a: um ataque aceito. H6b: resultado diferente por causa do ataque. |
| RQ7 | A cognição local (regras que propõem hipóteses) melhora o resultado em relação à cognição básica? | **H7a:** sem falhas, não: os resultados são iguais e a cognição local só custa chamadas de leitura. **H7b:** sob perda, a classificação correta com cognição local é maior ou igual, e estritamente maior nas execuções em que há desvio causado por lançamento irregular e a planilha dá a pista. **H7c:** o ganho custa mais mensagens. | H7a: resultados diferentes sem falha. H7b: cognição local pior, ou igual também no subgrupo. H7c: mesmo número de mensagens. |

**Defeito previsto pela leitura do código, antes de rodar.** O protocolo de conformidade
(PROT-CMP) só avisa o Orquestrador do prazo esgotado enquanto o AG-CIN ainda não respondeu
nada. Se o parecer do AG-CIN (ou a mensagem de correção enviada a ele) se perder depois disso,
ninguém é avisado e a solicitação pode ficar sem resposta. Os cenários de falha da DSM3 nunca
perdem essas mensagens, por isso o defeito não apareceu. A predição é que a perda aleatória o
exponha como violação do invariante INV-07 (toda solicitação recebe resposta explícita). O
experimento **não corrige** o defeito: mede a frequência e registra onde ele está.

## Braços

| Braço | O que é |
|---|---|
| `sma_basico` | O SMA como entregue na DSM3, com `cognicao="basico"`. |
| `sma_local` | O mesmo SMA com `cognicao="local"`: o AG-ORC recebe hipóteses das regras locais e as verifica. |
| `wf_equivalente` | Workflow centralizado **funcionalmente equivalente** (`baseline_eq.py`): um controlador único e sequencial que aplica as mesmas regras de reconciliação planilha × ERP, atribuição de desvio, conformidade com veto, correção e aprovação, com o mesmo SVC-POL e o mesmo aprovador simulado. Sem agentes, sem negociação, sem replanejamento. |
| `wf_minimo` | O `baseline.py` da DSM3, intacto. Referência histórica, só na condição nominal (não tem comunicação nem humano para falhar). |

LLM fica **fora** do experimento. Nenhum braço chama modelo de linguagem.

A palavra "equivalente" é sustentada por um teste automatizado (`tests/e2e/`): sem falhas, nos
cenários comparáveis da DSM3 e nas cargas sorteadas, em todos os portes, o workflow equivalente
e o SMA básico têm de dar o mesmo status final, a mesma DRE, as mesmas contas sinalizadas e
atribuídas e as mesmas correções. Onde não derem, a diferença é documentada, não escondida.

## Fatores e níveis

**Carga, igual para todos os braços e condições da mesma seed (blocagem).** Uma execução é uma
solicitação a uma empresa sintética de um porte.

- **Seed:** 1 a 30. A seed gera os dados da empresa e, por fluxos independentes
  (`random.Random(f"{seed}:{fator}")`, que não tocam no gerador dos dados), tudo o que é sorteado.
- **Porte:** micro, pequena, média, grande (`models/portes.yaml`).
- **Intenção:** `fechar_mes` e `avaliar_orcamento`.
- **Plantios sorteados:** cada um de `alcada`, `sod`, `duplicidade`, `competencia`,
  `desvio_orcamentario`, `divergencia_fonte` e `desvio_irregular` entra com probabilidade 0,35,
  de forma independente. Se houver `desvio_irregular`, a observação da planilha vem parafraseada
  com probabilidade 0,3 (as regras locais não a reconhecem). Se houver `desvio_orcamentario`,
  vem com um alarme falso com probabilidade 0,3.
- **Perfil do aprovador, sorteado:** diligente (0,75: corrige se a correção for oferecida,
  senão concede waiver), cauteloso (0,15: corrige se oferecida, senão bloqueia), rigoroso (0,10:
  bloqueia sempre).

**Condições.** As falhas de comunicação incidem sobre as mensagens entre agentes (PROT-DEL,
PROT-CMP, PROT-QRY). As mensagens com as pessoas (PROT-SOL com o solicitante e PROT-APR com o
aprovador) não se perdem: são a interface local do sistema, e a demora humana é modelada à parte.

| Condição | O que acontece |
|---|---|
| `nominal` | Nenhuma falha. A variação vem dos dados, dos plantios e do perfil do aprovador. |
| `perda_baixa` / `perda_media` / `perda_alta` | Cada mensagem entre agentes se perde com probabilidade 0,05 / 0,15 / 0,30. |
| `indisponibilidade` | Um especialista sorteado (AG-CUS, AG-ORC, AG-RES, AG-CIN ou AG-REL) fica fora do ar por 8 a 30 ticks, a partir de um tick sorteado entre 1 e 30. |
| `humano_lento` | O aprovador demora entre 0,3 e 1,3 vez o prazo da aprovação para decidir; com probabilidade 0,15 não aparece. |
| `combinadas` | Perda de 0,10, atraso de entrega de 0 a 2 ticks por mensagem, uma indisponibilidade e humano lento, ao mesmo tempo. |
| `combinadas_ataque` | O mesmo, mais os 14 ataques de `env/ataques.py` disparados enquanto o veto aguarda o aprovador. |

O sorteio de perda e de atraso é feito por mensagem com chave própria (remetente, destinatário,
protocolo, performativo e ordem de ocorrência), para que a mesma mensagem tenha o mesmo destino
em braços e variantes diferentes da mesma seed (números aleatórios comuns). O Orquestrador, o
solicitante e o aprovador não ficam indisponíveis: a queda do Orquestrador é um ponto único de
falha conhecido e **não** é exercitada aqui (limitação).

**Blocos.**

| Bloco | Desenho | Para quê |
|---|---|---|
| A — principal | 3 braços × 8 condições + `wf_minimo` na nominal; 4 portes × 2 intenções × 30 seeds = 6.000 execuções | RQ1, RQ2, RQ3, RQ4, RQ5 (porte), RQ6, RQ7 |
| B — varredura | Porte médio, `sma_basico`, condições nominal e combinadas; um parâmetro por vez, os outros no padrão: prazo de subtarefa {15, **30**, 60}; máximo de tentativas {1, **2**, 3}; máximo de correções {0, **2**}; TTL da reserva {40, 80, **200**}; prazo de aprovação {10, **20**, 40}; limiar percentual de desvio {5, **10**, 20}. O `wf_equivalente` roda nos três parâmetros que se aplicam a ele (correções, prazo de aprovação, limiar). | RQ5 (parâmetros) |
| C — ablação | Porte médio, base `sma_local` com tudo ligado; um mecanismo desligado por vez; condições nominal, `perda_media` e `consulta_instavel` (só as consultas ao AG-CIN se perdem, com probabilidade 0,5). `desvio_irregular` sempre plantado; no fechamento, um segundo pedido do mesmo mês chega 2 ticks depois (expediente concorrente). | Contribuição de cada mecanismo |
| D — controle de acesso | Porte médio, `sma_basico` com o SVC-IAM ligado (decisão com atestado de pessoa); condições nominal e `combinadas_ataque` (aqui com os ataques de `env/ataques.py` e os 15 de `env/ataques_acesso.py`). Comparado com as mesmas seeds do bloco A. | RQ3 (acesso), RQ6 |

Mecanismos da ablação e a medida em que cada um deve aparecer:

| Mecanismo desligado | Como | Medida designada |
|---|---|---|
| Reenvio do Orquestrador | máximo de tentativas = 1 | fração de execuções corretas em `perda_media` |
| Reserva de período | o Orquestrador não reserva o mês | publicações do mesmo período por execução (o certo é 1) no fechamento concorrente |
| Veto com correção | máximo de correções = 0 (o veto continua; a correção deixa de ser oferecida) | fração de fechamentos publicados sem ressalva de waiver e críticas corrigidas, na nominal |
| Negociação de prazo | extensão máxima = 0 (toda proposta é recusada) | classificação correta em `consulta_instavel`, intenção `avaliar_orcamento` |
| Cognição local | `cognicao="basico"` | classificação correta em `consulta_instavel` |

## Métricas

Todas saem do trace e do gabarito (`ds.gold`, que vem do que foi plantado, não das regras dos
agentes). Uma linha de `execucoes.csv` por execução.

| Métrica | Definição operacional |
|---|---|
| Resposta explícita | 1 se o solicitante recebeu `inform`, `failure`, `refuse` ou `not-understood`; 0 se a execução terminou sem resposta. |
| Conclusão | 1 se a resposta foi `inform` (resultado publicado). |
| Classificação correta | 1 se as contas sinalizadas como desvio são exatamente `gold["desvios"]` **e** as atribuídas a controle são exatamente `gold["desvios_atribuidos"]`; medida sempre que a avaliação orçamentária foi produzida. |
| DRE correta | 1 se a DRE publicada é igual a `gold["dre"]` (só `fechar_mes`). |
| Conformidade correta | 1 se os achados do primeiro parecer (regra, lançamento, severidade) são exatamente `gold["nao_conformidades"]` (só `fechar_mes`). |
| Críticas publicadas sem tratamento | Não conformidades críticas do gabarito que estavam no pacote publicado sem correção nem waiver. |
| Resultado igual ao nominal | 1 se status, DRE, contas sinalizadas, contas atribuídas e correções são iguais aos da execução do mesmo braço, porte, intenção e seed na condição nominal. |
| **Execução correta (robustez)** | resposta explícita **e** nenhuma crítica publicada sem tratamento **e** resultado igual ao nominal. A robustez de um braço numa condição é a fração de execuções corretas. |
| Degradação segura | resposta explícita e nenhuma crítica publicada sem tratamento, mas resultado diferente do nominal (falhou, bloqueou ou publicou com ressalva a mais). |
| Latência lógica | ticks entre o pedido e a resposta final. No workflow, 3 ticks por etapa (a premissa do `baseline.py`) mais a espera pelo aprovador no relógio do barramento. |
| Mensagens por solicitação | mensagens trocadas na solicitação. `mensagens` conta todas; `mensagens_coordenacao` exclui as três do PROT-SOL (a interface com o solicitante, que o workflow não usa). |
| Recuperação | ticks entre a primeira falha que atingiu a solicitação (primeira mensagem perdida ou primeiro prazo esgotado) e a resposta final; definida só quando houve falha e resposta. |
| Ataques aceitos | ataques cujo efeito foi aceito pelo barramento, pela política ou pelo gateway, sobre os tentados. Esperado: 0. |
| Violações de invariantes | violações acusadas por `invariantes.verificar` no trace, por invariante. Esperado: 0 para INV-01 a INV-06 e INV-08; para INV-07, ver o defeito previsto. |
| Registros de auditoria | número de registros do trace (custo de auditoria do controle de acesso). |
| Tempo de parede | milissegundos por execução, num arquivo separado (`tempo_parede.csv`), marcado como **não reproduzível**; nunca entra em teste de hipótese. |

## Plano de análise

- **Unidade estatística: a seed** (n = 30). Para cada braço e condição, o valor de uma seed é a
  média da métrica nas células daquela seed (portes × intenções). Células de portes diferentes
  da mesma seed compartilham plantios e não são tratadas como independentes.
- **Descrição:** média, desvio padrão, mediana e intervalo de confiança de 95% por bootstrap
  percentil (2.000 reamostragens, semente fixa).
- **Comparações pareadas** (dois braços ou duas condições nas mesmas seeds): Wilcoxon de postos
  sinalizados, bilateral; diferenças nulas descartadas; distribuição exata quando restam até 25
  pares, aproximação normal com correção de empates e de continuidade acima disso. Se todas as
  diferenças forem zero, o teste não se aplica e o resultado é relatado como "idêntico em todos
  os pares".
- **Comparações não pareadas** (grupos de execuções definidos pelo que aconteceu nelas, como o
  tempo de recuperação por tipo de falha): Mann-Whitney U, bilateral.
- **Tamanho de efeito:** delta de Cliff (desprezível < 0,147; pequeno < 0,33; médio < 0,474;
  grande acima) e diferença média pareada com IC de 95% por bootstrap.
- **Comparações múltiplas:** correção de Holm dentro de cada família de testes (uma família por
  pergunta de pesquisa, mais uma para a varredura e uma para a ablação), α = 0,05. As famílias
  são as comparações listadas nas hipóteses acima; nenhuma comparação é acrescentada depois de
  ver os dados sem ser marcada como exploratória.
- **H1a não é um teste de hipótese.** "Sem diferença" não se prova com p alto. O critério é
  identidade: número de pares com resultado diferente, que tem de ser zero.
- **Subgrupo registrado para H7b:** execuções com `desvio_irregular` plantado e observação não
  parafraseada, nas condições com perda.
- Só biblioteca padrão. A biblioteca estatística é conferida contra exemplos calculados à mão.

## Critérios de parada

- Tamanho fixo: 30 seeds (1 a 30), decidido aqui. Não há parada antecipada nem seeds extras
  depois de ver resultados.
- Uma execução que levante exceção vira uma linha com status `erro`; nenhuma execução é
  descartada.
- O experimento só é rodado de novo por inteiro se houver defeito no próprio aparato de medição
  (não no sistema medido). Cada reexecução por esse motivo é listada em "Desvios do
  pré-registro", com a causa.
- `execucoes.csv` tem de sair idêntico, byte a byte, numa segunda execução.

## Ameaças à validade previstas

- **Construto — a robustez favorece o workflow por construção.** O modelo de falhas atinge a
  comunicação entre agentes, e o workflow monolítico não tem essa comunicação. A comparação mede
  o preço da distribuição e quanto dele os mecanismos de recuperação devolvem; não mede um
  workflow distribuído (controlador com serviços remotos), que não foi construído.
- **Construto — o que o SMA compra não é só resultado.** Separação de autoridade (quem calcula
  não aprova), menor privilégio por agente e trilha de quem decidiu o quê não aparecem em
  métricas de resultado. O experimento os mede só indiretamente (ataques e invariantes).
- **Construto — latência lógica.** Um tick é uma unidade do relógio do barramento. Os 3 ticks
  por etapa do workflow são uma premissa.
- **Interna — equivalência.** O workflow equivalente foi escrito depois do SMA, pelos mesmos
  autores, lendo o código dos agentes. O teste de equivalência cobre a condição sem falhas; sob
  falha os dois braços divergem por desenho.
- **Interna — pareamento parcial.** A carga é pareada por seed; a realização das perdas, não
  totalmente: braços diferentes trocam mensagens diferentes. As chaves por mensagem reduzem o
  problema entre braços do SMA, não entre SMA e workflow.
- **Externa — dados sintéticos com plantio.** O gabarito é o que foi plantado. Empresas reais
  têm erros combinados e ambíguos que os plantios não cobrem.
- **Externa — modelo de falhas simples.** Perda independente por mensagem, sem rajadas, sem
  partição de rede, sem falha de dados nem do Orquestrador.
- **Conclusão — muitos testes.** Há dezenas de comparações; Holm controla o erro por família,
  não no experimento inteiro. Métricas binárias agregadas por seed têm muitos empates.
- **Conclusão — proporções das cargas são escolhas.** As probabilidades de plantio, de perda e
  de perfil do aprovador foram fixadas aqui, sem ajuste posterior; outros valores dariam outras
  frequências.

## Como reproduzir

```bash
python -m fin_mas experimento --replicas 30 --out docs/dsm4/resultados   # ou: make experimento
python -m fin_mas experimento --rapido --out /tmp/experimento            # poucos segundos, para conferir o aparato
```

Saídas: `execucoes.csv` (dado bruto), `resumo.json`, `resumo.md`, `testes.md`, figuras SVG,
`manifesto.json` (versão, seeds, parâmetros e hash do CSV) e `tempo_parede.csv`.
