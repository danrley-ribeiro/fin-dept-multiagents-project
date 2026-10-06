# ADR-001 — Plataforma de documentação

- **Status:** aceita (DSM1, 06/10/2026)
- **Contexto:** a documentação precisa ser 100% rastreável, compartilhável e editável por
  duas pessoas sem custo.

## Alternativas avaliadas

| Opção | Rastreabilidade | 2 editores grátis | Observação |
|---|---|---|---|
| Mintlify | manual (links Markdown) | **não** (plano Hobby: 1 assento) | Pro custa a partir de US$ 250/mês |
| Backstage.io (TechDocs) | catálogo de componentes, não de requisitos | sim, mas exige hospedar servidor | portal de desenvolvedor; pesado para o escopo |
| MkDocs Material + GitHub Pages | via script próprio | sim (repositório público) | sem extensão madura de rastreio |
| **Sphinx + sphinx-needs + Read the Docs** | **nativa** (tipos, links, matriz, grafo, validação) | **sim** (Community, repositório público) | padrão *docs-as-code* usado em engenharia de requisitos |

## Decisão

Usar **Sphinx + sphinx-needs**, com Markdown (MyST) e tema Furo, hospedado no
**Read the Docs Community**. Os modelos ficam em YAML (`models/`) e são convertidos
em objetos sphinx-needs por `tools/trace.py`.

## Consequências

- (+) Matriz, grafo e verificação de links automáticos; o build falha se a cadeia quebrar.
- (+) Colaboração por Pull Request, com histórico e revisão.
- (+) A mesma fonte gera as tabelas do PDF (LaTeX), eliminando divergência.
- (−) O repositório precisa ser **público**. A apostila da disciplina e os rascunhos locais
  ficam fora do versionamento (`.gitignore`).
- (−) Os needflows exigem Graphviz no build (instalado via `.readthedocs.yaml`).
