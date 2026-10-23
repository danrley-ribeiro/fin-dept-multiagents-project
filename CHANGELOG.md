# Changelog

Registro por entrega.

## DSM1 — v1.1 (19/10/2026)

- Nome do projeto: Sistema Multiagente de Controladoria (sem "terceirização").
- Nomes padronizados em português + ID: Orquestrador (`AG-ORQ`), Agente de Custos (`AG-CUS`),
  Agente de Orçamento (`AG-ORC`), Agente de Resultados (`AG-RES`), Agente de Controles Internos
  (`AG-CIN`) e Agente de Relatórios (`AG-REL`); serviços de plataforma também em português.
- Diagramas renomeados pela página da documentação onde aparecem (`ambiente_*`, `roles_*`,
  `protocols_*`, `traceability_*`).
- Novos diagramas de sequência: "avaliar o orçamento do trimestre" (Mermaid e TikZ) e "veto e waiver" (Mermaid, na documentação).
- Tratamento de falhas de especialista (um reenvio, depois `failure`) em `ROLE-ORQ`, `REQ-F01` e `TEST-26`.
- Linha de base do cenário sintético em `PROB-01`, `PROB-03`, `PROB-04` e `PROB-05`.

## DSM1 — v1.0 (06/10/2026)

- Modelos AOSE em `models/*.yaml`: 8 problemas, 7 stakeholders, 10 objetivos, 18 requisitos,
  8 papéis, 6 agentes, 6 protocolos (FSM), 8 normas, 8 recursos do ambiente, 7 serviços de
  plataforma, 25 testes especificados e 12 métricas.
- Validador e gerador de rastreabilidade (`tools/trace.py`): cobertura de 100% dos requisitos.
- Documentação Sphinx + sphinx-needs (`docs/`), pronta para o Read the Docs.
- PDF da entrega (`entregas/dsm1/documentacao/main.pdf`) com figuras TikZ.
- ADR-002 (LLM opcional por flag).

## DSM2 — Arquitetura e protótipo inicial (23/10/2026)

- Protótipo em Python 3.12 (`src/fin_mas/`): bus A2A em processo com relógio lógico, FSMs carregadas de
  `models/protocols.yaml`, Orquestrador e cinco agentes (`AG-CUS`, `AG-ORC`, `AG-RES`, `AG-CIN`, `AG-REL`),
  MCP mock somente leitura, dataset sintético com seed e gabarito, auditoria JSONL e reserva de período.
- ADR-003 (runtime Python determinístico) e ADR-004 (bus A2A e MCP mock); diagrama de arquitetura em
  `entregas/dsm2/`.
- CLI: `python -m fin_mas list | run | replay`; seis cenários, entre eles `depuracao` (seed 1337).
- 118 testes (`python -m pytest`), offline. `TEST-01` a `TEST-10`, `TEST-14`, `TEST-16`, `TEST-24` e
  `TEST-26` passam a `executado`; dez `COMP-*` passam a `implementado` com caminho real.
- `tools/trace.py` verifica que cada teste `executado` tem função pytest homônima e que cada componente
  `implementado` tem o caminho existente; a cobertura conta os testes executados.
- Fora do escopo, planejado para DSM3/DSM4: LLM, registro de modelos, memória, Approval Gate, redaction,
  métricas e dashboard (12 testes seguem `planejado`).

