# DSM3 — Comunicação, coordenação e protótipo funcional

**Projeto:** Sistema Multiagente de Controladoria da **SMA** (empresa fictícia) — INE5628 Sistemas Multiagentes.
**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).
**Versão:** 0.5.0 (12/11/2026). Enunciado: [`enunciados/DSM3.txt`](../../enunciados/DSM3.txt).

A DSM3 corrige as falhas de autorização e validação apontadas no feedback da DSM2 e conclui as
funcionalidades previstas. O barramento valida **remetente, destinatário, papel, conversa,
performativo e esquema** antes de mudar qualquer estado. As decisões humanas passam por um
**Approval Gate** formal (PROT-APR): cada uma fica vinculada à solicitação, ao veto (hash), ao
aprovador e a um prazo, é de uso único e segue uma política explícita. Há **memória
persistente** só de decisões aprovadas, **redaction** fail-closed e trace com cadeia de hashes e
selo HMAC.

A versão 0.5.0 acrescenta:

- **identidade e acesso por pessoa** (SVC-IAM): login, sessões, papéis e permissões; a decisão
  no Approval Gate vale pela **pessoa autenticada** (atestado, POL-09), com cargo e segregação de
  funções conferidos contra a pessoa real, e quem pede não aprova (POL-13). Fecha a lacuna da
  primeira versão, em que quem lesse o token do dashboard agia como o aprovador;
- **cognição assistida** no Agente de Orçamento: hipóteses propostas por regras locais ou por um
  LLM, validadas por regras, que só mudam a avaliação com evidência de fonte determinística;
- **negociação de prazo** no PROT-DEL entre especialista e Orquestrador;
- **dashboard autenticado** com áreas de trabalho e **console de administração** no terminal;
- **LLM multiprovedor** opcional (mocks, Claude, GPT, Gemini, modelos locais), com
  consentimento, pseudônimos e bancada de avaliação; sempre offline nos testes;
- **implantação local** (`fin-mas instalar`, `doctor`) e **invariantes** de segurança conferidos
  sobre qualquer trace.

A resposta a cada ponto do feedback está em [`docs/dsm3/revisao.md`](../../docs/dsm3/revisao.md).

## Conteúdo da entrega

| Exigido pelo enunciado | Onde |
|---|---|
| Comunicação com conteúdo e finalidade claros | [`docs/dsm3/protocolos.md`](../../docs/dsm3/protocolos.md); `models/protocols.yaml` (emissores, eventos locais, esquemas, `atestado`, negociação) |
| Protocolo de interação documentado | seis FSMs + [`modelos-editaveis/`](modelos-editaveis/) (validação, PROT-APR, decisão atestada, login, PROT-DEL com negociação, ciclo de hipóteses) |
| Coordenação, negociação, cooperação ou planejamento | [`docs/dsm3/coordenacao.md`](../../docs/dsm3/coordenacao.md), [`docs/dsm3/cognicao.md`](../../docs/dsm3/cognicao.md); negociação de prazo e ação epistêmica ORC→CIN |
| Tratamento de conflito, falha ou alternativa | [`docs/dsm3/seguranca.md`](../../docs/dsm3/seguranca.md) (modelo de ameaças, invariantes); reenvio, replanejamento, prazo, negação, reincidência, hipótese arquivada, extensão recusada, fallback de LLM |
| Testes integrados ou cenários automatizados | `codigo/tests/` (431 testes) e `codigo/web/e2e/` (29 roteiros); [`docs/dsm3/testes.md`](../../docs/dsm3/testes.md), [`docs/dsm3/cenarios-de-teste.md`](../../docs/dsm3/cenarios-de-teste.md) |
| Evidências de comportamento coletivo | traces dos 37 cenários, `docs/dsm3/resultados/` (10 seeds), cenários `ataque_decisao_forjada` e `ataque_acesso` |
| Segurança e acesso | [`docs/dsm3/acesso.md`](../../docs/dsm3/acesso.md), [`docs/dsm3/dashboard.md`](../../docs/dsm3/dashboard.md) |
| Implantação | [`docs/dsm3/implantacao.md`](../../docs/dsm3/implantacao.md) |
| Autoria e uso de IA | este arquivo e [`USO_DE_IA.md`](USO_DE_IA.md) |

**Pacote para envio:** `python tools/empacotar_dsm3.py` (ou `make entrega-dsm3`) gera
`entregas/dsm3/DSM3-entrega.zip`, com esta pasta e uma cópia do código em `codigo/`.

## Como executar

