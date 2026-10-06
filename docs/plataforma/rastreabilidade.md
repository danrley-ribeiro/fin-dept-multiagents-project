# Rastreabilidade

## Princípio

A cadeia segue o modelo de Cancian (2026, Cap. 4): cada requisito precisa poder
responder **"por que este componente existe?"** e **"que teste detectaria sua
regressão?"**. A evidência do teste volta ao requisito que a originou.

```{mermaid}
flowchart LR
  P[Problema<br/>PROB] --> R[Requisito<br/>REQ] --> G[Objetivo<br/>G] --> RA[Papel / Agente<br/>ROLE / AG]
  RA --> PN[Protocolo / Norma<br/>PROT / NORM] --> C[Componente<br/>COMP · DSM2] --> T[Teste<br/>TEST]
  T -. "evidência retroalimenta o critério de aceite" .-> R
  M[Métrica<br/>MET] -. mede .-> R
```

## Fonte única e verificação automática

| Camada | Onde fica | Quem garante |
|---|---|---|
| Modelos (fonte única) | `models/*.yaml` | edição humana revisada por PR |
| Validação da cadeia | `tools/trace.py --check` | CI falha com ID órfão, link quebrado, requisito sem objetivo, papel, protocolo/norma, teste ou métrica |
| Objetos da documentação | `docs/_generated/*.md` (gerado) | sphinx-needs + `needs_warnings` com build `-W` |
| Tabelas do PDF | `entregas/dsm1/generated/*.tex` (gerado) | mesma fonte; o PDF nunca diverge do site |
| Diagramas de estado | `diagrams/dsm1/fsm_*.mmd` (gerado) | derivados das transições de `models/protocols.yaml` |

Regras verificadas pelo `trace.py` (resumo):

- IDs únicos, com prefixo correto, e todo link aponta para um ID existente do tipo certo;
- todo **problema** é endereçado por um requisito; todo **objetivo-folha** é satisfeito por um requisito;
- todo **requisito** tem objetivo, problema, papel, protocolo ou norma, evidência, **teste** e **métrica**;
- todo **papel** tem ⟨Resp, Perm, Obl, Prot⟩ não vazios e é exercido por agente ou humano;
  papel e protocolo declaram-se mutuamente;
- todo **protocolo** tem ≥ 2 participantes, estados finais alcançáveis e ao menos uma **transição inválida**
  (origem de teste negativo);
- LLM só é permitido (por flag) em `AG-REL`, `AG-RES` e `AG-ORC`;
- nenhum teste pode ser marcado `PASS` na DSM1 (não há execução real ainda).

## Situação atual

```{include} ../_generated/cobertura.md
```

## Grafos por parte

O grafo com todos os objetos ao mesmo tempo é detalhado demais para ser lido, por isso a
documentação **nunca o exibe**. Cada grafo mostra apenas um recorte:

| Recorte | Onde |
|---|---|
| Árvore de objetivos | [Project charter](../dsm1/project_charter.md) |
| Objetivo-folha → problema | [Project charter](../dsm1/project_charter.md) |
| Agente → objetivo | [Modelo formal](../dsm1/formal_model.md) |
| Requisito → papel → protocolo → norma, por grupo de até 4 requisitos | [Matriz de rastreabilidade](../dsm1/traceability.md) |

Os grafos de requisitos são gerados por `tools/trace.py`: os requisitos são agrupados por tipo,
com no máximo 4 por grafo (`GRAPH_CHUNK`), e tipos com poucos requisitos são reunidos em um grupo
único. Assim os grafos continuam legíveis à medida que novas entregas acrescentam requisitos.

## Exportação

O build gera `needs.json` (todos os objetos e links), utilizável por outras ferramentas
(planilhas, Jira, scripts de auditoria).
