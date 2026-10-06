# Métricas e evidências de sucesso

As métricas serão coletadas dos **traces JSONL** (`SVC-AUD`) em cenários sintéticos com
gabarito, executados com seeds controlados (a partir da DSM2) e comparados à
**baseline** (workflow sequencial único, ver [project charter](project_charter.md)).

```{needtable}
:types: metric
:columns: id, title as "Métrica", measures as "Requisitos medidos"
:style: table
```

```{include} ../_generated/metrics.md
```

## Testes derivados dos modelos

Os testes abaixo são **especificados** na DSM1 a partir de requisitos, protocolos e
normas. Nenhum está marcado como aprovado: a execução e o resultado real são entregues
na DSM2.

```{needtable}
:types: test
:columns: id, title as "Teste", verifies as "Verifica", derived_from as "Derivado de", entrega, status
:style: table
```

```{include} ../_generated/tests.md
```
