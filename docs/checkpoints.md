# Checkpoints do DSMA (CP1–CP13)

A apostila da disciplina (Cancian, 2026, seção 5.16) organiza o desenvolvimento em treze
checkpoints incrementais. Cada um tem objetivo, entregável, evidência de conclusão e
critério mínimo. A tabela abaixo resume cada checkpoint **com nossas palavras** e aponta
onde está a evidência neste projeto e em que entrega ela foi produzida. Os checkpoints
não são pesos de avaliação; servem de roteiro para mostrar o que está pronto, o que é
parcial e o que fica para depois.

Legenda: <span class="badge-ok">feito</span> evidência executável no repositório ·
<span class="badge-pend">parcial</span> existe, mas falta parte do critério ·
<span class="badge-pend">planejado</span> previsto para entrega futura.

| CP | Tema | Evidência no projeto | Entrega | Situação |
|---|---|---|---|---|
| CP1 | Cenário e justificativa para SMA (autonomia, distribuição, interdependência, condição de rejeição) | {doc}`dsm1/project_charter` (hipóteses H1–H3 e linha de base) | DSM1 (v2) | <span class="badge-ok">feito</span> |
| CP2 | Requisitos rastreáveis, objetivos, papéis e arquitetura inicial | `models/requirements.yaml`, `roles.yaml`, `agents.yaml`; {doc}`dsm1/requirements`, {doc}`dsm1/roles`, {doc}`dsm2/arquitetura` | DSM1/DSM2 | <span class="badge-ok">feito</span> |
| CP3 | Modelo formal, protocolos com transições válidas e inválidas, métricas | {doc}`dsm1/formal_model`, `models/protocols.yaml`, `models/metrics.yaml` (MET-01 revisada, MET-13, MET-14) | DSM1/DSM2 | <span class="badge-ok">feito</span> |
| CP4 | Executável reproduzível com seed e **baseline** preservada | `python -m fin_mas run`; `src/fin_mas/baseline.py` (workflow centralizado); mesmo hash por seed (TEST-24) | DSM2 | <span class="badge-ok">feito</span> |
| CP5 | Comunicação: identidades, mensagens tipadas, bus, conversation id, timeout, testes negativos | `core/bus.py`, `core/fsm.py`; TEST-03, TEST-07, TEST-26, TEST-28 | DSM2 | <span class="badge-ok">feito</span> |
| CP6 | Coordenação e alocação com mecanismo justificado e conflito real de recurso | delegação por DAG, consulta direta ORC↔CIN, veto/correção (PROT-CMP), reserva de período (PROT-LCK, TEST-14, TEST-35); {doc}`dsm2/coordenacao` | DSM2/DSM3 | <span class="badge-pend">parcial</span>: sem Contract Net (avaliado para a DSM3) |
| CP7 | Tools separadas dos agentes: schema, validação, mocks, efeito protegido | gateway MCP com allowlist (NORM-02), servidor MCP de Excel (TEST-41), correção só com decisão humana | DSM2/DSM3 | <span class="badge-pend">parcial</span>: Approval Gate formal (PROT-APR) na DSM3 |
| CP8 | Conhecimento externo com recuperação e proveniência | base normativa por porte (`models/portes.yaml`, tool `normas.perfil`); proveniência `mcp://…` em toda resposta | DSM2/DSM3 | <span class="badge-pend">parcial</span>: RAG sobre documentos planejado |
| CP9 | Memória persistente com retenção e privacidade | `SVC-MEM` especificado; `COMP-MEM` pendente | DSM3 | <span class="badge-pend">planejado</span> |
| CP10 | Segurança e observabilidade: allowlist, approval gate, trace estruturado | allowlist MCP, trace JSONL com crenças, intenções e decisões, replay pela CLI e dashboard ao vivo; {doc}`dsm2/dashboard` | DSM2 | <span class="badge-pend">parcial</span>: redaction e PROT-APR na DSM3 |
| CP11 | Suíte única de testes com resultado real do runner | `python -m pytest` (e2e e integração) e `npm run test:e2e` (uso real no navegador); {doc}`dsm2/testes` | DSM2 | <span class="badge-ok">feito</span> |
| CP12 | Experimento com baseline, métricas, 10 seeds, dados brutos e ameaças à validade | `python -m fin_mas comparar` → `docs/dsm2/resultados/` (CSV, JSON, SVG); {doc}`dsm2/comparacao` | DSM2 (prévia) / DSM4 | <span class="badge-pend">parcial</span>: experimento completo na DSM4 |
| CP13 | Integração, documentação reproduzível e demonstração | READMEs por entrega, este site, dashboard; roteiro de demonstração na DSM4 | DSM4 | <span class="badge-pend">planejado</span> |

## Artefatos por checkpoint e entrega

- **DSM1 (v2)**: CP1, CP2 e CP3 revisados após o feedback (caracterização cognitiva, MET-01, decisões distribuídas).
- **DSM2 (revisada)**: CP4, CP5, CP11 completos; CP6, CP7, CP8, CP10 e CP12 iniciados com evidência executável.
- **DSM3**: completar CP6 (avaliar Contract Net), CP7 (Approval Gate), CP8 (RAG), CP9 (memória) e CP10 (redaction).
- **DSM4**: CP12 completo (perguntas, cenários, réplicas, análise) e CP13.
