# Cognição assistida: hipóteses verificáveis

Implementa o {need}`REQ-F08` e a {need}`NORM-11` (decisão em
{doc}`ADR-008-cognicao-local-e-llm`). O AG-ORC, que já era BDI na DSM2, passa a receber
**propostas** de hipótese sobre a causa de cada desvio. Uma proposta não é crença: ela é
validada por regras, vira hipótese num repositório separado e só gera uma **ação epistêmica**
(buscar a evidência). Quem muda a avaliação é a crença revisada pela evidência, pelos planos de
sempre.

```{mermaid}
flowchart LR
  P[proposta<br/>regra local ou LLM] --> V{validação<br/>5 regras}
  V -- recusa --> R[hipotese: rejeitada<br/>motivo no trace]
  V -- aceita --> H[hipótese<br/>estado: proposta]
  H --> D[desejo epistêmico<br/>verificar_hipotese]
  D --> A[ação epistêmica<br/>plano escolhido]
  A --> E[evidência de fonte<br/>determinística]
  E --> C[crença revisada]
  C --> F[confirmada / refutada]
  A -- sem evidência --> X[arquivada<br/>nada muda]
```

Código: `src/fin_mas/core/inferencia.py` (proposta, validação, estados), `src/fin_mas/cognicao/regras.py`
(motor local), `src/fin_mas/cognicao/llm.py` (proponente LLM, via SVC-MOD),
`src/fin_mas/core/bdi.py` (`_inferir`, `hipoteses`) e `src/fin_mas/agents/orc.py` (desejo
`verificar_hipotese` e os cinco planos).

## Onde entra no ciclo BDI

`AgenteBDI.ciclo()` chama `_inferir()` antes de gerar opções. Sem proponentes (nível `basico`),
`_inferir` retorna sem fazer nada e nenhum registro novo aparece no trace. Com proponentes, o
agente pede propostas uma única vez por gatilho (no AG-ORC: `desvios@<competência>`, quando
todas as fontes estão reconciliadas e há conta acima do limiar). Antes de pedir, ele percebe
duas fontes novas, ambas registradas como crença com a fonte MCP:

| Tool | O que traz | Crença |
|---|---|---|
| `planilhas.observacoes` | texto livre que quem preencheu a planilha deixou em cada conta | `observacao[conta]@competência` |
| `erp.historico` | série mensal (orçado e realizado) da conta; indisponível em empresa sem ERP | `historico[conta]@competência` |

## As cinco regras de validação

Cada regra recusa a proposta inteira; o motivo vai para um registro `hipotese` com
`evento: rejeitada` e `regra: NORM-11`.

| # | Regra | O que impede |
|---|---|---|
| 1 | o tipo está na lista fechada do agente e o alvo é uma conta da tarefa | hipótese sobre algo que não está em avaliação |
| 2 | toda evidência citada é uma crença que o agente tem (e há pelo menos uma) | evidência inventada pelo proponente |
| 3 | o texto não traz dígitos; valores entram por marcadores `{chave}` que o agente resolve com as próprias crenças | número inventado ou valor verdadeiro com a grandeza trocada |
| 4 | o texto não propõe ação (aprovar, estornar, lançar, liberar, bloquear, pagar, classificar…) | hipótese que tenta decidir; quem decide é a política |
| 5 | todo marcador aponta para uma evidência citada ou para `{alvo}` | marcador que puxaria uma crença não citada |

Além disso: confiança entre 0 e 1, justificativa com até 600 caracteres e chaves balanceadas.
A resposta de um LLM ainda precisa ser JSON estrito `{"propostas": [...]}` com os campos
`tipo`, `alvo`, `justificativa`, `evidencias`, `confianca`; fora disso, o SVC-MOD registra
`llm_fallback` e nenhuma proposta é lida. Proposta repetida (mesmo tipo, alvo e competência)
de outra origem não cria outra hipótese: a existente é **corroborada** e ganha a origem.

## Tipos de hipótese e como cada um é verificado

| Tipo | Significado | Regra local que propõe | Evidência que decide |
|---|---|---|---|
| `causa_controle` | o desvio vem de lançamento irregular (problema de controle interno, não de orçamento) | `R-OBS-REPETICAO`: a observação fala em duplicidade, lançamento repetido, "em dobro" | resposta do AG-CIN (PROT-QRY): valor contestado > 0 confirma; 0 refuta |
| `efeito_temporal` | o desvio é efeito de calendário: gasto que se repete na mesma época e se compensa no trimestre | `R-OBS-RECORRENCIA` (texto fala em sazonalidade, "todo início de trimestre"…) e `R-HIST-PICO` (o mesmo mês do trimestre anterior também passou do limiar) | cálculo sobre o histórico (`padrao_de_calendario`): em **todos** os trimestres completos, com pelo menos 2, o acumulado até este mês passou do limiar e o trimestre fechou dentro dele |

A regra local só propõe. Em `historico_calendario`, por exemplo, quem confirma é o cálculo
sobre todos os trimestres, e o teste `test_calendar_hypothesis_is_refuted_when_history_does_not_repeat`
mostra a mesma observação refutada quando o histórico não repete o padrão.

