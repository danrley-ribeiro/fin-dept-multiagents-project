### Funcional: REQ-F01 a REQ-F04

```{needflow}
:filter: id in ["PROT-DEL", "PROT-QRY", "PROT-SOL", "REQ-F01", "REQ-F02", "REQ-F03", "REQ-F04", "ROLE-CUS", "ROLE-ORC", "ROLE-ORQ", "ROLE-RES", "ROLE-SOL"]
:link_types: assigned_to, uses_protocol, constrained_by
```

### Funcional: REQ-F05 a REQ-F08

```{needflow}
:filter: id in ["NORM-04", "NORM-05", "NORM-07", "NORM-08", "NORM-11", "PROT-APR", "PROT-CMP", "PROT-DEL", "PROT-QRY", "REQ-F05", "REQ-F06", "REQ-F07", "REQ-F08", "ROLE-CIN", "ROLE-CUS", "ROLE-ORC", "ROLE-ORQ", "ROLE-REL", "ROLE-RES"]
:link_types: assigned_to, uses_protocol, constrained_by
```

### Funcional: REQ-F20 a REQ-F21

```{needflow}
:filter: id in ["NORM-02", "NORM-07", "NORM-08", "NORM-11", "NORM-20", "NORM-21", "PROT-CMP", "PROT-DEL", "PROT-QRY", "REQ-F20", "REQ-F21", "ROLE-CIN", "ROLE-CUS", "ROLE-ORC", "ROLE-REL", "ROLE-RES"]
:link_types: assigned_to, uses_protocol, constrained_by
```

### Segurança: REQ-S01 a REQ-S03

```{needflow}
:filter: id in ["NORM-01", "NORM-02", "NORM-03", "NORM-05", "NORM-09", "NORM-10", "PROT-APR", "PROT-CMP", "PROT-DEL", "PROT-LCK", "PROT-QRY", "PROT-SOL", "REQ-S01", "REQ-S02", "REQ-S03", "REQ-S04", "ROLE-APR", "ROLE-CIN", "ROLE-ORC", "ROLE-ORQ", "ROLE-REL", "ROLE-RES", "ROLE-SOL"]
:link_types: assigned_to, uses_protocol, constrained_by
```

### Segurança: REQ-S05

```{needflow}
:filter: id in ["NORM-10", "NORM-12", "NORM-13", "PROT-APR", "REQ-S05", "ROLE-ADM", "ROLE-APR", "ROLE-AUD", "ROLE-OPE", "ROLE-SOL"]
:link_types: assigned_to, uses_protocol, constrained_by
```

### Observabilidade: REQ-O01 a REQ-O04

```{needflow}
:filter: id in ["NORM-06", "NORM-07", "NORM-12", "PROT-DEL", "REQ-O01", "REQ-O02", "REQ-O03", "REQ-O04", "ROLE-APR", "ROLE-AUD", "ROLE-CIN", "ROLE-CUS", "ROLE-OPE", "ROLE-ORC", "ROLE-ORQ", "ROLE-REL", "ROLE-RES", "ROLE-SOL"]
:link_types: assigned_to, uses_protocol, constrained_by
```

### Demais requisitos: REQ-C01 a REQ-NF02

```{needflow}
:filter: id in ["NORM-06", "NORM-07", "PROT-DEL", "REQ-C01", "REQ-NF01", "REQ-NF02", "REQ-P01", "ROLE-APR", "ROLE-CIN", "ROLE-ORC", "ROLE-ORQ", "ROLE-REL", "ROLE-RES"]
:link_types: assigned_to, uses_protocol, constrained_by
```
