# Catálogo de cenários de teste

Tudo o que dá para rodar e o que se espera ver, em três interfaces: terminal, console de
administração (TUI) e dashboard. As colunas "esperado" do terminal vêm do campo `esperado` de
cada cenário em `src/fin_mas/env/scenarios.py` (para os 17 cenários revisados, que não têm o
campo, da descrição) e da resposta final conferida por
`python -m fin_mas cenarios --verificar` em 12/11/2026.

## Terminal

### Os 37 cenários

```bash
python -m fin_mas list                               # nome, seed e descrição
python -m fin_mas run --scenario <nome>              # trilha causal legível
python -m fin_mas run --scenario <nome> --trace t.jsonl && python -m fin_mas verificar t.jsonl
python -m fin_mas cenarios --verificar               # todos: resposta, 8 invariantes, repetível (duas execuções)
```

`cenarios --verificar` imprime, por cenário, o nível de cognição, a resposta final, se os oito
invariantes valem e se duas execuções dão o mesmo hash. Resultado: **37 de 37 em ordem**.

**Revisados (DSM2 e primeira versão da DSM3), nível `basico`:**

| Cenário | Resposta | O que observar |
|---|---|---|
| `fechar_mes` | `inform` | fechamento sem inconformidades: caminho feliz |
| `avaliar_orcamento` | `inform` | dois desvios plantados sinalizados |
| `veto_waiver` | `inform` | alçada violada: veto do AG-CIN, waiver humano libera com ressalva |
| `veto_bloqueio` | `failure` | alçada violada sem decisão: o ticket expira e a publicação fica bloqueada |
| `falha_especialista` | `failure` | AG-CUS expira duas vezes: um reenvio e depois `failure` |
| `depuracao` | `inform` | seed 1337, SoD plantado e uma perda de mensagem |
| `veto_correcao` | `inform` | veto, correção aprovada, `erp.corrigir`, AG-CIN reavalia, publicado |
| `correcao_parcial` | `failure` | alçada e SoD: humano corrige só uma, o veto se mantém e o prazo esgota |
| `divergencia_fonte` | `inform` | planilha diverge do ERP: AG-ORC revisa a crença e adota o ERP |
| `desvio_irregular` | `inform` | desvio inflado por NF duplicada: AG-ORC consulta o AG-CIN e reclassifica; estorno destrava |
| `orc_sem_cin` | `inform` | a consulta ao AG-CIN se perde: timeout e replanejamento (desvio sinalizado sem atribuição) |
| `expediente_sma` | `inform`/`refuse` | três competências, pedidos concorrentes; o fechamento concorrente do mesmo mês é recusado (PROT-LCK) |
| `fechamento_micro` | `inform` | micro sem ERP: planilhas, SoD por controle compensatório, alçada do assistente |
| `fechamento_pequena` | `inform` | EPP: duplicidade de NF vetada e estornada |
| `fechamento_grande` | `inform` | grande: materialidade menor; competência errada já é crítica |
| `ataque_decisao_forjada` | `failure` | 14 ataques, 0 aceitos; o ticket expira; nada publicado |
| `reincidencia_waiver` | `inform` | waiver de agosto vira memória; em setembro a POL-06 nega novo waiver e o humano corrige |

**Cognição local (ADR-008):** ver a tabela com mensagens, latência e acerto em {doc}`cognicao`.

| Cenário | Resposta | Esperado |
|---|---|---|
| `orc_hipotese_local` | `inform` | hipótese confirmada pelo AG-CIN (QRY-002); conta atribuída a controle, sem falso desvio |
| `hipotese_refutada` | `inform` | hipótese refutada sem mensagem extra (`P-CONFERIR-EVIDENCIA`); os dois desvios sinalizados |
| `hipotese_arquivada` | `inform` | três consultas perdidas (uma delas com prazo negociado); hipótese arquivada; ressalva de AG-CIN indisponível |
| `negociacao_prazo` | `inform` | `propose` e `accept-proposal` no PROT-DEL; QRY-003 respondida; sem falso desvio; nenhum timeout da subtarefa |
| `negociacao_recusada` | `inform` | `propose` e `reject-proposal` (período reservado); hipótese arquivada; fechamento publicado após a correção |
| `historico_calendario` | `inform` | hipótese `efeito_temporal` confirmada pelo histórico; desvio sinalizado com ressalva de calendário |
| `fechamento_hipotese_local` | `inform` | hipótese confirmada; veto com estorno aprovado; relatório publicado com o insight |

**Decisão por pessoa (ADR-009), nível `basico`, SVC-IAM com contas em memória:**

