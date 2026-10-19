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
- PDF da entrega (`entregas/dsm1/main.pdf`) com figuras TikZ editáveis.
- ADR-002 (LLM opcional por flag).

## DSM2 — pendente

- Estrutura reservada em `docs/dsm2/` e `entregas/dsm2/`. 13 componentes e 26 testes existem como
  stubs rastreáveis (`entrega: DSM2`).
