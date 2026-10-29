# Sistema Multiagente de Controladoria · SMA S.A.

<img src="assets/sma-logo.svg" alt="SMA" width="56">

Projeto da disciplina **INE5628 — Sistemas Multiagentes** (UFSC/CTC/INE, Prof. Rafael Luiz Cancian).

O Orquestrador e cinco agentes especializados (Agente de Custos, Agente de Orçamento, Agente de
Resultados, Agente de Controles Internos e Agente de Relatórios) executam as rotinas de
controladoria da **SMA S.A.** (empresa fictícia) de forma coordenada e auditável. Orçamento e
Controles Internos são **agentes cognitivos BDI**; as regras valem para empresas de **qualquer
porte** (micro, pequena, média e grande), com ou sem ERP (modelos Excel e servidor MCP de Excel). Um
**dashboard** mostra os agentes trabalhando num escritório, ao vivo ou em replay. A IA generativa é
**opcional e desligada por padrão**, restrita à narrativa em três agentes.

```bash
python -m venv .venv && .venv/bin/pip install -e . -r requirements-dev.txt   # Windows: .venv\Scripts\
python -m fin_mas run --scenario desvio_irregular        # trilha causal com a mente dos agentes BDI
cd web && npm install && npm run build && cd .. && python -m fin_mas serve   # escritório: http://127.0.0.1:8765
```

📘 **Documentação navegável:** <https://fin-dept-multiagents-project.readthedocs.io>

## Autoria

| Nome | Matrícula |
|---|---|
| Danrley Moreira Ribeiro | 23102664 |
| Jiliard Mai Peifer | 23103129 |

## Entregas

Cada entrega tem uma pasta própria com tudo o que é submetido.

| Entrega | Pasta | Situação |
|---|---|---|
| **DSM1** — Cenário, requisitos e modelagem | [`entregas/dsm1/`](entregas/dsm1/README.md) | ✅ concluída |
| **DSM1 v2** — revisão pós-feedback | [`entregas/dsm1/documentacao/main-v2.pdf`](entregas/dsm1/documentacao/main-v2.pdf) | ✅ concluída |
| **DSM2** — Arquitetura e protótipo (revisados após o feedback) | [`entregas/dsm2/`](entregas/dsm2/README.md) | ✅ concluída (prazo 31/10) |
| **DSM3** — Comunicação e coordenação | [`docs/dsm3/`](docs/dsm3/index.md) | 🟡 em andamento (prazo 18/11) |

Enunciados e o exemplo de formato estão em [`enunciados/`](enunciados/).

## Estrutura

```
entregas/
  dsm1/
    README.md            descrição da entrega
    USO_DE_IA.md         uso de IA na entrega
    documentacao/        main.tex (arquivo único) e main.pdf
    modelos-editaveis/   diagramas Mermaid (.mmd)
    diagramas/           imagens dos diagramas (.png)
  dsm2/                  README, USO_DE_IA, diagramas e modelos-editaveis do protótipo
src/fin_mas/             protótipo em Python (agentes, bus A2A, MCP mock, cenários, CLI)
tests/                   testes unitários e e2e (pytest)
enunciados/              enunciados da disciplina e exemplo de formato
models/                  modelos AOSE em YAML (fonte única da rastreabilidade)
tools/trace.py           valida a cadeia de rastreabilidade e gera a documentação
docs/                    site de documentação (Sphinx + sphinx-needs, Read the Docs)
```

## Rastreabilidade

Todos os objetos (problemas, stakeholders, objetivos, requisitos, papéis, agentes, protocolos,
normas, recursos, serviços, componentes, testes e métricas) têm **ID estável** em `models/*.yaml`.
O `tools/trace.py` valida a cadeia **Problema → Requisito → Objetivo → Papel/Agente →
Protocolo/Norma → Componente → Teste → Métrica** (falha com ID órfão, link quebrado ou requisito
incompleto) e gera os objetos da documentação (`docs/_generated/`) e as máquinas de estados dos
protocolos (`entregas/dsm1/modelos-editaveis/protocols_fsm_*.mmd`).

Situação atual: **18/18 requisitos (100%) com cadeia completa**, 137 objetos rastreados,
26 testes (14 **executados** na DSM2 e 12 planejados) e 15 stubs pendentes.

## Como executar o protótipo (DSM2)

```bash
python -m venv .venv && .venv/bin/pip install -e . -r requirements-dev.txt
python -m fin_mas run --scenario fechar_mes --seed 42   # make demo
python -m pytest                                        # make test
```

Detalhes, cenários e o cenário de depuração: [entregas/dsm2/README.md](entregas/dsm2/README.md).

## Como compilar

Pré-requisitos: Python 3.11+, Graphviz e TeX Live (com `latexmk`).

```bash
python -m venv .venv && .venv/bin/pip install -r docs/requirements.txt
make trace   # valida a cadeia e regenera os arquivos gerados
make docs    # documentação HTML em docs/_build/html
make pdf     # entregas/dsm1/documentacao/main.pdf
```

O CI (`.github/workflows/docs.yml`) repete essas etapas a cada push e PR. Fluxo de trabalho em
dupla e publicação no Read the Docs: [docs/plataforma/como-contribuir.md](docs/plataforma/como-contribuir.md).

## Materiais da disciplina

A apostila é de uso exclusivo em sala de aula e **não é versionada** (`.gitignore`); ela é apenas
citada (Cancian, 2026) e parafraseada nos artefatos.
