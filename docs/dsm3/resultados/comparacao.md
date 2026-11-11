<!-- gerado por `python -m fin_mas comparar`; não editar à mão -->
Seeds: 1 a 10 (10 por cenário e estratégia).

| Cenário | Estratégia | Status típico | Desvios corretos | Falsos desvios | Críticas publicadas sem tratamento | Críticas corrigidas | Mensagens A2A | Latência (ticks) | Decisões fora do ORQ | Reconsiderações |
|---|---|---|---|---|---|---|---|---|---|---|
| `fechar_mes` | SMA | publicado | 100% | 0 | 0 | 0 | 21 | 16 | 78% | 0 |
| `fechar_mes` | workflow | publicado | 100% | 0 | 0 | 0 | 0 | 15 | 0% | 0 |
| `avaliar_orcamento` | SMA | publicado | 100% | 0 | 0 | 0 | 13 | 11 | 85% | 0 |
| `avaliar_orcamento` | workflow | publicado | 100% | 0 | 0 | 0 | 0 | 6 | 0% | 0 |
| `veto_waiver` | SMA | publicado_com_ressalva | 100% | 0 | 0 | 0 | 24 | 18 | 64% | 1 |
| `veto_waiver` | workflow | publicado_com_ressalva | 100% | 0 | 1 | 0 | 0 | 15 | 0% | 0 |
| `veto_bloqueio` | SMA | bloqueado | — | — | 0 | 0 | 20 | 32 | 67% | 0 |
| `veto_bloqueio` | workflow | publicado_com_ressalva | 100% | 0 | 1 | 0 | 0 | 15 | 0% | 0 |
| `veto_correcao` | SMA | publicado | 100% | 0 | 0 | 1 | 25 | 21 | 69% | 2 |
| `veto_correcao` | workflow | publicado_com_ressalva | 100% | 0 | 1 | 0 | 0 | 15 | 0% | 0 |
| `correcao_parcial` | SMA | bloqueado | — | — | 0 | 1 | 24 | 37 | 62% | 2 |
| `correcao_parcial` | workflow | publicado_com_ressalva | 100% | 0 | 2 | 0 | 0 | 15 | 0% | 0 |
| `divergencia_fonte` | SMA | publicado_com_ressalva | 100% | 0 | 0 | 0 | 9 | 9 | 71% | 0 |
| `divergencia_fonte` | workflow | publicado | 0% | 1 | 0 | 0 | 0 | 6 | 0% | 0 |
| `desvio_irregular` | SMA | publicado_com_ressalva | 100% | 0 | 0 | 1 | 27 | 23 | 78% | 3 |
| `desvio_irregular` | workflow | publicado_com_ressalva | 0% | 1 | 1 | 0 | 0 | 15 | 0% | 0 |
| `orc_sem_cin` | SMA | publicado_com_ressalva | 0% | 1 | 0 | 0 | 10 | 19 | 78% | 1 |
| `orc_sem_cin` | workflow | publicado | 0% | 1 | 0 | 0 | 0 | 6 | 0% | 0 |
| `falha_especialista` | SMA | falhou | — | — | 0 | 0 | 8 | 61 | 40% | 0 |
| `falha_especialista` | workflow | publicado | 100% | 0 | 0 | 0 | 0 | 15 | 0% | 0 |
| `depuracao` | SMA | publicado_com_ressalva | 100% | 0 | 0 | 0 | 25 | 48 | 58% | 1 |
| `depuracao` | workflow | publicado_com_ressalva | 100% | 0 | 1 | 0 | 0 | 15 | 0% | 0 |
| `fechamento_micro` | SMA | publicado_com_ressalva | 100% | 0 | 0 | 1 | 25 | 21 | 69% | 2 |
| `fechamento_micro` | workflow | publicado_com_ressalva | 100% | 0 | 1 | 0 | 0 | 15 | 0% | 0 |
| `fechamento_pequena` | SMA | publicado | 100% | 0 | 0 | 1 | 25 | 21 | 69% | 2 |
| `fechamento_pequena` | workflow | publicado_com_ressalva | 100% | 0 | 1 | 0 | 0 | 15 | 0% | 0 |
| `fechamento_grande` | SMA | publicado | 100% | 0 | 0 | 1 | 29 | 23 | 81% | 2 |
| `fechamento_grande` | workflow | publicado_com_ressalva | 100% | 0 | 1 | 0 | 0 | 15 | 0% | 0 |

MET-01 (conclusão com `inform`): 79% · MET-13 (resposta explícita): 100% · MET-14 (decisões fora do Orquestrador): 69% · MET-07 (trace completo): 100%
MET-12 (mesmo hash na segunda execução): 100%