| Cenário | Resposta | Esperado |
|---|---|---|
| `decisao_por_pessoa` | `inform` | decisão de carla rejeitada (POL-03); ticket aprovado por diego; relatório publicado |
| `solicitante_nao_aprova` | `inform` | decisão de elisa rejeitada (POL-13); ticket aprovado pelo controller |
| `waiver_exige_cargo` | `inform` | waiver de ana rejeitado (POL-02); waiver de diego aceito; publicado com ressalva |
| `micro_controle_compensatorio` | `inform` | decisão aceita com `controle_compensatorio` registrado; fechamento publicado |
| `ataque_acesso` | `failure` | 15 ataques rejeitados (POL-02, 03, 09, 13 e IAM-05, 06); prazo esgota; nada publicado |

**LLM opcional, sempre com mocks ou servidor em loopback:**

| Cenário | Nível | Resposta | Esperado |
|---|---|---|---|
| `orc_hipotese_llm` | `llm` | `inform` | hipótese de origem `llm` confirmada pelo AG-CIN; sem falso desvio |
| `llm_hipotese_rejeitada` | `llm` | `inform` | cinco propostas rejeitadas (NORM-11); resposta igual à da cognição básica |
| `llm_nota_injetada` | `llm` | `inform` | proposta `dentro_do_limiar` rejeitada; os dois desvios seguem sinalizados |
| `llm_json_invalido` | `llm` | `inform` | `llm_fallback` "resposta fora do formato"; a hipótese local segue o caminho normal |
| `llm_provedor_fora` | `llm` | `inform` | duas falhas do provedor, depois disjuntor aberto; as duas avaliações publicadas |
| `llm_sem_consentimento` | `llm` | `inform` | `llm_fallback` NORM-06 "sem consentimento"; nenhum `llm_prompt` registrado |
| `llm_pseudonimos` | `llm` | `inform` | prompt com `FORNECEDOR-A` e sem `F-77`; insight com `F-77`; hipótese confirmada |
| `llm_textos_validados` | `basico` | `inform` | três chamadas de LLM, uma por agente (narrativa, comentário, síntese); nenhum número fora do texto-base |

### Comandos de acesso, auditoria e instalação

Numa pasta de teste (use `FIN_MAS_DIR_CHAVES` apontando para uma pasta temporária para não
misturar com as suas chaves):

| Comando | Resultado esperado |
|---|---|
| `python -m fin_mas run --scenario ataque_decisao_forjada --trace a.jsonl` e `verificar a.jsonl --ancora 2586f2c81fc2cc1c1739c12be744fce07eb2619044a5c337d2c6e1666becc76e` | "ATAQUES 14 de 14 rejeitados"; cadeia íntegra, âncora confere, 12 rejeições auditadas (saída 0) |
| `python -m fin_mas verificar a.jsonl` depois de alterar, remover ou cortar uma linha | adulteração acusada, saída 3 |
| `python -m fin_mas invariantes t.jsonl` | "8 invariantes, 0 violação(ões)"; num trace forjado, a lista das violações (`test_invariant_checker_flags_a_forged_trace`) |
| `python -m fin_mas auditoria t.jsonl --tipo hipotese` (trace de `orc_hipotese_local`) | 3 registros: aceita, em_verificacao, confirmada |
| `python -m fin_mas explicar t.jsonl <seq>` | cadeia percepção → crença → hipótese → desejo → deliberação → intenção → decisão, com o papel de cada registro |
| `python -m fin_mas sequencia t.jsonl SOL-001` | diagrama `sequenceDiagram` Mermaid da conversa e das subconversas |
| `python -m fin_mas acesso --acesso P demo` | 10 contas com papéis, cargo e pessoa do ERP; senha `Demonstracao-SMA-2026` |
| `python -m fin_mas acesso --acesso P papeis` | matriz papel × permissão lida dos modelos |
| `python -m fin_mas acesso --acesso P trilha verificar` | "trilha de acesso íntegra: N registro(s), cadeia e cabeça selada conferem" |
| `python -m fin_mas acesso --acesso P --como operador usuario papeis operador ROLE-OPE ROLE-APR` | recusado com IAM-05 |
| `python -m fin_mas instalar --demo --pasta P` e `doctor --pasta P` | pasta pronta; "0 erro(s)" e um aviso por chave de LLM ausente |
| `python -m fin_mas serve --demo` | escritório em `http://127.0.0.1:8765` com as contas de demonstração |
| `python -m fin_mas llm provedores` | os cinco provedores e, para cada um, se a chave está no ambiente (nunca o valor) |
| `python -m fin_mas llm avaliar` | bancada com o mock: 6 casos, "acertos: 6 de 6", 0 fallbacks |
| `python -m fin_mas run --scenario fechar_mes --llm mock-alucina` | síntese com número alterado descartada; relatório só com o template |

## Console de administração (TUI)

`tests/tui/test_tui_acesso.py` dirige a TUI real pelo `Pilot` do Textual (teclas e cliques
pelos ids estáveis de `tui/app.py` e `tui/telas.py`), sobre um cadastro selado em pasta
temporária; quando o roteiro precisa do "lado do servidor" (sessões abertas pela web, contas alteradas em outro
processo), usa uma segunda instância do SVC-IAM sobre o mesmo cadastro. 20 roteiros:

