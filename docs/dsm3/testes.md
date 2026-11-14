# Testes e evidências

```bash
python -m pytest                      # 250 testes (157 na DSM2), offline, ~40 s
python tools/trace.py --check         # rastreabilidade: 0 erros; 89 de 90 testes modelados executados
cd web && bun run test && bun run test:e2e   # reducer e regra da justificativa (12) e uso real no navegador (15)
```

## Novos na DSM3 (93 a mais que na DSM2)

| Arquivo | Testes | O que cobre |
|---|---|---|
| `tests/e2e/test_seguranca_protocolos.py` | 18 | os quatro ataques do feedback, personificação, papel, contraparte, esquema, isolamento de erros, adulteração de conteúdo, cenário adversarial completo e ausência de rejeições nos 7 cenários nominais |
| `tests/e2e/test_approval_gate.py` | 16 | TEST-12 e TEST-13, vínculo com solicitação/veto/ticket, duplicidade, atraso, reutilização entre ciclos de veto, papel do aprovador, SoD da aprovação, justificativa, correção fora das sugeridas, rejeição, reincidência |
| `tests/unit/test_memoria_redacao.py` | 21 | TEST-11 e TEST-23, retenção, persistência entre processos, pseudônimos, arquivo em outra versão do formato, adulteração do trace, credenciais fora do trace |
| `tests/e2e/test_revisao_pr.py` | 16 | um teste de regressão por achado da revisão do PR pelo coautor: decisão recusada mantém a pendência, waiver sem justificativa humana recusado, `replay --ancora`, redação sem alterar hashes, NORM-05 pelo valor, pseudônimo com chave, competência com uma regra só |
| `tests/unit/test_modelos_llm.py` | 8 | TEST-15, 17, 18, 20, 21, 22, 25 e provedor real indisponível |
| `tests/integration/test_dashboard_live.py` (casos novos) | 3 | token de sessão, `Host` e `Origin` na API do dashboard (TEST-73) |
| `tests/unit/test_fsm.py` (casos novos) | — | FSM do PROT-APR: quatro caminhos nominais e cinco transições inválidas |
| `tests/unit/test_bus.py` (casos novos) | — | mensagem sem credencial e mensagem sem protocolo; os demais passaram a usar agentes com papel |

Os testes da DSM2 que injetavam mensagens direto no barramento foram ajustados para enviar
pelo agente dono da identidade (com credencial), com o conteúdo que o esquema exige, e
continuam verificando a mesma propriedade de FSM.

## Evidências gravadas

| Evidência | Como gerar |
|---|---|
| Trace do cenário adversarial, verificado | `make ataque` (grava `saidas/ataque.jsonl` e roda `verificar`) |
| Comparação em 10 seeds (CSV, JSON, Markdown, SVG) | `python -m fin_mas comparar --seeds 10` → `docs/dsm3/resultados/` |
| Traces de todos os cenários para o replay do dashboard | `python -m fin_mas export` → `web/public/traces/` |
| Trilha causal legível | `python -m fin_mas run --scenario <nome>` (inclui `REJEITADA`, `POLITICA`, `MEMORIA`, `ATAQUES`) |
