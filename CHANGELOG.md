# Changelog

Registro por entrega.

## DSM2 revisada e início da DSM3 (29/10/2026)

- Feedback da DSM2: núcleo BDI (`core/bdi.py`); AG-ORC reescrito como BDI (fonte confiável, explicação de
  desvio por consulta direta ao AG-CIN, reconsideração e replanejamento); AG-CIN com seleção explícita entre
  aprovar, apontar, vetar com correção e vetar, e reconsideração após correção, waiver ou prazo.
- Decisões distribuídas: PROT-QRY ampliado (ORC↔CIN), ciclo `correcao` do PROT-CMP, Orquestrador só roteia.
- Baseline centralizado, MET-01 corrigida, MET-13 e MET-14, `python -m fin_mas comparar` (10 seeds).
- Empresa fictícia SMA S.A. com logo; dados mock de três competências (`expediente_sma`).
- Regras base e pesos BDI por porte (`models/portes.yaml`, normas-v2): micro, pequena, média e grande.
- Empresas sem ERP: modelos Excel, leitura validada, correções gravadas na planilha, servidor MCP de Excel.
- Execução ao vivo + servidor SSE + dashboard Vite/React/MUI (escritório, mente BDI, badges, decisão humana,
  desligar agentes, dados da empresa, replay offline, comparação).
- Testes novos só e2e, de integração e de uso real (Playwright no Chrome); `tools/trace.py` liga também os testes do Playwright.
- Comando único (`iniciar.ps1` / `iniciar.sh` / `tools/iniciar.py`): verifica ou instala Python e bun, cria o
  `.venv`, instala dependências, builda o dashboard, exporta traces e roda os modos ao-vivo, replay, dev,
  testes, docs e cli. Dashboard com bun (`web/bun.lock`).
- Documentação: cognição, coordenação, comparação, portes, planilhas, dashboard, ADR-005, ADR-006,
  checkpoints CP1–CP13, revisão pós-feedback, DSM3. DSM1 v2 (`main-v2.pdf`).

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

