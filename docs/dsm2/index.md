# DSM2 — Arquitetura e protótipo inicial

<span class="badge-ok">revisada após o feedback</span>

Protótipo executável em `src/fin_mas/` (Python 3.12, offline e determinístico), com dois
agentes cognitivos BDI (AG-ORC e AG-CIN), decisões distribuídas entre especialistas,
comparação com o workflow centralizado da DSM1 e um dashboard do escritório ao vivo. O que
mudou depois do feedback está em {doc}`revisao`.

## Enunciado

**Entregar:** código-fonte executável; diagrama de arquitetura; `README.md`; testes
iniciais; `USO_DE_IA.md`.

**Requisitos:** justificar arquitetura e runtime; implementar agentes principais e
ambiente; implementar estado/conhecimento e comportamento básico; demonstrar ao menos
uma interação; incluir cenário controlado para depuração; registrar limitações.

| Critério | Peso | Página |
|---|---|---|
| Arquitetura e justificativa | 25% | {doc}`arquitetura` · {doc}`runtime` · ADR-003 a ADR-006 |
| Implementação | 25% | {doc}`prototipo` · {doc}`cognicao` · {doc}`portes` · {doc}`planilhas` |
| Interação e corretude | 20% | {doc}`coordenacao` · {doc}`prototipo` |
| Testes e reprodutibilidade | 20% | {doc}`testes` · {doc}`comparacao` |
| Documentação e autoria | 10% | `entregas/dsm2/README.md` · `entregas/dsm2/USO_DE_IA.md` · {doc}`revisao` |

## Checklist de entregáveis

- [x] Diagrama de arquitetura (camadas → componentes `COMP-*`) e diagramas do ciclo BDI, da consulta ORC↔CIN e do veto com correção
- [x] ADR-003 (runtime), ADR-004 (A2A e MCP mock), ADR-005 (execução ao vivo e dashboard), ADR-006 (regras por porte e planilhas)
- [x] Agentes principais + ambiente (empresa SMA simulada por porte ou planilha real)
- [x] Estado, conhecimento e crenças separados; dois agentes BDI com ciclo observável
- [x] Interações demonstradas: PROT-SOL, DEL, QRY (inclusive ORC→CIN), CMP (veto e correção), LCK
- [x] Cenário controlado de depuração (`depuracao`, seed 1337)
- [x] Testes e2e, de integração e de uso real no navegador ({doc}`testes`)
- [x] Comparação com o baseline em 10 seeds ({doc}`comparacao`)
- [x] Limitações registradas ({doc}`limitacoes`)
- [x] Checkpoints CP1–CP13 mapeados ({doc}`../checkpoints`)

## Herdado da DSM1 e o que foi feito

| Da DSM1 | Na DSM2 revisada |
|---|---|
| 6 agentes e 7 serviços especificados | 6 agentes, 2 deles BDI; serviços A2A, MCP (com Excel), auditoria e reserva implementados; memória, registro de modelos e política ficam para a DSM3 |
| 6 protocolos com FSM | FSMs carregadas de `models/protocols.yaml`; PROT-QRY ampliado para ORC↔CIN; ciclo `correcao` do PROT-CMP implementado |
| 8 normas | NORM-02 (allowlist), NORM-03 (período exclusivo), NORM-04 (veto) em código; normas por porte em `models/portes.yaml` |
| 12 métricas | MET-01 corrigida; MET-13 e MET-14 novas; MET-01, 02, 03, 04, 07, 09, 12, 13 e 14 calculadas |
| Linha de base (premissa) | workflow centralizado implementado e comparado |

```{toctree}
:maxdepth: 1

revisao
arquitetura
runtime
ADR-003-runtime-python-deterministico
ADR-004-a2a-bus-e-mcp-mock
ADR-005-execucao-ao-vivo-e-dashboard
ADR-006-regras-por-porte-e-planilhas
cognicao
coordenacao
portes
planilhas
prototipo
dashboard
testes
comparacao
limitacoes
```
