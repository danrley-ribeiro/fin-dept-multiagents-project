---
orphan: true
---

# Cognição dos agentes na DSM4

Decisão e justificativa em {doc}`ADR-010-especialistas-bdi`. Esta página descreve o que cada
agente acredita, deseja e planeja, o que dispara cada coisa, e os três mecanismos novos:
aprendizado, compromisso e conhecimento normativo. Os trechos de trace são saídas reais
(`python -m fin_mas run --scenario NOME`, seed 42), sem as colunas de sequência e conversa e
com os valores longos abreviados por `...`.

## Níveis de cognição e quem é BDI em cada um

| Nível | AG-ORC | AG-CIN | AG-RES | AG-CUS | AG-REL |
|---|---|---|---|---|---|
| `basico` | BDI, sem hipóteses | BDI | reativo | reativo | reativo |
| `local` | BDI + hipóteses locais + memória + aprendizado | BDI + base normativa | **BDI** + hipóteses locais + aprendizado | **BDI** | **BDI** |
| `llm` | o de cima + hipóteses por LLM (flag) | igual a `local` (sem LLM) | igual a `local` + comentário por LLM (flag) | igual a `local` (sem LLM) | igual a `local` + síntese por LLM (flag) |

`basico` é o braço de comparação: os cenários revisados da DSM3 rodam nele e seus traces não
mudam. O AG-ORQ não é BDI nem usa LLM em nenhum nível.

## O ciclo, igual para todos

`perceber → revisar crenças → reconsiderar intenções → gerar opções → deliberar → executar`.
A deliberação lista todos os planos do desejo, com `aplicavel`, o motivo e a utilidade, e
escolhe o aplicável de maior utilidade. Utilidade = soma dos pesos dos desejos permanentes
que o plano atende × 10 + preferência. Os pesos vêm do porte (`models/portes.yaml` para
AG-ORC e AG-CIN; `models/cognicao.yaml` para os três novos). Plano que falha é marcado e o
agente delibera de novo sem ele.

## Por agente

### AG-RES (`agents/res_bdi.py`)

| | Conteúdo | O que dispara |
|---|---|---|
| **Crenças** | receita do ERP; situação de cada insumo (`aguardando`, `recebido`, `sem_resposta`, `recusado`, `indisponivel`); linhas da DRE e EBITDA%; médias do histórico; variação do EBITDA% e se é relevante; explicação da variação; correções aprovadas em meses do histórico | pedido do Orquestrador; resposta, recusa ou timeout de consulta; tool `erp.historico_resultado`; cálculo; SVC-MEM |
| **Desejos** | `obter_insumo` (1), `explicar_variacao` (2), `consolidar` (3) | insumo ainda não resolvido; hipótese validada sem evidência; tudo resolvido |
| **Permanentes** | completude, tempestividade, explicabilidade | pesos do porte |

| Desejo | Plano | Atende | Contexto |
|---|---|---|---|
| obter_insumo | P-CONSULTAR-ESPECIALISTA | completude + tempestividade | o dono do insumo está no diretório |
| | P-CONSULTAR-DE-NOVO | completude + tempestividade | a consulta expirou (não foi recusada), há tentativa e cabe no prazo |
| | P-DAR-POR-INDISPONIVEL | tempestividade | sempre |
| explicar_variacao | P-DETALHAR-COM-CUSTOS | explicabilidade | hipótese de custo fixo, confiança ≥ 0,5, cabe no prazo |
| | P-CONFERIR-NO-HISTORICO | tempestividade | há histórico (sem mensagem; menos preciso) |
| | P-ARQUIVAR-HIPOTESE | — | sempre |
| consolidar | P-CONSOLIDAR-COMPLETO | completude + tempestividade | os dois insumos e a receita conferida |
| | P-CONSOLIDAR-COM-RESSALVA | tempestividade | só falta o orçamento (não crítico) |
| | P-FALHAR-EXPLICITAMENTE | completude | falta insumo ou a receita diverge |

Reconsideração: se a delegação do Orquestrador já expirou, os desejos da tarefa deixam de
valer e as intenções são abandonadas.

Cenário `res_insumo_faltante` (o AG-ORC não responde a duas consultas), média empresa:

