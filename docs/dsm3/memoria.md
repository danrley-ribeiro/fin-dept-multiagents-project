# Memória persistente (SVC-MEM)

`src/fin_mas/services/memoria.py` implementa o SVC-MEM especificado na DSM1 (REQ-F07,
NORM-08, NORM-06), com uma simplificação assumida: em vez de embeddings e grafo, a memória é
um índice por **padrão** (tipo + chave), suficiente para o uso que os agentes fazem dela e
determinístico nos testes.

| Regra | Implementação |
|---|---|
| Só saída aprovada vira memória (NORM-08) | toda gravação cita um ticket PROT-APR que o SVC-POL confirma como decidido por humano (aprovado, executado ou rejeitado); sem isso, `recusada` |
| Proveniência | aprovação, solicitação, conversa vetada, decisão, quem decidiu (pseudônimo) e fonte; quem consulta recebe o id `MEM-…` |
| Controle de acesso | por tipo: quem grava e quem lê (hoje, só o AG-CIN usa a memória) |
| Privacidade (NORM-06) | redaction fail-closed do valor; pessoas como `pessoa#…` (hash estável) |
| Retenção | entradas mais antigas que `retencao` competências (padrão 12) expiram na consulta |
| Persistência | arquivo JSON gravado de forma atômica (`--memoria ARQ`); sem arquivo, só em memória (padrão dos testes) |

## Como os agentes usam

- **Grava:** o AG-CIN, ao receber `waiver_humano` (tipo `waiver`, chave = regra + pessoa ou
  fornecedor do lançamento), `correcao` (tipo `correcao`) e `prazo_esgotado` com `decisao: bloquear`
  (tipo `bloqueio`). Prazo expirado ou ação negada **não** viram memória: não houve decisão humana.
- **Consulta:** o AG-CIN, antes de vetar, procura waiver anterior para o mesmo padrão em
  competências anteriores. Se encontra, marca o achado como **reincidente** (crença
  `reincidencia[...]` com fonte `SVC-MEM MEM-…`) e cita a memória na evidência. A política
  (POL-06) então não abre a opção de waiver.

## Evidência

Cenário `reincidencia_waiver` (agosto e setembro com a mesma violação de alçada):

```
t=069 CMP-002  MEMORIA consultada waiver ['MEM-0001']
t=069 CMP-002  CRENCA AG-CIN: reincidencia[L-013]@2026-09 = {"aprovacao": "APR-001", "competencia": "2026-08", "memoria": "MEM-0001"}
t=071 APR-002  POLITICA POL-01 ticket emitido require_approval opções=['corrigir', 'bloquear']
...
SOL-002 inform publicado  (correção aprovada por Controller (APR-002): L-013 reaprovado por carla)
```

Para gravar a memória em arquivo e inspecioná-la:

```bash
python -m fin_mas run --scenario reincidencia_waiver --memoria .fin_mas/memoria.json
```

Entre execuções, o teste `test_memory_persists_across_runs_and_flags_recidivism` monta dois
sistemas independentes sobre o mesmo arquivo: o waiver de agosto, gravado pela primeira
execução, é carregado pela segunda (`MEMORIA carregada`) e muda a decisão de setembro; sem o
arquivo, a mesma execução de setembro aceita o waiver.

Testes: `test_memory_only_approved_with_provenance` (TEST-11),
`test_memory_persists_across_runs_and_flags_recidivism`, `test_memory_retention_expires_old_entries`,
`test_memory_file_has_no_personal_names`, `test_recurring_violation_after_waiver_denies_new_waiver`.
