# DSM2 — Arquitetura e protótipo inicial

<span class="badge-pend">pendente</span> · Peso: 25% da MPDSM · Prazo: 31/10/2026 23:55

```{admonition} Entrega ainda não iniciada
:class: warning
Esta seção está **pré-estruturada**: contém o enunciado, os critérios, o checklist de
entregáveis e o que a DSM1 deixou como ponto de partida. Nenhuma decisão de
arquitetura, runtime ou código foi tomada ainda.
```

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
| Documentação e autoria | 10% | `README.md` · `USO_DE_IA.md` (seção DSM2) |

## Checklist de entregáveis

- [ ] Diagrama de arquitetura (camadas → componentes `COMP-*`)
- [ ] ADR-003 de runtime e linguagem, justificada pelos requisitos (Cancian, 2026, §4.6)
- [ ] ADR-004 de transporte A2A concreto e MCP servers mock
- [ ] Código executável: agentes principais + ambiente sintético
- [ ] Estado/conhecimento separados (crenças × regras × memória)
- [ ] Pelo menos uma interação demonstrada (sugestão: {need}`PROT-DEL` + {need}`PROT-QRY`)
- [ ] Cenário controlado de depuração (seed fixo, dataset com gabarito)
- [ ] Testes iniciais: mudar o `status` dos `TEST-*` escolhidos de `planejado` para `executado`, com resultado real
- [ ] Limitações registradas
- [ ] `README.md` e `USO_DE_IA.md` (seção DSM2) atualizados
- [ ] Componentes `COMP-*` com `caminho` real e `entrega: DSM2`, `status: implementado`

## Herdado da DSM1 → a fazer na DSM2

| Da DSM1 | Ação na DSM2 |
|---|---|
| 6 agentes e 7 serviços especificados | mapear para componentes ({doc}`arquitetura`) |
| 6 protocolos com FSM e transições inválidas | implementar FSM e testes nominais/negativos |
| 8 normas (`NORM-*`) | implementar `SafetyPolicy`, `ModelRegistry` e redaction |
| 25 testes planejados | escolher o subconjunto inicial e executar |
| 12 métricas | instrumentar o tracer para coletá-las |
| ADR-002 (LLM por flag) | implementar a flag com mock de LLM (offline) |

## Perguntas em aberto (decidir na DSM2)

1. Runtime: Python puro com scheduler determinístico, SPADE ou outro? Critérios: offline, testabilidade, semântica de mensagens.
2. Transporte A2A: barramento local em processo (didático) com adaptador para o protocolo A2A real?
3. Formato do dataset sintético e do gabarito (CSV, SQLite?).
4. Quais `TEST-*` compõem a suíte inicial mínima?

```{toctree}
:maxdepth: 1

arquitetura
runtime
prototipo
testes
limitacoes
```
