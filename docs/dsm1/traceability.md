# Matriz de rastreabilidade ponta a ponta

Cada necessidade do negócio está ligada a requisito, objetivo, papel/agente,
protocolo/norma, componente (stub DSM2), teste derivado e métrica. A matriz é gerada da
mesma fonte das tabelas do PDF.

```{include} ../_generated/cobertura.md
```

## Matriz

```{include} ../_generated/matriz.md
```

## Matriz interativa (filtrável)

```{needtable}
:types: req
:columns: id, title as "Requisito", addresses as "Problema", satisfies as "Objetivo", assigned_to as "Papéis", uses_protocol as "Protocolos", constrained_by as "Normas", verifies_back as "Testes", measures_back as "Métricas"
:style: datatables
```

## Grafo requisito → papel → protocolo → norma

```{needflow}
:types: req, role, prot, norm
:link_types: assigned_to, uses_protocol, constrained_by
:scale: 55
```

## Itens pendentes (DSM2 e futuro)

```{needtable}
:filter: entrega in ["DSM2", "FUTURA"]
:columns: id, title, type_name as "Tipo", entrega, status
:style: table
```
