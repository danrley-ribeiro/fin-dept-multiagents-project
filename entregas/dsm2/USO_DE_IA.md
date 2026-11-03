# Uso de IA — DSM2

**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).

Registro do uso de IA generativa na produção da DSM2 (arquitetura e protótipo), da revisão feita após o
feedback do professor e do que foi adiantado da DSM3. O uso de IA **no produto** (LLM opcional por flag)
está na [ADR-002](../../docs/dsm1/ADR-002-llm-opcional-por-flag.md) e **não foi implementado**: todos os
agentes rodam em modo determinístico.

## Ferramentas e períodos

| Fase | Modelo | Ferramenta | Período |
|---|---|---|---|
| Protótipo inicial da DSM2 | Claude Sonnet 5.5 | Claude Code | 23/10/2026 |
| Revisão pós-feedback e início da DSM3 | Claude Opus 5.5 | Claude Code | 29/10/2026 |

Nenhum commit tem coautoria da ferramenta; o histórico está no repositório com o autor humano.

## O que a IA produziu

### Protótipo inicial (23/10)

| Atividade | Artefatos |
|---|---|
| Plano de execução a partir dos modelos da DSM1 e do enunciado da DSM2 | marcos de implementação |
| Comparação de runtimes e redação das ADRs | `docs/dsm2/ADR-003-*.md`, `ADR-004-*.md` |
| Bus A2A, FSMs lidas de `models/protocols.yaml`, seis agentes, MCP mock, dataset sintético, auditoria e reserva de período | `src/fin_mas/` |
| Testes iniciais e cenário de depuração | `tests/` |
| Ligação de testes e componentes aos modelos | `models/`, `tools/trace.py` |
| Documentação inicial | `docs/dsm2/`, `entregas/dsm2/README.md` |

### Revisão pós-feedback (29/10)

| Ponto do feedback ou pedido dos autores | O que a IA implementou | Artefatos |
|---|---|---|
| Dois agentes cognitivos | núcleo BDI; AG-ORC reescrito como BDI; seleção e reconsideração explícitas no AG-CIN | `core/bdi.py`, `agents/orc.py`, `agents/cin.py` |
| Decisões distribuídas | consulta direta ORC→CIN, veto com correção sugerida e reavaliação | `agents/orq.py`, `models/protocols.yaml` |
| MET-01 e comparação com o baseline | baseline centralizado, MET-01 corrigida, MET-13 e MET-14, experimento em 10 seeds | `baseline.py`, `metricas.py`, `experimentos.py`, `docs/dsm2/resultados/` |
| Checkpoints CP1–CP13 | mapa a partir da seção 5.16 da apostila (parafraseado) | `docs/checkpoints.md` |
| Empresa fictícia e dados mock (DSM3) | SMA com logo, três competências de dados | `env/empresa.py`, `assets/sma-logo.svg`, cenário `expediente_sma` |
| Regras para qualquer porte | base normativa por porte com referências legais | `models/portes.yaml`, `env/portes.py` |
| Empresas sem ERP | modelos Excel, leitura validada, servidor MCP de Excel | `fontes/planilha.py`, `mcp/excel_server.py` |
| Dashboard do escritório | execução ao vivo, servidor SSE, interface Vite + React + MUI com badges | `live.py`, `server.py`, `web/` |
| Comando único | preparação e execução em todos os modos | `iniciar.ps1`, `iniciar.sh`, `tools/iniciar.py` |
| Testes | e2e, integração e uso real no navegador (Playwright) | `tests/e2e/`, `tests/integration/`, `web/e2e/` |
| Documentação | Read the Docs, ADR-005, ADR-006, DSM1 v2 | `docs/`, `entregas/` |

## Decisões que ficaram com os autores

- Responder a cada ponto do feedback e, além dele, adiantar itens da DSM3 (dashboard, empresa SMA, dados
  mock, regras por porte e planilhas), por pedido explícito.
- Regras **sem LLM**, só determinísticas e com serviços simulados, como recomendou o feedback.
- Testes novos **só e2e, de integração e de uso real**, sem testes unitários isolados.
- **bun** como gerenciador de pacotes do dashboard.
- Commits sem coautoria da ferramenta.
- Domínio, agentes, protocolos e normas de base: definidos pelos autores na DSM1.

## Verificação

- `python -m pytest`: 157 testes passam, offline (o `tests/conftest.py` só libera o loopback).
- `tools/trace.py --check`: 0 erros, 100% dos requisitos cobertos; cada `TEST-*` executado tem um teste
  homônimo (pytest ou Playwright).
- `bun run test` (3) e `bun run test:e2e` (14 testes no Chrome sobre o servidor Python verdadeiro).
- `.\iniciar.ps1 testes` executado de ponta a ponta no Windows.
- `sphinx -W`: só o aviso do Graphviz ausente na máquina local (o Read the Docs instala).
- Inspeção visual do dashboard no navegador e do PDF da DSM1 v2.

## Revisão humana dos autores

- **Danrley Moreira Ribeiro** (conduziu as sessões com a ferramenta): trouxe o feedback do professor e pediu
  a correção completa na DSM2; revisou o dashboard no navegador e pediu Material Design, badges de
  notificação, o nome do departamento junto do código de cada agente, "Períodos" clicável, pessoas dentro
  das salas, um visual mais limpo para o fluxo das fontes de dados e a explicação de onde ficam "Novo
  pedido" e o desligamento de agentes; definiu que as regras e os BDIs deveriam valer para micro, pequena,
  média e grande empresa e que empresas sem ERP deveriam usar modelos Excel e um MCP de Excel; indicou a
  seção 5.16 da apostila para os checkpoints; pediu testes reais de uso, apenas testes e2e e de
  integração, bun no lugar de npm, um comando único de execução e a documentação completa no Read the Docs.
- **Jiliard Mai Peifer:** *registrar aqui o que conferiu antes da entrega* (a ferramenta não tem registro
  da participação dele nestas sessões).

## Limites conhecidos

- O protótipo não roda em ambiente distribuído nem com agentes em processos separados.
- Os parâmetros por porte são referências coerentes com a legislação de porte, não a política de uma
  empresa real; dados sintéticos têm gabarito, planilhas reais não.
- O `iniciar.sh` foi escrito para Linux/macOS, mas só o fluxo do Windows foi executado.
- O conteúdo da apostila foi apenas citado e parafraseado (material de uso restrito).
