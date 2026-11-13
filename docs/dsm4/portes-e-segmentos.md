# Portes novos (MEI e Média empresa II) e segmentos

<span class="badge-ok">implementado</span> · DSM4

Pedido do dono do produto: aprofundar os quatro portes (feito na DSM3, ver `docs/dsm2/portes.md`),
acrescentar o **MEI**, **subdividir a média** e variar por **segmento** (comércio, serviços,
indústria). Tudo foi acrescentado **sem mudar nenhum valor dos quatro portes de antes**, sem mudar a
versão das normas (`normas-v2`, que entra no trace) e sem mudar a ordem de consumo do gerador
aleatório: os 140 traces revisados da DSM3 têm o mesmo hash.

## Fontes legais (consultadas em 12/11/2026)

| Fato | Fonte | O que confirmou |
|---|---|---|
| Limite do MEI | LC 123/2006, art. 18-A, § 1º, redação da LC 188/2021 — <https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm> | receita bruta no ano-calendário anterior de até **R$ 81.000,00** |
| Empregado do MEI | LC 123/2006, art. 18-C (redação da LC 155/2016) | um único empregado |
| Mudança futura do MEI | LC 238/2026 — <https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp238.htm> | R$ 110.000,00 no ano-calendário de 2027 (art. 2º); R$ 140.000,00 com efeitos a partir de 1º/1/2028 (art. 10, I); até 2 empregados a partir de 1º/1/2027 (art. 10, II); ampliação condicionada à lei orçamentária (art. 3º) |
| ME e EPP | LC 123/2006, art. 3º, I e II (redação da LC 155/2016) | ME até R$ 360.000,00; EPP até R$ 4.800.000,00 |
| Média I e II | BNDES, "Porte de empresa" — <https://www.bndes.gov.br/wps/portal/site/home/financiamento/guia/porte-de-empresa> | Média Empresa I: mais de R$ 4,8 milhões até R$ 90 milhões; **Média Empresa II: mais de R$ 90 milhões até R$ 300 milhões**; grande acima de R$ 300 milhões (receita operacional bruta anual) |

A competência simulada é 2026-09, então vale o limite de **R$ 81 mil** do MEI; a LC 238/2026 está
anotada no `models/portes.yaml` para quando a competência passar de 2026. A página do BNDES não
informa data de atualização nem o ato normativo em que se baseia.

**A confirmar** (não conferido na fonte nesta implementação; está marcado assim na ficha): a lista
exata de obrigações acessórias do MEI (DAS-MEI, DASN-SIMEI e o relatório mensal das receitas
brutas, regulados por resolução do CGSN) e a data de publicação da LC 238/2026 no DOU.

## O que é lei e o que é parâmetro da simulação

- **Lei/classificação oficial**: os limites de receita acima e o fato de o MEI ser um
  **enquadramento por opção** (SIMEI), não só uma faixa de receita. Por isso
  `porte_por_receita(receita, mei=True)` só devolve `mei` para quem optou; uma ME com receita
  abaixo de R$ 81 mil continua `micro` (TEST-170).
- **Parâmetros da simulação** (como nos quatro portes de antes): escala da receita sintética,
  alçadas, severidades, materialidade, pesos BDI, ciclos de correção e toda a ficha descritiva.
  A Média empresa II é classificação oficial do BNDES; os números de regra dela são parâmetros.

## Portes novos (`models/portes.yaml`, `env/portes.py`)

`PORTES = ("mei", "micro", "pequena", "media", "media_ii", "grande")`, do menor ao maior.

| | MEI | Média empresa II |
|---|---|---|
| Receita anual simulada | sempre abaixo de R$ 81 mil (escala 0,02) | entre R$ 90 e 300 milhões em 996 de 1.000 seeds, e em todas as seeds dos testes (escala 105) |
| Pessoas | uma: `elisa` como `titular` | as cinco da média |
| ERP | não (planilha, como a micro) | sim |
| Alçadas | titular sem limite (não há a quem delegar) | analista R$ 15 mil, gerente R$ 75 mil, diretor R$ 300 mil |
| Severidades | SoD e competência não críticas; alçada e duplicidade críticas | como a média |
| Controle compensatório | SoD impossível: revisão mensal pelo titular, conferida pelo contador | — |
| Materialidade | 20% e R$ 200 | 7% e R$ 20 mil |
| Pesos BDI (AG-CIN / AG-ORC) | conformidade 10, prazo 9 / precisão 1, tempestividade 2 | 10, 4 / 4, 1 |
| Ciclos de correção | 2 | 1 |

