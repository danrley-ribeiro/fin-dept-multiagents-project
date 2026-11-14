# Revisão pós-feedback

Cada ponto do feedback do professor sobre a DSM1, tratado na DSM2: o que mudou e onde está a evidência.

| Ponto do feedback | O que foi feito | Evidência |
|---|---|---|
| Só o AG-CIN era BDI; faltava o segundo agente cognitivo | AG-ORC reescrito sobre um núcleo BDI comum: crenças revisadas por percepção, desejos gerados das crenças, biblioteca de planos com utilidade, intenções suspensas e retomadas, replanejamento | {doc}`cognicao`; `src/fin_mas/core/bdi.py`, `agents/orc.py`; TEST-27, TEST-28, TEST-29 |
| Detalhar seleção e reconsideração de intenções no AG-CIN | Desejos concorrentes (conformidade × prazo), quatro planos com utilidade registrada em cada deliberação, reconsideração após correção, waiver e prazo | {doc}`cognicao`; `agents/cin.py`; TEST-30, TEST-31 |
| Mostrar decisões distribuídas, e não um workflow centralizado | Consulta direta AG-ORC → AG-CIN; o AG-CIN sugere correções e reavalia; o Orquestrador só roteia. Nova métrica MET-14 (decisões fora do Orquestrador) | {doc}`coordenacao`; {doc}`comparacao` |
| MET-01 contava falha como conclusão | MET-01 = `inform` / total; resposta explícita virou MET-13 | `models/metrics.yaml`; `src/fin_mas/metricas.py`; TEST-32 |
| Documentar CP1–CP13 | Mapa de checkpoints × artefatos × entrega | {doc}`../checkpoints` |
| Ciclo completo com divergência, veto, correção, timeout e aprovação humana | Cenários `divergencia_fonte`, `veto_correcao`, `correcao_parcial`, `orc_sem_cin`, `veto_waiver`, `veto_bloqueio` | {doc}`prototipo`; {doc}`testes` |
| Observar crenças, objetivos, intenções e decisões | Registros `belief`, `desire`, `deliberation` e `intention` no trace; CLI e dashboard | {doc}`dashboard`; ADR-005 |
| Só regras determinísticas e serviços simulados | Mantido: sem LLM; MCP mock e planilhas locais | ADR-003, ADR-004, ADR-006 |
| Comparar com o workflow centralizado | Baseline implementado com as mesmas regras; 10 seeds; vantagens e custos | {doc}`comparacao`; TEST-33 |

## Além do feedback (pedidos do grupo, adiantando a DSM3)

- Empresa fictícia **SMA** com logo nos relatórios, no dashboard e na documentação; dados
  mock de três competências (`expediente_sma`).
- **Regras por porte** (micro, pequena, média, grande) com base legal: {doc}`portes`.
- **Empresas sem ERP**: modelos Excel, modo manual e servidor MCP de Excel: {doc}`planilhas`.
- **Dashboard** do escritório ao vivo, com Material Design, badges e testes de uso real:
  {doc}`dashboard`.