## Os planos do desejo epistêmico

O desejo `verificar_hipotese(conta)` (prioridade 2) nasce de cada hipótese ainda em `proposta`.
Para `causa_controle`, ele só nasce depois que a consulta normal ao AG-CIN respondeu ou
falhou. Enquanto ele está ativo, a intenção de alertar o desvio fica suspensa: o AG-ORC só
sinaliza depois de verificar.

| Plano | Contexto (quando é aplicável) | O que faz | Custo |
|---|---|---|---|
| `P-CONFERIR-EVIDENCIA` | `causa_controle` e o AG-CIN já respondeu sobre a conta | confere a resposta que já existe | nenhuma mensagem |
| `P-VERIFICAR-COM-CIN` | `causa_controle`, a consulta normal falhou, o AG-CIN está no diretório, cabe no prazo do solicitante (consulta de 10 ticks + folga de 5) e no teto de 3 verificações por tarefa | nova `query-ref` ao AG-CIN (PROT-QRY) | +2 mensagens |
| `P-NEGOCIAR-PRAZO` | igual ao anterior, mas a consulta **não** cabe no prazo; só uma negociação por tarefa e só com o Orquestrador como solicitante | `propose` ao Orquestrador (PROT-DEL); aceito, consulta o AG-CIN; recusado, o plano falha | +2 mensagens da negociação, +2 da consulta |
| `P-VERIFICAR-NO-HISTORICO` | `efeito_temporal` e há histórico da conta | calcula o padrão de calendário | nenhuma mensagem |
| `P-ARQUIVAR-HIPOTESE` | sempre (fallback) | arquiva: nada muda na avaliação | nenhuma mensagem |

A escolha entre planos aplicáveis segue a utilidade da DSM2 (pesos dos desejos do porte +
preferência). Confirmada ou refutada, a hipótese registra a **fonte** da evidência
(`AG-CIN (QRY-002)`, `cálculo sobre mcp://erp/historico`); o insight que vai para o relatório
cita a origem e a evidência e tem os números resolvidos pelas crenças do agente.

## Níveis de cognição

| Nível | Proponentes no AG-ORC | Onde é o padrão |
|---|---|---|
| `basico` | nenhum: o ciclo BDI da DSM2/DSM3 revisada | os 17 cenários revisados, os 5 de acesso por pessoa e `llm_textos_validados` |
| `local` | regras locais (`ProponenteLocal`), offline e sem custo | cenários cognitivos novos; `fin-mas instalar` sugere `local` |
| `llm` | regras locais + LLM opcional (`ProponenteLLM`), que só chama o modelo se a flag e o uso `hipoteses` do AG-ORC estiverem ligados no SVC-MOD | cenários `orc_hipotese_llm` e `llm_*` (sempre com mocks ou servidor em loopback) |

```bash
python -m fin_mas run --scenario orc_sem_cin --cognicao local      # cenário revisado no nível local
python -m fin_mas serve --demo --cognicao local                    # dashboard ao vivo com hipóteses
```

O nível também muda pelo dashboard (aba *Agentes e LLM*, comando `reiniciar` com `cognicao`,
exige `PERM-SIM-OPERAR`). Só o AG-ORC tem proponentes nesta entrega
({doc}`limitacoes`).

## Cenários cognitivos e resultado esperado

Resultado medido rodando cada cenário no nível dele e de novo com `--cognicao basico`
(`metricas.medir` e `metricas.medir_cognicao`, seed 42). "Mensagens" são registros `open` e
`send` de protocolo na solicitação; latência em ticks lógicos.