A `media` continua com o teto legal da classe média (R$ 300 milhões) e, na classificação por
receita, cede a faixa de R$ 90 a 300 milhões à subdivisão `media_ii` (campos `subdivide` e
`receita_bruta_anual_min`; `classe_legal("media_ii") == "media"`). No MEI, o plantio `alcada` é
recusado com erro (não há alçada menor para violar) em vez de gerar um gabarito falso.

## Segmentos (`models/segmentos.yaml`, `env/segmentos.py`)

| Segmento | Unidades | Custo variável | Centros de custo | Rateio dos custos fixos (AG-CUS) |
|---|---|---|---|---|
| `software_servicos` (padrão, a SMA de sempre) | Software, Serviços | licenças, nuvem e horas (40–65% do preço) | Administrativo, Comercial, Operações | percentual fixo da diretoria, 60/40 (`rateio-v1`) |
| `comercio` | Loja física, Loja virtual | CMV pelo estoque (55–72%) | Administrativo, Lojas, Logística e estoque | área ocupada em m², 80/20 |
| `servicos` | Consultoria, Operação terceirizada | mão de obra direta, 80% do custo variável (45–62%) | Administrativo, Comercial, Entrega | horas trabalhadas, 65/35 |
| `industria` | Linha 1 (usinagem), Linha 2 (montagem) | matéria-prima, MOD e CIF variáveis (50–68%) | Administrativo, Produção (CIF fixos), Manutenção | horas-máquina, 70/30 |

Cada segmento tem o seu plano de contas de orçamento (quatro contas e um chamariz). O direcionador
vira conhecimento do AG-CUS na montagem do sistema (`build_system`), e o gabarito (`ds.gold`) é
calculado com o mesmo direcionador, então o resultado por unidade do AG-CUS é conferido contra o
que foi gerado (TEST-173). O gabarito ganha `estrutura_custos` fora do padrão: estoque inicial +
compras − estoque final = CMV no comércio, horas de MOD em serviços, custo de produção com os CIF
fixos rateados na indústria (TEST-174). O segmento padrão gera exatamente os mesmos dados de antes
e o `meta` do trace só ganha o campo `segmento` fora do padrão (TEST-175).

Onde aparece: `Dataset(segmento=...)`, `Ambiente(segmento=...)`, `build_system(segmento=...)`,
`Scenario(segmento=...)`, `fin-mas run --segmento`, `fin-mas serve --segmento`, `fin-mas instalar
--segmento`, comando `reiniciar` do dashboard com `segmento`, `/api/portes` (`segmentos` e
`segmento_atual`), `/api/modelos` (exemplo por segmento) e a aba "Porte" do dashboard. Na planilha
modelo, a aba Empresa ganhou o campo opcional "Segmento"; sem ele, vale o padrão.

## Cenários nomeados

| Cenário | O que observar |
|---|---|
| `fechamento_mei` | veto só da duplicidade (crítica); estorno aprovado; SoD em todos os lançamentos vira uma ressalva com o controle compensatório; realizado da planilha |
| `fechamento_media_ii` | veto da alçada com reaprovação; dois desvios acima de 7% e de R$ 20 mil; publicado |
| `fechamento_comercio` | AG-CUS rateia por m² (80/20); duplicidade estornada; publicado |
| `fechamento_servicos` | AG-CUS rateia por horas (65/35); SoD vetado e reaprovado; publicado |
| `fechamento_industria` | AG-CUS rateia por horas-máquina (70/30); NF duplicada atribuída a controle; estorno aprovado |

Os cinco ficam no nível de cognição `basico`, como `fechamento_micro`, `fechamento_pequena` e
`fechamento_grande`: o que muda neles é a regra do porte e a forma do segmento, não a cognição.
