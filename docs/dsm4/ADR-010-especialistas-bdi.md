---
orphan: true
---

# ADR-010 — Todos os especialistas BDI, com as variantes reativas como braço de comparação

- **Status:** aceita (DSM4, 13/11/2026)
- **Requisitos:** {need}`REQ-F20`, {need}`REQ-F21`, {need}`REQ-F07`, {need}`REQ-F08`
- **Normas:** {need}`NORM-07`, {need}`NORM-08`, {need}`NORM-11`, {need}`NORM-20`, {need}`NORM-21`
- **Estende:** ADR-008 (cognição local e LLM opcional). Não substitui nenhuma decisão anterior.

## Contexto

Até a DSM3 só dois agentes deliberavam: o AG-ORC (o que é desvio, a quem perguntar) e o AG-CIN
(aprovar, apontar, vetar). AG-RES, AG-CUS e AG-REL eram reativos: recebiam o pedido, aplicavam
a fórmula ou o template e respondiam. Para a entrega final foi pedido que **todos** os
especialistas fossem BDI.

## O alerta da apostila

A apostila da disciplina adverte contra a agentificação excessiva: dar cognição a quem só
aplica uma fórmula. O critério que adotamos a partir desse alerta: um agente merece crenças,
desejos e intenções quando escolhe entre alternativas sob incerteza, quando o mundo muda
enquanto ele age, ou quando depende de outros que podem falhar. Fora disso, a cognição só
deixa o sistema mais caro e mais difícil de auditar.

O alerta se aplica aqui de forma desigual:

| Agente | O que há para decidir | Onde o alerta pesa |
|---|---|---|
| AG-RES | depende de dois outros agentes que podem não responder, tem prazo, e pode ou não explicar uma variação | pouco: há incerteza, tempo e dependência |
| AG-CUS | qual critério de rateio usar quando o direcionador do período não serve | médio: a escolha existe, mas não envolve tempo nem outros agentes |
| AG-REL | como comunicar (estrutura, ordem, o que incluir) conforme os achados e o leitor | muito: recebe tudo pronto e nenhum plano falha por causa do ambiente |

## Decisão

1. **Variantes, não substituição.** `AgenteResultadosBDI`, `AgenteCustosBDI` e
   `AgenteRelatoriosBDI` são classes novas (`agents/res_bdi.py`, `cus_bdi.py`, `rel_bdi.py`).
   `build_system` instancia as variantes nos níveis de cognição `local` e `llm`; em `basico`
   instancia as classes reativas de sempre, sem nenhuma alteração. Os cenários revisados da
   DSM3 ficam em `basico` e seus traces não mudam (guarda de hash sobre as 140 execuções da
   comparação). As classes reativas passam a ser o **braço `basico` do experimento**.

2. **Deliberação que se vê no trace.** Cada variante tem crenças com fonte, desejos gerados
   das crenças, mais de um plano por desejo com contexto e utilidade, e ao menos um ponto em
   que a escolha muda com as crenças ou com o porte. A utilidade continua sendo a soma dos
   pesos dos desejos permanentes que o plano atende; os pesos por porte ficam em
   `models/cognicao.yaml` e chegam ao agente pela tool `normas.cognicao`. O detalhe por
   agente está em {doc}`cognicao`.

3. **LLM só onde já era permitido, e sempre fora das frases do agente.** AG-CUS, AG-CIN e
   AG-ORQ seguem sem LLM (NORM-07). Nas variantes BDI o texto de modelo (comentário do
   AG-RES, narrativa do AG-ORC, síntese do AG-REL) vai ao fim do relatório, rotulado como
   texto de modelo; as frases de insight são montadas por template do agente, com números das
   crenças. Hipóteses por LLM continuam só no AG-ORC.

4. **Aprendizado local em registro próprio.** Cada regra local de hipótese acumula
   confirmações e refutações de evidência verificada, e a confiança da regra nas competências
   seguintes vem dessa contagem (`services/aprendizado.py`, NORM-20). O registro **não** fica
   no SVC-MEM: a memória só aceita decisão aprovada por humano (NORM-08), e estatística de
   regra não é decisão de ninguém. Abrir essa exceção enfraqueceria a regra que permite ao
   AG-CIN negar um segundo waiver com base na memória. O registro usa o arquivo selado do
   SVC-IAM (`services/selado.py`), com falha fechada, e sem caminho vive só na execução.

5. **Compromisso como parâmetro.** `AgenteBDI.compromisso` aceita `cego`, `obstinado` e
   `aberto` (Rao & Georgeff, 1991). `aberto` é o padrão em todos os portes e reproduz o
   comportamento anterior byte a byte. As outras duas existem como fator do experimento.

