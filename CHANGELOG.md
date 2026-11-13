# Changelog

Registro por entrega.

## DSM3 v0.5.0 (12/11/2026)

- Cognição assistida (ADR-008, NORM-11, REQ-F08): proposta → validação (cinco regras) → hipótese → ação
  epistêmica → evidência → crença no AG-ORC; motor local offline (`cognicao/regras.py`) e LLM opcional como
  proponente; desejo `verificar_hipotese` com os planos P-CONFERIR-EVIDENCIA, P-VERIFICAR-COM-CIN,
  P-NEGOCIAR-PRAZO, P-VERIFICAR-NO-HISTORICO e P-ARQUIVAR-HIPOTESE; tools `planilhas.observacoes` e
  `erp.historico`; níveis `basico | local | llm` (`--cognicao`). Os 17 cenários revisados ficam em `basico`, com as
  mesmas métricas (o hash dos traces muda só pela versão do pacote no registro `meta`).
- Negociação de prazo no PROT-DEL: `propose`, `accept-proposal`, `reject-proposal`, estado `NEGOCIANDO`; regras do
  Orquestrador (só prazo, sem extensão com período reservado, uma por subtarefa, até 20 ticks); prazo vigente por
  conversa no barramento.
- Identidade e acesso por pessoa (ADR-009, SVC-IAM, REQ-S05, NORM-12, NORM-13): contas com scrypt, sessões com
  prazo e revogação, papéis ROLE-OPE, ROLE-AUD e ROLE-ADM, permissões em `models/permissions.yaml`, regras IAM-01 a
  IAM-07; cadastro em arquivo selado com contador e trava entre processos; trilha de acesso encadeada.
- Approval Gate pela pessoa: atestado de sessão (POL-09) no `approve`/`reject` (campo `atestado` no esquema), POL-02
  e POL-03 contra a pessoa real, POL-13 (quem solicita não aprova; controle compensatório na micro); prazo do ticket
  pelo instante previsto de entrega da decisão (TEST-134). Cenários `decisao_por_pessoa`, `solicitante_nao_aprova`,
  `waiver_exige_cargo`, `micro_controle_compensatorio` e `ataque_acesso` (15 ataques, 0 aceitos).
- Servidor e dashboard: login com cookie `HttpOnly; SameSite=Strict`, CSRF por sessão, permissão por rota e por
  comando, cabeçalhos de segurança; áreas Solicitações, Aprovações, Logs, Agentes e LLM e Porte; aba Hipóteses e
  origem das crenças na mente do agente. TEST-19 executado.
- LLM multiprovedor (SVC-MOD): mock, Claude (SDK opcional), GPT, Gemini e servidores compatíveis com a API da OpenAI;
  usos por agente (síntese, hipóteses, narrativa, comentário); consentimento para envio externo, pseudônimos,
  disjuntor, preço por modelo, conferência de números por rótulo; bancada `fin-mas llm avaliar`; `.env.example`.
  AG-ORQ, AG-CUS e AG-CIN seguem sem LLM (NORM-07).
- CLI: `acesso`, `auditoria`, `explicar`, `sequencia`, `invariantes` (INV-01 a INV-08), `cenarios [--verificar]`,
  `llm provedores | avaliar`, `instalar`, `doctor`, `serve --demo | --acesso | --instalacao | --cognicao`; comando
  `fin-mas`. Console de administração e auditoria no terminal (Textual, extra `tui`).
- Ficha do porte em `models/portes.yaml` (regime, obrigações, estrutura, calendário, papéis de acesso); as regras lidas
  pelos agentes não mudaram (normas-v2).
- Rastreabilidade: REQ-S05, REQ-F08, NORM-11 a NORM-13, SVC-IAM, componentes novos, MET-17 e MET-18, TEST-19 e
  TEST-91 a TEST-153 executados (312 objetos, 21 requisitos, 153 testes modelados, 0 erros).
- Correção simulada da v0.5.0 (4ª rodada): registro do barramento fechado depois da montagem; validação do texto
  de LLM endurecida e texto de modelo rotulado como não verificado; chave de API só para destinos confiáveis
  (`FIN_MAS_LLM_URLS_CONFIAVEIS`); prazo só pelo iniciador da conversa; falha explícita para resposta malformada de
  especialista; 400 para corpo HTTP inválido; bloqueio por tentativas sem derrubar sessões; SVC-LCK com credencial;
  invariantes INV-01, 02 e 03 corrigidos (TEST-141 a 153).
- Testes: 431 no pytest (eram 249 na tag `dsm3-base`), todos e2e, de integração ou de interface (TUI pelo Pilot do
  Textual); nenhum unitário novo. Playwright: 29 roteiros (9 de acesso e 6 das áreas de trabalho, novos). `make
  cenarios`, `make diagramas`, `make cobertura`, `make verificar-tudo`; `requirements-lock.txt`.
- Diagramas novos em `entregas/dsm3/`: login e sessão, decisão atestada, ciclo de hipóteses, PROT-DEL com
  negociação. Âncora nova do cenário `ataque_decisao_forjada`.
- Documentação: `docs/dsm3/` ganhou cognição, acesso, dashboard, implantação, catálogo de cenários de teste, ADR-008 e
  ADR-009; protocolos, coordenação, segurança (modelo de ameaças e invariantes), LLM, testes, revisão e limitações
  atualizados.

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