| Cenário | Esperado (campo `esperado`) | Hipóteses | Mensagens básico → nível | Latência básico → nível | Acerto (desvios corretos / falsos) básico → nível |
|---|---|---|---|---|---|
| `orc_hipotese_local` | hipótese confirmada pelo AG-CIN (QRY-002); conta atribuída a controle, sem falso desvio | 1 confirmada | 10 → 12 | 19 → 21 | 0/1 → 1/0 |
| `hipotese_refutada` | refutada sem mensagem extra (`P-CONFERIR-EVIDENCIA`); os dois desvios sinalizados | 1 refutada | 13 → 13 | 11 → 11 | 1/0 → 1/0 |
| `hipotese_arquivada` | três consultas perdidas (uma com prazo negociado); arquivada; ressalva de AG-CIN indisponível | 1 arquivada | 10 → 14 | 19 → 41 | 0/1 → 0/1 |
| `negociacao_prazo` | `propose` e `accept-proposal` no PROT-DEL; QRY-003 respondida; sem falso desvio | 1 confirmada | 10 → 15 | 19 → 33 | 0/1 → 1/0 |
| `negociacao_recusada` | `propose` e `reject-proposal` (período reservado); arquivada; publicado após a correção | 1 arquivada | 26 → 29 | 31 → 43 | 0/1 → 0/1 |
| `historico_calendario` | `efeito_temporal` confirmada pelo histórico; desvio sinalizado com ressalva de calendário | 1 confirmada | 11 → 11 | 11 → 11 | 1/0 → 1/0 |
| `fechamento_hipotese_local` | confirmada; veto com estorno aprovado; relatório publicado com o insight | 1 confirmada | 26 → 28 | 31 → 33 | 0/1 → 1/0 |
| `orc_hipotese_llm` | hipótese de origem `llm` confirmada pelo AG-CIN; sem falso desvio | 1 confirmada | 10 → 12 | 19 → 21 | 0/1 → 1/0 |
| `llm_hipotese_rejeitada` | cinco propostas rejeitadas (NORM-11); resposta igual à da cognição básica | 0 (5 rejeitadas) | 10 → 10 | 19 → 19 | 0/1 → 0/1 |
| `llm_nota_injetada` | proposta `dentro_do_limiar` rejeitada; os dois desvios seguem sinalizados | 0 (1 rejeitada) | 13 → 13 | 11 → 11 | 1/0 → 1/0 |
| `llm_json_invalido` | `llm_fallback` "resposta fora do formato"; a hipótese local segue o caminho normal | 1 confirmada (local) | 11 → 11 | 11 → 11 | 1/0 → 1/0 |
| `llm_provedor_fora` | duas falhas, depois disjuntor aberto; as duas avaliações publicadas | 0 | 13 → 13 | 11 → 11 | 1/0 → 1/0 |
| `llm_sem_consentimento` | `llm_fallback` NORM-06 "sem consentimento"; nenhum `llm_prompt` | 1 confirmada (local) | 11 → 11 | 11 → 11 | 1/0 → 1/0 |
| `llm_pseudonimos` | prompt com `FORNECEDOR-A` e sem `F-77`; insight com `F-77`; confirmada | 1 confirmada | 10 → 12 | 19 → 21 | 0/1 → 1/0 |

Leitura: quando a hipótese encontra evidência, o acerto melhora (o desvio inflado por NF
duplicada deixa de ser falso desvio) ao custo de 2 mensagens e 2 ticks, ou de 5 mensagens e
14 ticks quando é preciso negociar prazo. Quando não há evidência, a hipótese é arquivada, o
resultado é o do nível básico e o custo fica registrado (`hipotese_arquivada`: +4 mensagens,
+22 ticks). Propostas inválidas não mudam nada.

```bash
python -m fin_mas run --scenario orc_hipotese_local      # HIPOTESE aceita -> em_verificacao -> confirmada
python -m fin_mas run --scenario negociacao_prazo        # propose / accept-proposal no PROT-DEL
python -m fin_mas cenarios --filtro hipotese              # tabela de conferência só destes
```

## O que garante que o nível básico não mudou

1. **Código:** sem proponentes, `_inferir` retorna antes de qualquer efeito; as tools novas só
   são chamadas dentro do gatilho de inferência; os desejos e planos novos dependem de
   hipóteses, que não existem no nível básico.
2. **Teste:** `test_basic_cognition_has_no_hypotheses_and_no_extra_perception` roda cada
   cenário do nível básico e confere que não há registro `hipotese`, nem chamada às tools novas,
   nem `cognicao` no registro `meta`, nem `hipoteses`/`insights` na resposta.
3. **Reprodutibilidade:** `test_offline_seeded_reproducibility` roda cada um dos 37 cenários
   duas vezes e compara o hash do trace; `python -m fin_mas cenarios --verificar` faz o mesmo
   pela linha de comando (37 de 37 em ordem).
4. **Guarda contra a referência gravada:** os 140 pares (cenário revisado, seed) de
   `docs/dsm3/resultados/comparacao.csv` produzem o mesmo hash de trace da referência v0.5.0
   (0 diferentes na execução de 12/11/2026). Em relação à tag `dsm3-base`, as 20 colunas de
   métricas desse CSV são idênticas; os hashes mudaram porque o registro `meta` do trace leva
   a versão do pacote (0.4.0 → 0.5.0). Conferido registro a registro em `fechar_mes`: é o
   único registro diferente, além do selo final.

## MET-18: disciplina das hipóteses

{need}`MET-18` é lida do trace por `metricas.medir_cognicao`: propostas, rejeitadas,
hipóteses, confirmadas, refutadas, arquivadas, **crenças com um proponente como fonte**,
consultas de verificação, negociações de prazo, chamadas e fallbacks de LLM.

| Indicador | Resultado nos 37 cenários |
|---|---|
| crenças com fonte `local:` ou `llm:` | **0** (alvo: 0); também o invariante INV-05 e o teste `test_hypothesis_never_writes_a_belief` |
| hipóteses confirmadas / refutadas / arquivadas (cenários cognitivos) | 8 / 1 / 2 |
| propostas rejeitadas | 6 (5 em `llm_hipotese_rejeitada`, 1 em `llm_nota_injetada`) |
| custo da ação epistêmica | ver a tabela acima: 0 a 5 mensagens a mais por solicitação |

Testes: `tests/e2e/test_cognicao_local.py` (45 casos, contando os parametrizados) e
`tests/e2e/test_cognicao_llm.py` (19), descritos em {doc}`testes`.
