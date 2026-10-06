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

## Grafo completo

```{needflow}
:types: prob, goal, req, role, agent, prot, norm
:show_link_names:
:scale: 60
```

## Exportação

O build gera `needs.json` (todos os objetos e links), utilizável por outras ferramentas
(planilhas, Jira, scripts de auditoria).
