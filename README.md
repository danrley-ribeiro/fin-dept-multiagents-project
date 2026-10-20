# Sistema Multiagente de Controladoria

Projeto da disciplina **INE5628 — Sistemas Multiagentes** (UFSC/CTC/INE, Prof. Rafael Luiz Cancian).

O Orquestrador e cinco agentes especializados (Agente de Custos, Agente de Orçamento, Agente de
Resultados, Agente de Controles Internos e Agente de Relatórios) executam as rotinas de
controladoria de forma coordenada e auditável, apoiados por serviços de plataforma (A2A/MCP,
auditoria, registro de modelos, memória, política de segurança e reserva de período). A IA
generativa é **opcional e desligada por padrão**, restrita à narrativa em três agentes.

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
| **DSM2** — Arquitetura e protótipo inicial | [`entregas/dsm2/`](entregas/dsm2/README.md) | ⏳ pendente |

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
  dsm2/                  mesma organização (pendente)
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
26 testes **especificados** (execução na DSM2) e 39 stubs pendentes da DSM2.

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
