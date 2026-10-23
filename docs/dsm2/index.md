# DSM2 — Arquitetura e protótipo inicial

<span class="badge-ok">em implementação</span>

Protótipo executável em `src/fin_mas/` (Python), com documentação em [Protótipo](prototipo.md),
[Testes](testes.md) e [Limitações](limitacoes.md). O que é de DSM3 e DSM4 (LLM, memória, Approval
Gate, métricas, dashboard) ficou fora de propósito.

## Enunciado

**Entregar:** código-fonte executável; diagrama de arquitetura; `README.md`; testes
iniciais; `USO_DE_IA.md`.

**Requisitos:** justificar arquitetura e runtime; implementar agentes principais e
ambiente; implementar estado/conhecimento e comportamento básico; demonstrar ao menos
uma interação; incluir cenário controlado para depuração; registrar limitações.

| Critério | Peso | Página |
|---|---|---|
| Arquitetura e justificativa | 25% | [Arquitetura](arquitetura.md) · [Runtime](runtime.md) |
| Implementação | 25% | [Protótipo](prototipo.md) |
| Interação e corretude | 20% | [Protótipo](prototipo.md) · [Testes](testes.md) |
| Testes e reprodutibilidade | 20% | [Testes](testes.md) |
| Documentação e autoria | 10% | `entregas/dsm2/README.md` · `entregas/dsm2/USO_DE_IA.md` |

## Checklist de entregáveis

- [x] Diagrama de arquitetura (camadas → componentes `COMP-*`)
- [x] ADR-003 de runtime e linguagem, justificada pelos requisitos (Cancian, 2026, §4.6)
- [x] ADR-004 de transporte A2A concreto e MCP servers mock
- [x] Código executável: agentes principais + ambiente sintético
- [x] Estado/conhecimento separados (crenças × regras × memória)
- [x] Pelo menos uma interação demonstrada (sugestão: {need}`PROT-DEL` + {need}`PROT-QRY`)
- [x] Cenário controlado de depuração (seed fixo, dataset com gabarito)
- [x] Testes iniciais: mudar o `status` dos `TEST-*` escolhidos de `planejado` para `executado`, com resultado real
- [x] Limitações registradas
- [x] `entregas/dsm2/README.md` e `entregas/dsm2/USO_DE_IA.md`
- [x] Componentes `COMP-*` com `caminho` real e `entrega: DSM2`, `status: implementado`

## Herdado da DSM1 e o que foi feito

| Da DSM1 | Na DSM2 |
|---|---|
| 6 agentes e 7 serviços especificados | 6 agentes e 4 serviços (A2A, MCP, auditoria, reserva de período) implementados ({doc}`arquitetura`); registro de modelos, memória e política ficam para a DSM3 |
| 6 protocolos com FSM e transições inválidas | FSMs carregadas de `models/protocols.yaml`; testes nominais e negativos |
| 8 normas (`NORM-*`) | NORM-02 (allowlist MCP), NORM-03 (período exclusivo) e NORM-04 (veto) em código; as demais ficam para a DSM3 |
| 26 testes planejados | 14 executados (ver {doc}`testes`) |
| 12 métricas | não instrumentadas; o trace JSONL guarda os dados |
| ADR-002 (LLM por flag) | só o modo template; a flag e o mock de LLM ficam para a DSM3 |

## Perguntas em aberto da DSM1, resolvidas

1. **Runtime:** Python puro com scheduler determinístico ({doc}`ADR-003-runtime-python-deterministico`).
2. **Transporte A2A:** barramento local em processo com interface mínima para um adaptador futuro ({doc}`ADR-004-a2a-bus-e-mcp-mock`).
3. **Dataset:** estruturas Python geradas por seed, com gabarito do que foi plantado.
4. **Suíte inicial:** os 14 testes listados em {doc}`testes`.

```{toctree}
:maxdepth: 1

arquitetura
runtime
ADR-003-runtime-python-deterministico
ADR-004-a2a-bus-e-mcp-mock
prototipo
testes
limitacoes
```
