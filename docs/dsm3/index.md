# DSM3 — Comunicação, coordenação e protótipo funcional

<span class="badge-ok">concluída</span> · prazo: 18/11/2026 · versão 0.5.0

A DSM3 consolida a **segurança e a robustez das interações** apontadas no feedback da DSM2 e
conclui as funcionalidades que estavam previstas: barramento que valida remetente,
destinatário, papel, conversa, performativo e esquema; **Approval Gate** formal (PROT-APR) com
política de aprovação explícita; **memória persistente** aprovada (SVC-MEM); **proteção de
informações** (redaction fail-closed, pseudônimos, trace com hash encadeado); **LLM opcional**
com validação numérica, sempre offline nos testes. O que mudou em resposta ao feedback, ponto
a ponto, está em {doc}`revisao`.

A versão 0.5.0 (12/11/2026) acrescenta:

- **cognição assistida** no AG-ORC: proposta → validação → hipótese → ação epistêmica →
  evidência → crença, com motor local offline e LLM opcional ({doc}`cognicao`, ADR-008);
- **negociação de prazo** no PROT-DEL entre especialista e Orquestrador ({doc}`protocolos`);
- **identidade e acesso por pessoa** (SVC-IAM): login, sessões, papéis, decisão no Approval
  Gate vinculada à pessoa autenticada, trilha de acesso íntegra ({doc}`acesso`, ADR-009);
- **dashboard autenticado** com áreas de trabalho e **console de administração** no terminal
  ({doc}`dashboard`);
- **LLM multiprovedor** (mock, Claude, GPT, Gemini, servidores compatíveis com a API da OpenAI)
  com consentimento, pseudônimos e bancada de avaliação ({doc}`llm`);
- **implantação local** (`fin-mas instalar`, `doctor`, `serve --instalacao`) e ficha dos portes
  ({doc}`implantacao`);
- **invariantes** de segurança conferidos sobre qualquer trace e catálogo de cenários
  verificável ({doc}`seguranca`, {doc}`cenarios-de-teste`).

## Enunciado e onde está cada critério

| Critério | Peso | Página |
|---|---|---|
| Comunicação e protocolos | 25% | {doc}`protocolos` (envelope, validação, papéis, esquemas, PROT-APR com atestado, PROT-DEL com negociação) · ADR-007 |
| Coordenação coletiva | 25% | {doc}`coordenacao` (delegação, consulta direta, veto→aprovação→correção, reserva, memória entre ciclos, ação epistêmica ORC→CIN, negociação de prazo) · {doc}`cognicao` · ADR-008 |
| Corretude e robustez | 25% | {doc}`seguranca` (14 + 15 ataques rejeitados, política POL-01..09 e POL-13, modelo de ameaças, 8 invariantes) · {doc}`acesso` · ADR-009 |
| Testes e evidências | 15% | {doc}`testes` · {doc}`cenarios-de-teste` · `docs/dsm3/resultados/` · cenários `ataque_decisao_forjada` e `ataque_acesso` |
| Documentação e autoria | 10% | `entregas/dsm3/README.md` · `entregas/dsm3/USO_DE_IA.md` · {doc}`limitacoes` · {doc}`implantacao` |

| Requisito do enunciado | Evidência |
|---|---|
| Comunicação com conteúdo e finalidade claros | performativos FIPA por protocolo com esquema de conteúdo validado (`models/protocols.yaml`, `core/schema.py`); `propose`/`accept-proposal`/`reject-proposal` com esquema no PROT-DEL; `atestado` no `approve`/`reject` |
| Protocolo de interação documentado | seis FSMs com transições válidas e inválidas, emissores e eventos locais; estado `NEGOCIANDO` no PROT-DEL; diagramas em `entregas/dsm3/modelos-editaveis/` |
| Coordenação, negociação, cooperação ou planejamento | DAG do Orquestrador, consulta ORC↔CIN, ciclo veto→aprovação→correção→reavaliação, exclusão mútua de período, **negociação de prazo** (`negociacao_prazo`, `negociacao_recusada`), **ação epistêmica** do AG-ORC ao AG-CIN para verificar hipótese |
| Tratamento de conflito, falha ou alternativa | reenvio e falha explícita, replanejamento BDI, prazo do ticket, decisão negada pela política, reincidência, hipótese arquivada sem evidência, extensão de prazo recusada, fallback e disjuntor do LLM |
| Testes integrados ou cenários automatizados | 437 testes pytest (unit 95, e2e 260, integração 62, TUI 20), 30 roteiros Playwright, 12 vitest; 37 cenários nomeados, todos conferidos por `cenarios --verificar` |
| Evidências de comportamento coletivo | traces JSONL com crenças, hipóteses, intenções, decisões, rejeições, tickets e autor de cada decisão; comparação em 10 seeds; MET-15 a MET-18 |

Rastreabilidade (`python tools/trace.py --check`): 315 objetos, 21 requisitos com cadeia
completa, 156 testes modelados (156 executados), 18 métricas, 0 erros.

## Como reproduzir

```bash
python -m fin_mas cenarios --verificar                    # 37 de 37: resposta explícita, 8 invariantes, repetível
python -m fin_mas run --scenario ataque_decisao_forjada   # 14 ataques ao barramento, 0 aceitos
python -m fin_mas run --scenario ataque_acesso            # 15 ataques de quem controla a caixa APR, 0 aceitos
python -m fin_mas run --scenario orc_hipotese_local       # hipótese -> nova consulta ao AG-CIN -> confirmada
python -m fin_mas run --scenario negociacao_prazo         # propose / accept-proposal no PROT-DEL
python -m fin_mas run --scenario decisao_por_pessoa       # POL-03 contra a pessoa real
python -m fin_mas run --scenario reincidencia_waiver      # memória entre meses + POL-06
python -m fin_mas run --scenario veto_correcao --trace t.jsonl && python -m fin_mas verificar t.jsonl
python -m fin_mas serve --demo                            # dashboard: http://127.0.0.1:8765, senha Demonstracao-SMA-2026
python -m pytest                                          # 437 testes
```

```{toctree}
:maxdepth: 1

revisao
protocolos
coordenacao
cognicao
seguranca
acesso
memoria
llm
dashboard
implantacao
testes
cenarios-de-teste
limitacoes
ADR-007-autenticidade-e-approval-gate
ADR-008-cognicao-local-e-llm
ADR-009-identidade-e-acesso
```