6. **Memória aprovada lida por tipo.** AG-ORC, AG-RES e AG-REL passam a ler correções
   aprovadas; waiver e bloqueio continuam só com o AG-CIN. Só o AG-CIN grava.

7. **Conhecimento normativo com proveniência (CP8).** Base versionada em
   `models/conhecimento.yaml`, busca lexical offline, tool `normas.buscar`. Sem evidência a
   busca devolve vazio e o agente declara "sem evidência" (NORM-21).

## Hipótese a testar no experimento

> **H-BDI.** Com as mesmas seeds e os mesmos plantios, o braço `local` (especialistas BDI)
> entrega resultado igual ao do braço `basico` nas condições nominais e melhor sob falha de
> especialista ou dado inutilizável, ao custo de mais mensagens, mais chamadas de tool e mais
> registros de trace.

O que se espera observar, por agente, e o que derruba a hipótese:

| Agente | Onde o `local` deve ganhar | Onde deve empatar | O que refuta |
|---|---|---|---|
| AG-RES | fechamento publicado com ressalva quando o AG-ORC não responde (o `basico` aborta); variação explicada com o centro de custo | DRE e KPIs nas condições nominais | mesma taxa de publicação sob falha, ou explicação que não bate com o gabarito plantado |
| AG-CUS | direcionador inutilizável percebido e declarado (o `basico` aplica o rateio fixo em silêncio) | margens e DRE sempre; resultado por unidade sem plantio | nenhuma diferença mensurável além de registros a mais |
| AG-REL | nenhum ganho de corretude esperado; só forma (exceção antes dos indicadores) | todos os números do relatório | — (a diferença é qualitativa; ver abaixo) |

A hipótese pode ser refutada em parte, e o desenho admite isso: se o AG-CUS e o AG-REL não
mostrarem ganho mensurável, o resultado honesto do experimento é que a cognição se justificou
no AG-RES e não nos outros dois. As métricas para isso são a MET-30 (deliberação efetiva) e
as de qualidade já existentes, comparadas entre os dois braços.

## Onde a cognição pesa pouco (declarado)

- **AG-REL.** A escolha entre três estruturas é guardada por contexto e nenhum plano falha:
  uma tabela de decisão faria o mesmo. O que o BDI acrescenta é a escolha registrada com os
  motivos e os pesos do porte, não capacidade nova.
- **AG-CUS.** A deliberação é real (o plano padrão falha ao perceber o dado e há alternativas
  cuja ordem muda com o porte), mas é uma cadeia curta e síncrona. O ganho é transparência:
  o agente reativo aplica 60/40 sem saber que a tabela do período estava errada. O desenho
  inicial previa precisão contra tempestividade; como todos os critérios se calculam no mesmo
  instante, o segundo desejo do AG-CUS é simplicidade, que é o custo que de fato existe.
- **Compromisso no AG-CIN.** A intenção de vetar é reavaliada por eventos do protocolo
  (correção, waiver), não pelo filtro genérico; nos cenários atuais as três estratégias dão o
  mesmo resultado nesse agente.

## Alternativas rejeitadas

- **Trocar as classes reativas pelas BDI.** Quebraria os traces revisados da DSM3 e tiraria
  do experimento o único braço de comparação com as mesmas funções.
- **Um `if cognicao` dentro das classes atuais.** Mistura dois comportamentos numa classe e
  torna a garantia "em `basico` nada muda" dependente de disciplina, não de estrutura.
- **Guardar o aprendizado no SVC-MEM.** Exigiria afrouxar a NORM-08 (ver decisão 4).
- **Deixar o LLM propor critério de rateio ou estrutura de relatório.** O AG-CUS não pode usar
  LLM (NORM-07), e a estrutura do relatório é decidível por regra; um modelo ali só
  acrescentaria custo e não determinismo.
- **Citação normativa por similaridade semântica (embeddings).** Dependência nova e
  resultado menos explicável; a busca lexical com limiar de cobertura devolve vazio quando o
  corpus não trata do assunto, que é o comportamento exigido pelo CP8.
- **Compromisso por porte diferente de `aberto` no padrão.** Mudaria o comportamento de
  cenários existentes sem evidência de que é melhor; fica como fator do experimento.

## Consequências

- O trace dos níveis `local` e `llm` cresce (crenças, desejos, deliberações e intenções de
  mais três agentes; registros `aprendizado`); os traces exportados para o replay do
  dashboard precisam ser gerados de novo para esses níveis.
- Tools novas de leitura no gateway: `normas.cognicao`, `normas.buscar`,
  `erp.direcionadores`, `erp.historico_resultado`, cada uma só na allowlist de quem a usa.
- `Fault` ganhou o campo opcional `competencia`, para perder mensagens de um mês específico.
- Plantios novos, aditivos: `direcionador_ausente`, `direcionador_inconsistente`,
  `variacao_custo_fixo`.
