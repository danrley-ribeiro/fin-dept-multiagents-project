<!-- ARQUIVO GERADO por tools/trace.py a partir de models/*.yaml — não editar à mão -->

### Funcional: REQ-F01 a REQ-F04

```{needflow}
:filter: id in ["PROT-DEL", "PROT-QRY", "PROT-SOL", "REQ-F01", "REQ-F02", "REQ-F03", "REQ-F04", "ROLE-CUS", "ROLE-ORC", "ROLE-ORQ", "ROLE-RES", "ROLE-SOL"]
:link_types: assigned_to, uses_protocol, constrained_by
```

### Funcional: REQ-F05 a REQ-F07

```{needflow}
:filter: id in ["NORM-04", "NORM-05", "NORM-07", "NORM-08", "PROT-APR", "PROT-CMP", "PROT-DEL", "REQ-F05", "REQ-F06", "REQ-F07", "ROLE-CIN", "ROLE-CUS", "ROLE-ORC", "ROLE-ORQ", "ROLE-REL", "ROLE-RES"]
:link_types: assigned_to, uses_protocol, constrained_by
```

### Segurança: REQ-S01 a REQ-S03

```{needflow}
:filter: id in ["NORM-01", "NORM-02", "NORM-03", "NORM-05", "PROT-APR", "PROT-LCK", "REQ-S01", "REQ-S02", "REQ-S03", "ROLE-APR", "ROLE-ORC", "ROLE-ORQ", "ROLE-REL", "ROLE-RES"]
:link_types: assigned_to, uses_protocol, constrained_by
```

### Observabilidade: REQ-O01 a REQ-O04

```{needflow}
:filter: id in ["NORM-06", "NORM-07", "PROT-DEL", "REQ-O01", "REQ-O02", "REQ-O03", "REQ-O04", "ROLE-APR", "ROLE-CIN", "ROLE-CUS", "ROLE-ORC", "ROLE-ORQ", "ROLE-REL", "ROLE-RES", "ROLE-SOL"]
:link_types: assigned_to, uses_protocol, constrained_by
```

### Demais requisitos: REQ-C01 a REQ-NF02

```{needflow}
:filter: id in ["NORM-06", "NORM-07", "PROT-DEL", "REQ-C01", "REQ-NF01", "REQ-NF02", "REQ-P01", "ROLE-APR", "ROLE-CIN", "ROLE-ORC", "ROLE-ORQ", "ROLE-REL", "ROLE-RES"]
:link_types: assigned_to, uses_protocol, constrained_by
```