```
t=016 TIMEOUT contra AG-ORC  [AGUARDANDO -> EXPIRADA]
t=016 CRENCA AG-RES: insumo[orcamento]@DEL-003 = {"estado": "sem_resposta", ...} (fonte: SVC-A2A (timeout de QRY-002))
t=016 INTENCAO AG-RES: AG-RES-I002 P-CONSULTAR-ESPECIALISTA falhou (timeout de AG-ORC)
t=016 DELIBERA AG-RES: obter_insumo:orcamento|DEL-003 -> P-CONSULTAR-DE-NOVO [P-CONSULTAR-ESPECIALISTA x u=51; P-CONSULTAR-DE-NOVO u=50; P-DAR-POR-INDISPONIVEL u=30]
t=026 DELIBERA AG-RES: obter_insumo:orcamento|DEL-003 -> P-DAR-POR-INDISPONIVEL [P-CONSULTAR-ESPECIALISTA x u=51; P-CONSULTAR-DE-NOVO x u=50; P-DAR-POR-INDISPONIVEL u=30]
t=026 DELIBERA AG-RES: consolidar:DEL-003 -> P-CONSOLIDAR-COM-RESSALVA [P-CONSOLIDAR-COMPLETO x u=51; P-CONSOLIDAR-COM-RESSALVA u=30; P-FALHAR-EXPLICITAMENTE u=20]
```

Com `--porte grande` a última linha vira
`-> P-FALHAR-EXPLICITAMENTE [... P-CONSOLIDAR-COM-RESSALVA u=10; P-FALHAR-EXPLICITAMENTE u=50]`.
No nível `basico` o mesmo cenário termina em `failure` e nada é publicado.

Cenário `res_explica_variacao`:

```
t=008 CRENCA AG-RES: variacao[ebitda_pct]@2026-09 = {"atual": 27.07, "delta_pp": -8.03, "media": 35.1, "relevante": true} (fonte: cálculo sobre AG-CUS (QRY-001) e mcp://erp/historico_resultado)
t=008 HIPOTESE AG-RES: AG-RES-H001 causa_custo_fixo(ebitda_pct) aceita (local:R-RES-CUSTO-FIXO)
t=008 DELIBERA AG-RES: explicar_variacao:AG-RES-H001|DEL-003 -> P-DETALHAR-COM-CUSTOS [P-DETALHAR-COM-CUSTOS u=41; P-CONFERIR-NO-HISTORICO u=30; P-ARQUIVAR-HIPOTESE u=0]
t=010 CRENCA AG-RES: explicacao[ebitda_pct]@2026-09 = {"aumento_do_centro": 11171021, "centro": "CC-OPS", ...} (fonte: cálculo sobre AG-CUS (QRY-003) e mcp://erp/historico_resultado)
t=010 HIPOTESE AG-RES: AG-RES-H001 causa_custo_fixo(ebitda_pct) confirmada (custos fixos respondem por 101% da queda do EBITDA contra a média do histórico; maior aumento em CC-OPS)
```

### AG-CUS (`agents/cus_bdi.py`)

| | Conteúdo | O que dispara |
|---|---|---|
| **Crenças** | porte e existência de ERP; receita por unidade; custos fixos; situação do direcionador do período (`ok`, `ausente`, `inconsistente`, com o motivo); critério adotado | tools `normas.cognicao`, `erp.balancete`, `erp.direcionadores`; plano |
| **Desejos** | `definir_rateio` (1), `apurar_custos` (2) | apuração pedida sem critério; critério definido |
| **Permanentes** | precisão, simplicidade | pesos do porte |

| Plano de `definir_rateio` | Atende | Contexto |
|---|---|---|
| P-RATEIO-PADRAO | precisão + simplicidade | direcionador válido, ou ainda não lido (o plano o lê e falha se não servir) |
| P-RATEIO-ULTIMO-VALIDO | precisão + simplicidade | direcionador ausente (tabela alterada não libera a anterior) |
| P-RATEIO-PROPORCIONAL-RECEITA | precisão | todas as unidades com receita no período |
| P-RATEIO-IGUALITARIO | simplicidade | sempre |

Cenário `cus_rateio_alternativo` (percentuais do período somam 110):

```
t=002 DELIBERA AG-CUS: definir_rateio:2026-09|DEL-001 -> P-RATEIO-PADRAO [P-RATEIO-PADRAO u=42; P-RATEIO-ULTIMO-VALIDO x u=41; P-RATEIO-PROPORCIONAL-RECEITA u=31; P-RATEIO-IGUALITARIO u=10]
t=002 CRENCA AG-CUS: direcionador@2026-09 = {"estado": "inconsistente", "motivo": "os percentuais somam 110, não 100", ...} (fonte: mcp://erp/direcionadores)
t=002 INTENCAO AG-CUS: AG-CUS-I001 P-RATEIO-PADRAO falhou (direcionador do período inconsistente: os percentuais somam 110, não 100)
t=002 DELIBERA AG-CUS: definir_rateio:2026-09|DEL-001 -> P-RATEIO-PROPORCIONAL-RECEITA [P-RATEIO-PADRAO x u=42; P-RATEIO-ULTIMO-VALIDO x u=41; P-RATEIO-PROPORCIONAL-RECEITA u=31; P-RATEIO-IGUALITARIO u=10]
```