Requer Python 3.11+ (versões exatas em que a suíte passou: `requirements-lock.txt`). Nada usa a
internet em tempo de execução. Para o dashboard, use o comando único descrito no
[README da raiz](../../README.md#um-comando).

```bash
python -m venv .venv
.venv/bin/pip install -e . -r requirements-dev.txt            # Windows: .venv\Scripts\pip
.venv/bin/python -m pytest                                     # 431 testes, offline (unit 95, e2e 254, integração 62, TUI 20)
.venv/bin/python tools/trace.py --check                        # 312 objetos, 21 requisitos, 153 de 153 testes executados, 0 erros
.venv/bin/python -m fin_mas cenarios --verificar               # 37 de 37 cenários em ordem
cd web && bun run test && bun run test:e2e                     # vitest (12) e Playwright no Chrome (29)
make verificar-tudo                                            # tudo acima e a documentação, parando no primeiro erro
```

Cobertura da suíte pytest (`make cobertura`): 87% de 7.401 instruções; subprocessos da CLI
(`python -m fin_mas ...` chamados pelos testes) não entram na medição.

### Roteiro de demonstração

```bash
python -m fin_mas run --scenario ataque_decisao_forjada --trace ataque.jsonl
#   14 ataques ao barramento (os 4 do feedback e outros 10 da mesma família): 0 aceitos; o ticket expira, nada é publicado
python -m fin_mas verificar ataque.jsonl --ancora 2586f2c81fc2cc1c1739c12be744fce07eb2619044a5c337d2c6e1666becc76e
#   a âncora (hash final da cadeia) é reproduzível: confere em qualquer máquina, sem a chave do autor;
#   altere, remova ou corte uma linha e o comando acusa (saída 3)
python -m fin_mas run --scenario ataque_acesso
#   quem controla a caixa APR tenta 15 vezes decidir sem ser a pessoa certa: sem atestado, atestado forjado,
#   de outra decisão, de sessão revogada, replay, cargo sem alçada, aprovador envolvido, solicitante decidindo,
#   escalada de privilégio. 15 de 15 recusados (POL-09, 02, 03, 13, IAM-05, 06); nada é publicado
python -m fin_mas run --scenario decisao_por_pessoa
#   carla criou o lançamento vetado e tenta decidir: POL-03; diego decide e o fechamento é publicado
python -m fin_mas run --scenario orc_hipotese_local
#   a consulta ao AG-CIN se perde; a observação da planilha gera a hipótese causa_controle; o AG-ORC consulta
#   de novo, o AG-CIN contesta o valor e o desvio deixa de ser falso desvio
python -m fin_mas run --scenario negociacao_prazo
#   a nova consulta não cabe no prazo: propose -> accept-proposal no PROT-DEL; hipótese confirmada
python -m fin_mas run --scenario veto_correcao
#   veto -> ticket APR-001 -> approve (corrigir) -> erp.corrigir com a aprovação -> AG-CIN reavalia -> publicado
python -m fin_mas run --scenario reincidencia_waiver --memoria memoria.json
#   waiver em agosto vira memória; em setembro o AG-CIN cita MEM-0001, a política (POL-06) nega novo waiver
python -m fin_mas serve --demo
#   dashboard em http://127.0.0.1:8765; entre como avaliador (senha Demonstracao-SMA-2026) para ver tudo,
#   ou como operador, auditor, carla, diego... para ver o que cada papel pode
```

Contas de demonstração (senha pública `Demonstracao-SMA-2026`, só para avaliação e aula):
`avaliador`, `admin`, `operador`, `auditor`, `controller`, `elisa`, `carla`, `diego`, `ana`,
`bruno`. Papéis, cargos e para que serve cada uma:
[`docs/dsm3/acesso.md`](../../docs/dsm3/acesso.md). Console de administração:
`python -m fin_mas acesso --acesso dados/acesso tui` (extra `tui`).

## Feedback da DSM2 → correção

| Falha relatada | Agora | Teste |
|---|---|---|
| `decisao_humana` de remetente inexistente liberou o fechamento vetado | remetente precisa estar registrado e ter credencial; o canal livre acabou; a decisão só vale pelo PROT-APR, validada pelo SVC-POL, e (v0.5.0) atestada pela pessoa autenticada | `test_forged_human_decision_from_unknown_sender_is_rejected`, `test_access_attacks_are_all_rejected_and_nothing_is_published` |
| transição local por identificador não autorizado | `advance` exige credencial, participação e papel autorizado em `eventos_locais` | `test_local_transition_by_unauthorized_identity_is_rejected` |
| resposta a quem não participava da conversa | destinatário tem de ser a contraparte e ter papel participante | `test_reply_to_non_participant_receiver_is_rejected` |
| `KeyError` por campo obrigatório ausente | esquema por performativo; erro de agente isolado e respondido | `test_malformed_request_does_not_crash_simulation` |
| suíte não detectava as violações | testes adversariais (falsificação, duplicidade, atraso, reutilização, papel, SoD, adulteração, acesso): 249 testes na tag `dsm3-base`, 414 na v0.5.0 | `docs/dsm3/testes.md` |
| baseline sem veto/correção | ressalva registrada; workflow equivalente planejado para a DSM4 | `docs/dsm3/limitacoes.md` |

## Componentes novos

| Código | Componente | Papel |
|---|---|---|
| `core/bus.py`, `core/schema.py`, `core/diretorio.py`, `core/agent.py` | `COMP-A2A`, `COMP-SCH` | autenticação, papel, contraparte, esquema, integridade, isolamento de erros; prazo vigente por conversa (v0.5.0) |
| `services/politica.py` | `COMP-POL` (SVC-POL) | tickets do Approval Gate e política POL-01..09 e POL-13 |
| `services/memoria.py` | `COMP-MEM` (SVC-MEM) | memória aprovada, persistente, com retenção e pseudônimos |
| `services/redacao.py`, `services/audit.py` | `COMP-RED` | redaction fail-closed e JSONL com hash encadeado |
| `services/modelos.py` | `COMP-MOD` (SVC-MOD) | LLM opcional com usos por agente, validação numérica por rótulo, cota, consentimento, disjuntor e logs |
| `services/provedores.py`, `services/pseudonimos.py` | `COMP-PRV` | provedores de LLM (mocks, Claude, GPT, Gemini, compatível OpenAI) e pseudônimos do envio externo |
| `core/inferencia.py`, `cognicao/` | `COMP-INF`, `COMP-COG` | hipóteses: proposta, validação, estados; motor local de regras; proponente LLM; bancada |
| `services/iam.py`, `services/selado.py`, `services/trilha.py`, `core/permissoes.py` | `COMP-IAM`, `COMP-SEL`, `COMP-TRI` (SVC-IAM) | contas, sessões, papéis, atestado; arquivo selado com trava; trilha de acesso encadeada |
| `cli_acesso.py`, `tui/`, `implantacao.py` | `COMP-CLA`, `COMP-TUI`, `COMP-IMP` | linha de comando de acesso, console de administração, `instalar` e `doctor` |
| `invariantes.py`, `services/explicacao.py`, `services/consulta.py` | `COMP-INV`, `COMP-EXP` | invariantes INV-01..08, explicação de decisões e sequência, filtros do trace |
| `server.py`, `live.py`, `web/src/` | — | login, CSRF, permissão por rota e comando, áreas de trabalho, hipóteses na mente do agente |
| `env/ataques.py`, `env/ataques_acesso.py` | — | ataques dos cenários adversariais (14 e 15) |

Decisões de arquitetura: [ADR-007](../../docs/dsm3/ADR-007-autenticidade-e-approval-gate.md),
[ADR-008](../../docs/dsm3/ADR-008-cognicao-local-e-llm.md),
[ADR-009](../../docs/dsm3/ADR-009-identidade-e-acesso.md).
Limitações e plano da DSM4: [`docs/dsm3/limitacoes.md`](../../docs/dsm3/limitacoes.md).

## Estrutura da pasta

```
entregas/dsm3/
  README.md            este arquivo
  USO_DE_IA.md         uso de IA no desenvolvimento da entrega
  modelos-editaveis/   7 diagramas Mermaid (.mmd)
  diagramas/           7 imagens (.png), uma por .mmd (make diagramas regenera as desatualizadas)
  DSM3-entrega.zip     pacote para envio (gerado por tools/empacotar_dsm3.py; não versionado)
```

| Diagrama | Imagem | Fonte editável |
|---|---|---|
| Pipeline de validação do barramento | [`diagramas/pipeline_validacao.png`](diagramas/pipeline_validacao.png) | [`pipeline_validacao.mmd`](modelos-editaveis/pipeline_validacao.mmd) |
| FSM do Approval Gate (PROT-APR) | [`diagramas/fsm_prot_apr.png`](diagramas/fsm_prot_apr.png) | [`fsm_prot_apr.mmd`](modelos-editaveis/fsm_prot_apr.mmd) |
| Sequência veto → aprovação → correção | [`diagramas/sequencia_approval_gate.png`](diagramas/sequencia_approval_gate.png) | [`sequencia_approval_gate.mmd`](modelos-editaveis/sequencia_approval_gate.mmd) |
| Login e sessão (v0.5.0) | [`diagramas/sequencia_login_sessao.png`](diagramas/sequencia_login_sessao.png) | [`sequencia_login_sessao.mmd`](modelos-editaveis/sequencia_login_sessao.mmd) |
| Decisão atestada pela pessoa (v0.5.0) | [`diagramas/sequencia_decisao_atestada.png`](diagramas/sequencia_decisao_atestada.png) | [`sequencia_decisao_atestada.mmd`](modelos-editaveis/sequencia_decisao_atestada.mmd) |
| Ciclo das hipóteses (v0.5.0) | [`diagramas/ciclo_hipoteses.png`](diagramas/ciclo_hipoteses.png) | [`ciclo_hipoteses.mmd`](modelos-editaveis/ciclo_hipoteses.mmd) |
| FSM do PROT-DEL com negociação (v0.5.0) | [`diagramas/fsm_prot_del_negociacao.png`](diagramas/fsm_prot_del_negociacao.png) | [`fsm_prot_del_negociacao.mmd`](modelos-editaveis/fsm_prot_del_negociacao.mmd) |

Para regenerar as imagens: `make diagramas` (usa o mermaid de `web/node_modules` e o
Playwright; só refaz as desatualizadas).
