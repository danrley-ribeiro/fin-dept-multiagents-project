# Uso de IA — DSM2

**Autores:** Danrley Moreira Ribeiro (23102664) e Jiliard Mai Peifer (23103129).

Registro do uso de IA generativa na produção da DSM2. O uso de IA **no produto** (LLM opcional por
flag) está na [ADR-002](../../docs/dsm1/ADR-002-llm-opcional-por-flag.md) e **não foi implementado** nesta
entrega: os agentes rodam só em modo determinístico.

## DSM2 — Arquitetura e protótipo inicial

**Modelo utilizado no desenvolvimento:** **Claude Sonnet 5.5**, pelo Claude Code.
**Período:** a partir de 23/10/2026.

### Papel da IA

A IA implementou o protótipo a partir dos modelos e das decisões da DSM1 (`models/*.yaml`), com o
escopo restrito ao que o enunciado da DSM2 pede.

| Atividade | Artefatos |
|---|---|
| Leitura da DSM1 (modelos, protocolos, requisitos, testes planejados) e do enunciado da DSM2 para planejar a execução | plano de execução em marcos |
| Comparação de runtimes e redação das ADRs | `docs/dsm2/ADR-003-*.md`, `ADR-004-*.md` |
| Diagrama de arquitetura (Mermaid e PNG) | `entregas/dsm2/modelos-editaveis/`, `entregas/dsm2/diagramas/` |
| Implementação do bus A2A, das FSMs lidas de `models/protocols.yaml`, dos seis agentes, do MCP mock, do dataset sintético, da auditoria e da reserva de período | `src/fin_mas/` |
| Escrita dos testes unitários e e2e e do cenário de depuração | `tests/` |
| Ligação dos testes e componentes aos modelos (`status`, `caminho`) e checagem em `tools/trace.py` | `models/`, `tools/trace.py` |
| Documentação da DSM2 | `docs/dsm2/`, `entregas/dsm2/README.md`, `CHANGELOG.md` |

### Decisões que permaneceram com os autores

- Escopo da entrega: **só o exigido pelo enunciado da DSM2**; LLM, memória, Approval Gate, métricas e
  dashboard ficam para a DSM3 e a DSM4.
- Commits locais e detalhados, sem coautoria da ferramenta.
- Domínio, agentes, protocolos, normas e testes: definidos pelos autores na DSM1.

### Verificação

- `python -m pytest`: **118 testes passam**, offline (a fixture de `tests/conftest.py` bloqueia a rede).
- `python tools/trace.py --check`: cadeia de rastreabilidade fechada, 0 erros; cada `TEST-*` marcado
  `executado` tem uma função pytest homônima (a checagem falha se o nome mudar).
- Reprodutibilidade: mesmo seed e mesmo hash, inclusive entre processos com `PYTHONHASHSEED` diferentes.
- `sphinx -W`: sem avisos além do `dot` (Graphviz) ausente na máquina local; o CI instala o Graphviz.
- **Revisão humana dos autores:** *a preencher pelos autores* com o que cada um conferiu antes da entrega
  (ADRs, regras dos agentes, cenário de depuração, resultados dos testes).

### Limites conhecidos

- A IA não executou o protótipo em ambiente distribuído nem com agentes em processos separados.
- Os valores do dataset são sintéticos; a linha de base da DSM1 continua sendo premissa.
- O conteúdo da apostila foi apenas citado e parafraseado (material de uso restrito).