Na microempresa (simplicidade 3, precisão 1) a segunda deliberação escolhe
P-RATEIO-IGUALITARIO. O critério e o motivo vão para a proveniência, para a decisão
registrada e para uma ressalva do fechamento. O gabarito (`gold["rateio"]`) traz o resultado
por unidade de cada critério; os totais da DRE não mudam.

### AG-REL (`agents/rel_bdi.py`)

| | Conteúdo | O que dispara |
|---|---|---|
| **Crenças** | o que o período teve (parecer, correções, waivers, ressalvas, desvios, insights); público; histórico de correções aprovadas; base normativa de cada exceção | pedido do Orquestrador; tools `normas.cognicao` e `normas.buscar`; SVC-MEM |
| **Desejo** | `comunicar` | relatório pedido |
| **Permanentes** | clareza, completude, concisão | pesos do porte (público) |

| Plano | Atende | Contexto |
|---|---|---|
| P-RELATORIO-DE-EXCECAO | clareza + completude | houve correção aprovada ou waiver no período |
| P-SUMARIO-EXECUTIVO | clareza + concisão | tudo conforme: sem exceção, ressalva, desvio ou insight |
| P-RELATORIO-COMPLETO | completude | sempre (o template da DSM3, na mesma ordem) |

O texto é sempre de template. O relatório de exceção abre pelas exceções, ordena as ressalvas
por destaque, só reproduz insights de hipóteses verificadas e cita a base normativa de cada
exceção. Texto de modelo, quando a flag está ligada, vai ao fim, rotulado.

Cenário `rel_relatorio_de_excecao`:

```
t=018 CRENCA AG-REL: achados@DEL-004 = {"atribuidas": 0, "correcoes": 1, "insights": 0, "notas": 1, ...} (fonte: pedido do AG-ORQ (DEL-004))
t=018 DELIBERA AG-REL: comunicar:DEL-004 -> P-RELATORIO-DE-EXCECAO [P-RELATORIO-DE-EXCECAO u=51; P-SUMARIO-EXECUTIVO x u=50; P-RELATORIO-COMPLETO u=20]
```

Sem exceção (`fechar_mes --cognicao local`) a escolha é P-SUMARIO-EXECUTIVO; com
`--porte grande` é P-RELATORIO-COMPLETO (`P-SUMARIO-EXECUTIVO u=20; P-RELATORIO-COMPLETO u=40`).

### AG-ORC e AG-CIN (o que mudou)

- **AG-ORC** lê as correções aprovadas da memória. Correção de lançamento que inflava a mesma
  conta em competência anterior vira a crença `reincidencia[conta]` (fonte: `SVC-MEM MEM-…`) e
  alimenta a regra `R-MEM-REINCIDENCIA`, que propõe a hipótese de causa de controle ou
  corrobora a que já existe (a confiança sobe). A memória não classifica nada: quem confirma
  é o AG-CIN. Cenário `memoria_reincidencia_orc`.
- **AG-ORC** deixa de gastar consulta nova com hipótese de confiança abaixo de 0,5.
- **AG-CIN** busca na base normativa o trecho que fundamenta cada regra violada.

## Aprendizado local auditável

`services/aprendizado.py` (SVC-APD, NORM-20). Para cada agente e regra local:

    confiança = (inicial × 2 + confirmadas) / (2 + confirmadas + refutadas)

| Regra | Vale | Não vale |
|---|---|---|
| O que conta | hipótese `confirmada` ou `refutada`, com a fonte da evidência | arquivada; evidência sem fonte; fonte `local:` ou `llm:`; origem `llm:` |
| Quando vale | competências anteriores à atual | a própria competência (a ordem dos eventos no mês não muda nada) |
| Quantas vezes | uma por (agente, regra, competência, tipo, alvo) | reprocessar o mês |
| Onde fica | arquivo selado próprio (`--aprendizado ARQUIVO`) ou só na execução | SVC-MEM (só decisão humana, NORM-08) |
| Se o arquivo for alterado | aprendizado desligado, regras na confiança inicial, nada gravado | — |

A confiança não é crença e não classifica desvio. Ela só entra no contexto dos planos
epistêmicos que custam mensagem. Cenário `aprendizado_regra`:

```
t=004 APRENDIZADO AG-ORC: local:R-OBS-REPETICAO refutada em C-3001 Pessoal (0 confirmada(s), 1 refutada(s))
t=053 APRENDIZADO AG-ORC: local:R-OBS-REPETICAO refutada em C-3001 Pessoal (0 confirmada(s), 2 refutada(s))
t=111 DELIBERA AG-ORC: verificar_hipotese:2026-09|C-3001 Pessoal|AG-ORC-H003 -> P-ARQUIVAR-HIPOTESE [P-CONFERIR-EVIDENCIA x u=42; P-VERIFICAR-COM-CIN x u=31; ...]
```

