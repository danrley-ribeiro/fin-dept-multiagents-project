# Testes e evidências

```bash
python -m pytest                       # 437 testes, offline (249 na tag dsm3-base; 157 na DSM2)
python tools/trace.py --check          # rastreabilidade: 0 erros; 153 de 156 testes modelados executados
python -m fin_mas cenarios --verificar # 37 de 37 cenários: resposta explícita, 8 invariantes, repetível
cd web && bun run test && bun run test:e2e   # vitest (12) e Playwright no Chrome (30 roteiros)
```

Contagem pela coleta do pytest (13/11/2026, `python -m pytest --co`):

| Pasta | Testes | Na tag `dsm3-base` |
|---|---|---|
| `tests/unit/` | 95 | 95 |
| `tests/e2e/` | 260 | 141 |
| `tests/integration/` | 62 | 13 |
| `tests/tui/` | 20 | — |
| **Total** | **437** | **249** |

A execução completa (`python -m pytest`) terminou com os 437 passando e código de saída 0. O
catálogo de todos os cenários e roteiros, com o resultado esperado de cada um, está em
{doc}`cenarios-de-teste`.

## Política desta etapa: sem unitários novos

Os testes novos da v0.5.0 são **e2e** (cenários completos, verificados pelo trace),
**integração** (servidor HTTP real, CLI em subprocesso, provedores de LLM contra servidor falso
em loopback, arquivos selados em pasta temporária) e **interface** (TUI pelo `Pilot` do Textual,
dashboard pelo Playwright no Chrome). Nenhum teste unitário novo: a pasta `tests/unit/` tem os
mesmos 95 da tag `dsm3-base`. O motivo é o mesmo da DSM2 revisada: o que importa é o
comportamento observável do sistema (mensagens, decisões, trace, respostas HTTP, telas), não a
função isolada.

## Novos na v0.5.0 (188 a mais que na tag `dsm3-base`)

| Arquivo | Testes | O que cobre |
|---|---|---|
| `tests/e2e/test_cognicao_local.py` | 45 | hipótese local leva a nova consulta e reclassifica; proposta nunca grava crença (em todos os cenários); alarme falso refutado sem mensagem extra; arquivada sem evidência não muda nada; padrão de calendário confirmado e refutado pelo histórico; fechamento completo com correção aprovada; ação epistêmica respeita o prazo do solicitante; nível básico sem hipóteses e sem as tools novas (por cenário); `--cognicao local` pela CLI |
| `tests/e2e/test_cognicao_llm.py` | 19 | hipótese do LLM verificada antes de mudar o resultado; propostas rejeitadas deixam o resultado idêntico; nota injetada não muda a classificação; JSON inválido cai no fallback; disjuntor; sem consentimento nada sai; pseudônimos; textos opcionais validados por agente; narrativa alucinada descartada; número verdadeiro sob o rótulo errado recusado; reprodutibilidade com mock; LLM proibido em ORQ, CUS e CIN |
| `tests/e2e/test_decisao_por_pessoa.py` | 11 | POL-03 contra a pessoa real; POL-13; POL-02 pelo cargo; controle compensatório na micro; os 15 ataques de `ataque_acesso`; cenários com pessoa reproduzíveis e toda decisão com pessoa; sem SVC-IAM, regras por identidade como antes |
| `tests/e2e/test_negociacao_prazo.py` | 8 | Orquestrador aceita a extensão; recusa com período reservado; prazo estendido substitui o temporizador antigo; regras das propostas; uma extensão por subtarefa; negociação fora de ordem ou pelo papel errado recusada |
| `tests/e2e/test_reprodutibilidade.py` (casos novos) | 20 | mesmo hash em duas execuções para cada um dos 20 cenários novos (parametrizado por cenário) |
| `tests/e2e/test_approval_gate.py` (caso novo) | 1 | prazo do ticket conferido pelo instante real de entrega da decisão (TEST-134) |
| `tests/integration/test_dashboard_acesso.py` | 14 | servidor real: fluxo de eventos, token CSRF, autenticação antes do corpo (3 casos que estavam em `test_dashboard_live.py`, agora com sessão), filtros, permissões por papel, decisão ligada à pessoa logada, pedido com a pessoa e solicitante que não aprova, revogação imediata com SSE fechado, bloqueio de login e erro genérico, senha temporária, rotas das áreas de trabalho, configuração de LLM com permissão, cabeçalhos de segurança e cookie, cadastro adulterado |
| `tests/integration/test_provedores_llm.py` | 16 | `openai-compat`, `openai`, `gemini` e `anthropic` contra servidor falso em loopback: formato do pedido, uso de tokens, chave só no cabeçalho; falhas e tempo limite caem no fallback; chave ausente sem pedido; CLI com servidor local, recusas da CLI, bancada e lista de provedores sem revelar chaves |
| `tests/integration/test_acesso_cli.py` | 10 | ciclo de vida de contas pelo terminal; trilha listada, verificada e adulteração detectada; rollback do cadastro recusado; escritores concorrentes não perdem atualizações; matriz dos modelos; `auditoria`, `explicar`, `sequencia` e `invariantes` sobre trace gravado; trace forjado acusado; catálogo de cenários; `verificar --ancora` em trace sem cadeia devolve 3; ator revogado ou rebaixado não continua administrando |
| `tests/integration/test_implantacao.py` | 4 | `instalar` e `doctor`; `doctor` acusa instalação adulterada; servidor sobe da pasta instalada com o porte escolhido; servidor não sobe sem contas |
| `tests/tui/test_tui_acesso.py` | 20 | console de administração e auditoria pela TUI real (roteiros em {doc}`cenarios-de-teste`) |
| `tests/integration/test_dashboard_live.py` | −3 | os 3 casos movidos para `test_dashboard_acesso.py` |

