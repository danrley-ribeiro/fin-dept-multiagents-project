# SMA de Controladoria — Sistema Multiagente para terceirização da Controladoria

Projeto da disciplina **INE5628 — Sistemas Multiagentes** (UFSC/CTC/INE, Prof. Rafael Luiz Cancian).

Um orquestrador e cinco agentes especializados (Custos e Rentabilidade, Orçamento e Controle
Orçamentário, Resultados e Indicadores, Controles Internos e Relatórios Gerenciais) executam as
rotinas de controladoria de forma coordenada e auditável. Eles se apoiam em serviços de
plataforma: comunicação A2A/MCP, auditoria, configuração de modelos, memória, política de
segurança e reserva de período. A IA generativa é **opcional e desligada por padrão**, restrita à
narrativa em três agentes.

- 📘 **Documentação navegável e rastreável:** <https://fin-dept-multiagents-project.readthedocs.io>
- 📄 **PDF da DSM1:** [`entregas/dsm1/main.pdf`](entregas/dsm1/main.pdf)

## Autoria

| Nome | Matrícula |
|---|---|
| Danrley Moreira Ribeiro | 23102664 |
| Jiliard Mai Peifer | 23103129 |

Grupo: *Estudante 1, Jiliard e Danrley* (Moodle INE5628).

## Entregas

| Entrega | Conteúdo | Prazo | Situação |
|---|---|---|---|
| **DSM1** | Cenário, requisitos e modelagem (AOSE) | 10/10/2026 | ✅ concluída |
| **DSM2** | Arquitetura e protótipo inicial | 31/10/2026 | ⏳ pendente (pré-estruturada em `docs/dsm2/` e `entregas/dsm2/`) |

Enunciados: [`DSM1`](DSM1) · [`DSM2`](DSM2). Exemplo de formato usado como referência: [`DSM1.pdf`](DSM1.pdf).

### Entregáveis da DSM1

| Exigido | Onde |
|---|---|
| PDF (~4–6 páginas) | `entregas/dsm1/main.pdf` (fonte: `entregas/dsm1/main.tex`) |
| Diagramas/modelos editáveis | `models/*.yaml` (modelos AOSE), `diagrams/dsm1/*.mmd` (Mermaid), `entregas/dsm1/figures/*.tex` (TikZ) |
| README.md | este arquivo |
| USO_DE_IA.md | [`USO_DE_IA.md`](USO_DE_IA.md) |

## Rastreabilidade

Todos os objetos (problemas, stakeholders, objetivos, requisitos, papéis, agentes, protocolos,
normas, recursos, serviços, componentes, testes e métricas) têm **ID estável** em `models/*.yaml`,
que é a **fonte única**. O script `tools/trace.py`:

1. valida a cadeia **Problema → Requisito → Objetivo → Papel/Agente → Protocolo/Norma →
   Componente → Teste → Métrica**: falha com ID órfão, link quebrado ou requisito sem objetivo,
   papel, protocolo/norma, teste, métrica ou componente;
2. gera os objetos **sphinx-needs** da documentação (`docs/_generated/`), as **tabelas do PDF**
   (`entregas/dsm1/generated/`) e os **diagramas de estado** dos protocolos (`diagrams/dsm1/fsm_*.mmd`).

Situação atual: **18/18 requisitos (100%) com cadeia completa**, 136 objetos rastreados,
25 testes **especificados** (execução na DSM2) e 38 stubs pendentes da DSM2.

## Estrutura

```
models/              Fonte única dos modelos (YAML editável)
tools/trace.py       Validador + gerador de rastreabilidade
docs/                Documentação Sphinx + sphinx-needs (MyST Markdown)
  plataforma/        Rastreabilidade, fluxo de contribuição, ADR-001
  dsm1/              Entrega 1 (completa)
  dsm2/              Entrega 2 (esqueleto pendente)
diagrams/dsm1/       Diagramas Mermaid editáveis
entregas/dsm1/       main.tex, figuras TikZ, tabelas geradas e main.pdf
entregas/dsm2/       Pasta reservada da DSM2
```

## Como compilar

Pré-requisitos: Python 3.11+, Graphviz e TeX Live (com `latexmk`).

```bash
python -m venv .venv && .venv/bin/pip install -r docs/requirements.txt
make trace   # valida e regenera artefatos
make docs    # documentação HTML em docs/_build/html (sphinx -W)
make pdf     # entregas/dsm1/main.pdf
```

O CI (`.github/workflows/docs.yml`) repete essas etapas a cada push e PR e falha se os arquivos
gerados não estiverem atualizados no commit.

## Publicação no Read the Docs (feito uma vez)

1. Em <https://readthedocs.org> → *Import a Project* → selecionar este repositório.
2. A configuração já está em `.readthedocs.yaml` (Python 3.13, Graphviz, `fail_on_warning`).
3. Em *Admin → Maintainers*, adicionar a segunda pessoa. No GitHub, adicioná-la como colaboradora.

Fluxo de trabalho em dupla: [docs/plataforma/como-contribuir.md](docs/plataforma/como-contribuir.md).

## Observação sobre materiais da disciplina

A apostila da disciplina é de uso exclusivo em sala de aula e **não é versionada** (`.gitignore`).
Ela é apenas citada (Cancian, 2026) e parafraseada nos artefatos.
