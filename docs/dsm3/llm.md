# LLM opcional do Agente de Relatórios (SVC-MOD)

Implementa o ADR-002 da DSM1 em `src/fin_mas/services/modelos.py`. O LLM **só acrescenta**
uma síntese no topo do relatório do AG-REL; os números continuam vindo do template.

| Regra (ADR-002, NORM-05, NORM-07) | Implementação | Teste |
|---|---|---|
| Flag desligada por padrão | `RegistroModelos.config(...)["llm"] = False`; `run --llm MODELO` liga no AG-REL | `test_prompt_log_only_when_llm_enabled` |
| LLM só em AG-REL, AG-RES, AG-ORC | `configurar` levanta `ConfiguracaoInvalida` | `test_llm_not_allowed_roles_rejected` (TEST-21) |
| Número do texto = número do núcleo | todo número do texto gerado precisa existir no template; senão, fallback | `test_llm_numeric_mismatch_falls_back` (TEST-15) |
| LLM não autoriza ação | texto que propõe aprovar, estornar, lançar etc. é descartado | idem |
| Log de prompt e de custo só com a flag | registros `llm_prompt` (com `versao_prompt`) e `llm_custo` (tokens e US$) | TEST-17, TEST-18 |
| Troca de modelo sem reiniciar agentes | `configurar(..., modelo=...)` vale na próxima tarefa | `test_model_swap_without_redeploy` (TEST-20) |
| Cota de tokens | estimativa antes do envio; esgotada, não chama e usa o template | `test_token_limit_exceeded_fallback` (TEST-22) |
| Offline nos testes | provedores `mock-narrador`, `mock-alucina`, `mock-acao`; a rede é bloqueada no `conftest` | `test_real_provider_unavailable_falls_back_offline` |

Provedor real: `claude-opus-5-5`, pelo SDK `anthropic` (não é dependência obrigatória), com
`output_config.effort = "low"` (síntese curta), fallback do lado do servidor
(`fallbacks: "default"`) e checagem de `stop_reason == "refusal"`. Sem o SDK, sem credencial ou
sem rede, a chamada falha, o fallback é registrado e o relatório sai só com o template.

```bash
python -m fin_mas run --scenario fechar_mes --llm mock-narrador   # síntese aceita
python -m fin_mas run --scenario fechar_mes --llm mock-alucina    # número alterado: descartada (NORM-05)
```