Em setembro a confiança da regra é 0,40 e P-VERIFICAR-COM-CIN não é aplicável ("confiança
0.40 da hipótese abaixo de 0.5"). Com `aprendizado=False` o agente faz a consulta a mais e
chega à mesma classificação. O efeito é de custo, e o risco é declarado: uma regra que errou
duas vezes pode estar certa na terceira; no fechamento o AG-CIN ainda vetaria o lançamento.

## Estratégias de compromisso

`AgenteBDI.compromisso`, por agente (`Scenario.compromisso`, `build_system(compromisso=…)`,
`--compromisso`) e por porte (`models/cognicao.yaml`, hoje `aberto` em todos).

| Estratégia | Larga a intenção quando | Na falha do plano | Registro |
|---|---|---|---|
| `aberto` (padrão) | é atingida, fica impossível **ou o motivo cai** | replaneja | `abandonada`, `reconsiderada` |
| `obstinado` | é atingida ou fica impossível | replaneja | `mantida` |
| `cego` | é atingida | repete o mesmo plano (até 2 vezes; depois replaneja, para a execução terminar) | `insistida`, `mantida` |

Mesma situação nos três cenários (`compromisso_aberto`, `_obstinado`, `_cego`): a consulta ao
AG-CIN se perde; depois o AG-CIN contesta o lançamento e o motivo do alerta cai.

| | Falha da consulta | Motivo do alerta cai | Resultado |
|---|---|---|---|
| aberto | replaneja (P-SEM-EXPLICACAO), depois verifica a hipótese | abandona P-SINALIZAR | conta atribuída a controle (gabarito) |
| obstinado | replaneja | mantém e conclui P-SINALIZAR | falso desvio |
| cego | insiste em P-CONSULTAR-CIN | mantém e conclui P-SINALIZAR | falso desvio, por outro caminho |

```
t=014 INTENCAO AG-ORC: AG-ORC-I002 P-SINALIZAR mantida (compromisso obstinado: o motivo caiu (desvio ajustado R$ 1.815,07 abaixo do limiar após AG-CIN contestar R$ 21.005,86), mas a intenção não foi atingida nem ficou impossível)
t=012 INTENCAO AG-ORC: AG-ORC-I001 P-CONSULTAR-CIN insistida (compromisso cego: repete o mesmo plano após falha (timeout de AG-CIN); insistência 1 de 2)
```

Com falha permanente do AG-CIN, o agente cego faz três consultas, estoura o prazo das duas
tentativas do Orquestrador e a solicitação termina em `failure`; o aberto entrega a avaliação
com ressalva. O teto de insistências é um desvio declarado da definição pura (compromisso cego
nunca desiste), necessário para toda solicitação ter resposta (INV-07).

## Conhecimento normativo com proveniência (CP8)

`models/conhecimento.yaml` (versão `corpus-v1`) e `conhecimento/base.py`. São trechos curtos,
em paráfrase, das normas que o projeto já cita (LC 123/2006, BNDES, Lei 11.638/2007, Lei
6.404/1976, Lei 9.718/1998, ITG 1000, NBC TG 1000, NBC TA 320, COSO 2013 e as normas do
próprio sistema). Não é o texto oficial: cada trecho traz a referência para conferência.

- `buscar(consulta, k)`: BM25 com a biblioteca padrão, offline e determinístico.
- Cada resultado traz `documento`, `trecho`, `texto`, `versao`, `referencia`, `pontuacao`.
- **Sem evidência não se preenche.** Um trecho só conta se cobrir pelo menos metade do peso
  informativo (IDF) dos termos da consulta; termo que o corpus não tem pesa o máximo. Assunto
  fora do corpus devolve lista vazia.
- Tool MCP `normas.buscar`, só na allowlist do AG-CIN e do AG-REL.
- Terminal: `python -m fin_mas normas "segregação de funções" -k 1` (código 1 sem evidência).

| Regra do AG-CIN | Resultado |
|---|---|
| alçada | COSO-2013, trecho COSO-ALCADA |
| SoD | COSO-2013, trecho COSO-SEGREGACAO |
| competência | LEI-6404-1976, trecho LEI-6404-ART177 |
| duplicidade | **sem evidência** (regra interna do porte, sem norma externa citada pelo projeto) |

O achado leva o fundamento na evidência e no campo `fundamento`; sem evidência, leva
`{"situacao": "sem evidência", "corpus": "corpus-v1"}` e continua valendo pela regra interna
(cenários `normas_fundamentam_achado` e `normas_sem_evidencia`).

## O que não foi feito

- Hipóteses por LLM no AG-RES (era opcional): o agente usa só as regras locais.
- Negociação de prazo pelo AG-RES: ele replaneja dentro do prazo que recebeu.
- Compromisso por porte diferente de `aberto` no padrão: fica como fator do experimento.
- O AG-RES só trata piora do EBITDA%; melhora relevante não gera hipótese.
