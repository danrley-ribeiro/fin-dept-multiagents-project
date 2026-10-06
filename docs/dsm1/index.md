# DSM1 — Cenário, requisitos e modelagem

<span class="badge-ok">concluída</span> · Peso: 20% da MPDSM · Prazo: 10/10/2026 23:55 · Versão 1.0

**PDF da entrega:** [`entregas/dsm1/main.pdf`](https://github.com/danrley-ribeiro/fin-dept-multiagents-project/blob/main/entregas/dsm1/main.pdf)
(fonte LaTeX: `entregas/dsm1/main.tex`).

## Entregáveis exigidos

| Exigido pelo enunciado | Onde está |
|---|---|
| PDF de ~4–6 páginas | `entregas/dsm1/main.pdf` |
| Diagramas/modelos editáveis | `models/*.yaml` (modelos AOSE), `diagrams/dsm1/*.mmd` (Mermaid), `entregas/dsm1/figures/*.tex` (TikZ) |
| `README.md` | raiz do repositório |
| `USO_DE_IA.md` | raiz do repositório (seção DSM1) |

## Conteúdo × critérios de avaliação

| Critério (peso) | Conteúdo exigido | Página |
|---|---|---|
| Problema e objetivos (20%) | cenário-problema, motivação e objetivo | [Project charter](project_charter.md) |
| Agentes e ambiente (25%) | fronteira e ambiente | [Fronteira e ambiente](ambiente.md) |
| | agentes, papéis e responsabilidades | [Papéis e agentes](roles.md) |
| | objetivos, percepções, ações, estado e conhecimento | [Modelo formal (PEAS/BDI)](formal_model.md) |
| Interações e coordenação (25%) | interações e coordenação previstas | [Protocolos e normas](protocols.md) |
| Rastreabilidade (20%) | requisitos e matriz ponta a ponta | [Requisitos](requirements.md) · [Matriz](traceability.md) |
| | métricas/evidências de sucesso | [Métricas e testes derivados](metrics.md) |
| Documentação e autoria (10%) | README, USO_DE_IA, decisões | [ADR-002](ADR-002-llm-opcional-por-flag.md) · `README.md` · `USO_DE_IA.md` |

## Metodologia

Combinação controlada de três lentes AOSE (Cancian, 2026, §4.4), cada uma respondendo
a uma pergunta declarada:

- **Tropos** → stakeholders, objetivos e dependências (*early requirements*);
- **Gaia** → papéis ⟨Resp, Perm, Obl, Prot⟩, protocolos e normas organizacionais;
- **Prometheus** → cenário âncora, percepções/ações por agente e caminho até o design (DSM2).

```{toctree}
:maxdepth: 1

project_charter
ambiente
requirements
roles
formal_model
protocols
metrics
traceability
ADR-002-llm-opcional-por-flag
```