No dashboard: `web/e2e/acesso.spec.ts` (9 roteiros) e `web/e2e/areas.spec.ts` (6) são novos;
`web/e2e/escritorio.spec.ts` (14) passou a entrar com uma conta de demonstração. Total: 29
roteiros de uso real, mais 12 testes vitest (reducer e regra da justificativa).

Rastreabilidade: TEST-19 (dashboard autenticado com filtros, especificado na DSM1) passou a
`executado`; TEST-91 a TEST-156 são novos, todos `executado`, cada um ligado a uma função pytest
ou a um roteiro do Playwright ou da TUI que `tools/trace.py` confere.

## Novos na primeira versão da DSM3 (histórico)

Registro de 10–12/11/2026, antes da v0.5.0: de 157 (DSM2) para 249 testes. A entrega inicial
somou 75 (232); a revisão do PR pelo coautor, 15 (247); a issue #2, 2 casos no teste de falha
fechada da memória (249).

| Arquivo | Testes | O que cobre |
|---|---|---|
| `tests/e2e/test_seguranca_protocolos.py` | 18 | os quatro ataques do feedback, personificação, papel, contraparte, esquema, isolamento de erros, adulteração de conteúdo, cenário adversarial completo e ausência de rejeições nos cenários nominais |
| `tests/e2e/test_approval_gate.py` | 16 | TEST-12 e TEST-13, vínculo com solicitação/veto/ticket, duplicidade, atraso, reutilização entre ciclos de veto, papel do aprovador, SoD da aprovação, justificativa, correção fora das sugeridas, rejeição, reincidência |
| `tests/unit/test_memoria_redacao.py` | 21 | TEST-11 e TEST-23, retenção, persistência entre processos, pseudônimos, adulteração do trace, credenciais fora do trace, falha fechada da memória |
| `tests/e2e/test_revisao_pr.py` | 15 | um teste de regressão por achado da revisão do PR pelo coautor |
| `tests/unit/test_modelos_llm.py` | 8 | TEST-15, 17, 18, 20, 21, 22, 25 e provedor real indisponível |
| `tests/integration/test_dashboard_live.py` (casos novos) | 3 | token de sessão, `Host` e `Origin` na API do dashboard (TEST-73); movidos para `test_dashboard_acesso.py` na v0.5.0 |
| `tests/unit/test_fsm.py`, `tests/unit/test_bus.py` (casos novos) | — | FSM do PROT-APR; mensagem sem credencial e sem protocolo |

## Evidências gravadas

| Evidência | Como gerar |
|---|---|
| Trace do cenário adversarial, verificado | `make ataque` (grava `saidas/ataque.jsonl` e roda `verificar`); âncora `2586f2c81fc2cc1c1739c12be744fce07eb2619044a5c337d2c6e1666becc76e` |
| Comparação em 10 seeds (CSV, JSON, Markdown, SVG) | `python -m fin_mas comparar --seeds 10` → `docs/dsm3/resultados/` |
| Traces de todos os cenários para o replay do dashboard | `python -m fin_mas export` → `web/public/traces/` (37 cenários) |
| Trilha causal legível | `python -m fin_mas run --scenario <nome>` (inclui `REJEITADA`, `POLITICA`, `MEMORIA`, `ATAQUES`, `HIPOTESE`) |
| Conferência do catálogo | `python -m fin_mas cenarios --verificar` |
| Invariantes de um trace | `python -m fin_mas invariantes trace.jsonl` |
| Métricas MET-17 e MET-18 | `metricas.medir_acesso` e `metricas.medir_cognicao` sobre a execução ({doc}`acesso`, {doc}`cognicao`) |
