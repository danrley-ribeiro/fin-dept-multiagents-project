"""Cognição dos agentes além do núcleo BDI: proponentes locais de hipóteses e níveis de cognição (ADR-008).

Níveis (`Scenario.cognicao`, `--cognicao`):

- `basico`: o ciclo BDI de sempre, sem hipóteses (comportamento da DSM2/DSM3 revisada);
- `local`: regras locais propõem hipóteses, offline e sem custo (padrão dos cenários novos);
- `llm`: além das regras locais, um LLM opcional propõe hipóteses (exige a flag do agente no SVC-MOD).
"""
NIVEIS = ("basico", "local", "llm")
