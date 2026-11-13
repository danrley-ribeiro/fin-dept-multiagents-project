# Changelog

Registro por entrega.

## DSM3 — Comunicação, coordenação e protótipo funcional (10/11/2026)

- Feedback da DSM2 (segurança das interações): o barramento autentica o remetente (credencial por
  identidade), confere papel por performativo, destinatário como contraparte, esquema do conteúdo e
  transição da FSM antes de mudar estado; `advance` só por participante autenticado com papel autorizado;
  conteúdo copiado e conferido por hash; erro de agente isolado (`erro_agente` + resposta explícita).
  Fim do canal livre `protocol=None`. Campos `emissores`, `eventos_locais` e `esquemas` em `models/protocols.yaml`.
- Approval Gate (PROT-APR) e SVC-POL: ticket vinculado a solicitação, veto (hash), aprovador e prazo;
  política POL-01 a POL-08; `erp.corrigir` como único efeito externo, só com aprovação.
- SVC-MEM: memória persistente só de decisões humanas, com proveniência, retenção e pseudônimos; reincidência
  após waiver nega novo waiver (POL-06).
- Proteção de informações: redaction fail-closed em todo registro; JSONL com hash encadeado e `fin_mas verificar`.
- LLM opcional do AG-REL (SVC-MOD) com mocks offline, validação numérica, logs de prompt e custo, cota.
- Cenários `ataque_decisao_forjada` (14 ataques, 0 aceitos) e `reincidencia_waiver`; 75 testes novos (232 no total).
- Revisão do PR pelo coautor (12/11/2026): decisão humana recusada não consome mais a pendência; waiver sem
  justificativa humana é recusado (sem texto padrão); `replay --ancora`; redação de CPF/CNPJ não altera hashes
  hexadecimais; NORM-05 compara números pelo valor; pseudônimo da memória com HMAC; regra de competência única.
  15 testes de regressão (247 no total). Botão de waiver do dashboard
  com a regra da POL-04 (12 testes vitest e 14 Playwright passando).
- Issue #2: arquivo do SVC-MEM em outra versão do formato (ex.: v3, pseudônimo sem chave) deixa a memória
  comprometida ao carregar (falha fechada), em vez de carregar chaves de reincidência que não casam e
  desativar a POL-06. 2 casos novos no teste de falha fechada (249 no total).
- Teste exploratório: `iniciar.ps1` funciona sem Python 3.13 no PowerShell 5.1; dependências da documentação
  (Python 3.12+) só no modo `docs`; waiver negado pela política não aparece nem vira bloqueio no dashboard;
  aviso de erro só diz "pausada" quando pausou; MET-01 e `docs/dsm2/revisao.md` atribuídas ao feedback da
  DSM1. 250 testes Python e 15 de uso real. Limitação registrada: POL-06 conferida só na emissão do
  ticket (dois vetos do mesmo padrão pendentes juntos podem receber waiver), correção na DSM4.
- Rastreabilidade: REQ-S04, NORM-09, NORM-10, MET-15, MET-16, TEST-46 a TEST-71; COMP-MEM, COMP-POL, COMP-MOD,
  COMP-RED e COMP-SCH implementados. Resultados da DSM3 em `docs/dsm3/resultados/` (os da DSM2 preservados).
- Dashboard: pendências humanas pelo PROT-APR, rejeições no feed, decisão recusada vira aviso; API só aceita
  `Host`/`Origin` de loopback e exige token de sessão nos POST.
- Revisão interna: competência validada como `AAAA-MM`, entidade desconhecida recusada, scripts aceitam Python 3.11.
- Correção simulada por avaliador independente: gateway MCP e memória autenticados; barramento guarda só hashes de
  credenciais; envio atômico e prazo em `APROVADA`; reserva do período renovada durante a aprovação; memória assinada
  (HMAC) e sem nomes; selo HMAC no fim do trace; comandos do dashboard validados; redaction ampliada; POL-04 mais forte.
- Recorreção (nota simulada 7,3 → 8,1): memória com selo do arquivo inteiro, contador e chave fora da pasta de dados e
  falha fechada; ids únicos; decisão no último tick recusada; servidor autentica antes de ler o corpo; CPF/CNPJ sem
  máscara; âncora pública para verificar o trace sem a chave (`verificar --ancora`).
- Documentação `docs/dsm3/` (revisão pós-feedback, protocolos, coordenação, segurança, memória, LLM, testes,
  limitações, ADR-007) e pacote `entregas/dsm3/` (`make entrega-dsm3`).

## DSM2 revisada e início da DSM3 (29/10/2026)

- Feedback da DSM2: núcleo BDI (`core/bdi.py`); AG-ORC reescrito como BDI (fonte confiável, explicação de
  desvio por consulta direta ao AG-CIN, reconsideração e replanejamento); AG-CIN com seleção explícita entre
  aprovar, apontar, vetar com correção e vetar, e reconsideração após correção, waiver ou prazo.
- Decisões distribuídas: PROT-QRY ampliado (ORC↔CIN), ciclo `correcao` do PROT-CMP, Orquestrador só roteia.
- Baseline centralizado, MET-01 corrigida, MET-13 e MET-14, `python -m fin_mas comparar` (10 seeds).
- Empresa fictícia SMA com logo; dados mock de três competências (`expediente_sma`).
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