| # | Roteiro | Regra |
|---|---|---|
| 1 | primeiro uso: o assistente cria o primeiro administrador | IAM-01 |
| 2 | senha errada mostra o erro e não entra | IAM-03 |
| 3 | conta sem permissão de administração nem de auditoria é recusada na entrada | IAM-05 |
| 4 | cadastro comprometido não deixa ninguém entrar | IAM-07 |
| 5 | login do administrador abre o console; sair encerra a sessão | — |
| 6 | matriz de papéis e quadro de combinações incompatíveis | IAM-06, POL-13 (aviso) |
| 7 | criar conta pelo formulário (senha fraca mantém o formulário aberto) | IAM-02 |
| 8 | dar o papel de aprovador ao administrador é recusado com IAM-06 | IAM-06 |
| 9 | trocar papéis e vínculo (pessoa do ERP, cargo) de uma conta | — |
| 10 | bloquear uma conta derruba a sessão e o login dela | IAM-04 |
| 11 | o último administrador não pode ser bloqueado | IAM-06 |
| 12 | redefinir senha dá uma temporária e derruba as sessões | IAM-02, IAM-04 |
| 13 | senha temporária precisa ser trocada antes de usar o console | IAM-02 |
| 14 | revogar uma sessão aberta pelo servidor a derruba | IAM-04 |
| 15 | o console volta à entrada quando a própria sessão é revogada | IAM-04 |
| 16 | o console acompanha mudanças de papéis feitas em outro lugar | IAM-05 |
| 17 | trilha: filtros, exportação, integridade e adulteração | NORM-13 |
| 18 | o auditor vê a trilha e não administra | IAM-05 |
| 19 | abrir um trace gravado, filtrar, explicar e exportar | — |
| 20 | trace adulterado ou ausente mostra o erro | — |

```bash
python -m pytest tests/tui                  # exige o extra `tui` (textual)
```

## Dashboard (Playwright no Chrome)

29 roteiros de uso real em `web/e2e/`, com o servidor Python de verdade e as contas de
demonstração (`web/e2e/preparar.ts`, `web/e2e/apoio.ts`).

`escritorio.spec.ts` (14):

1. primeira visita mostra o guia e o escritório com códigos e departamentos
2. operador pausa, avança evento a evento e retoma
3. veto vira notificação; o humano corrige no ERP e o AG-CIN reconsidera
4. waiver exige justificativa e libera com ressalva
5. desligar o AG-CIN gera perdas, timeout, replanejamento do AG-ORC e falha explícita
6. badges mostram novidades não vistas e somem ao abrir o agente
7. novo pedido pelo diálogo entra na fila e é atendido
8. replay offline e comparação com o workflow centralizado
9. tema escuro alterna e é lembrado
10. períodos e fontes de dados são clicáveis e mostram o que aconteceu
11. trocar o porte para micro muda regras, fonte (sem ERP) e chip da empresa
12. empresa sem ERP: baixa o modelo, envia a planilha e o escritório roda sobre ela
13. planilha inválida é recusada com a lista de erros
14. liga e desliga pelo chip do agente e faz novo pedido pelo painel do Solicitante

`acesso.spec.ts` (9):

1. sem sessão o escritório pede login e a API não entrega nada
2. senha errada mostra erro genérico e cinco erros bloqueiam a conta
3. operador opera a simulação, mas não pede nem decide
4. auditor só lê: consulta e exporta os logs, não opera nem configura
5. a decisão é da pessoa: a gerente envolvida é impedida e outro gerente decide
6. sessão revogada pelo administrador no terminal devolve o dashboard ao login
7. senha temporária precisa ser trocada na primeira entrada
8. sair encerra a sessão no servidor
9. o que a pessoa pede fica no nome dela

`areas.spec.ts` (6):

1. solicitações: pedir, acompanhar e abrir o relatório para baixar
2. aprovações: fila com prazo, decisão com justificativa e histórico com a pessoa
3. logs: filtros por agente e tipo, busca, por quê e sequência da conversa
4. porte: ficha com as regras de cada porte e o porte em uso
5. cognição local pelo dashboard: a hipótese aparece na mente do agente e é confirmada
6. LLM opcional pelo dashboard: ligar o mock no AG-ORC, corroborar a hipótese e ver o custo

## Como rodar tudo

```bash
python -m pytest                              # 431 testes: unit 95, e2e 254, integration 62, tui 20
python tools/trace.py --check                 # rastreabilidade: 0 erros
python -m fin_mas cenarios --verificar        # 37 de 37 cenários em ordem
cd web && bun run test && bun run test:e2e    # vitest (12) e Playwright (29)
```

O comando único também roda a parte Python e a de interface: `./iniciar.sh testes` (ou
`.\iniciar.ps1 testes`). Os testes de uso real usam o Chrome instalado
(`channel: chrome`); sem ele, `PW_CHANNEL=chromium` usa o Chromium do Playwright, como no CI.
